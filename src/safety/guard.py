import hashlib
import json
import time
import os
from dotenv import load_dotenv
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

load_dotenv()

class RiskTier(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class SafetyDecision(BaseModel):
    authorized: bool = Field(description="Whether the action is permitted by policy")
    risk_tier: RiskTier = Field(description="The calculated risk tier (low, medium, high)")
    reason: str = Field(description="Brief reason for the decision")
    action_id: str = Field(description="Unique identifier for this action attempt")
    signature: Optional[str] = Field(default=None, description="Cryptographic signature of the authorized action")
    requires_hitl: bool = Field(default=False, description="True if human-in-the-loop review is required")
    explanation: Optional[str] = Field(default=None, description="Detailed explanation for the user/auditor")
    policy_violations: List[str] = Field(default_factory=list, description="List of specific policy rules violated")

class AutonomyGuard:
    """
    Policy Enforcement Layer (PEL) for the KYB Agent.
    Implements Know Your Agent (KYA) principles, LLM-as-judge guardrails,
    and tiered risk escalation.
    """
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        # In a production environment, this would be a secure private key.
        self._signing_key = os.getenv("AGENT_SIGNING_KEY", f"kya-secret-{agent_id}")
        self.llm = ChatOpenAI(model="gpt-4o")
        
        self.policy_rules = """
        1. NO direct access to PII (Personally Identifiable Information) without explicit consent.
        2. NO modification of historical audit logs.
        3. Mandatory escalation for any action involving jurisdictional overrides.
        4. ALL external data writes must be reviewed if they affect the final risk score by >20%.
        5. NO automated final sign-off for high-value corporate entities (> $100M revenue).
        """

    def _generate_signature(self, payload: Dict[str, Any]) -> str:
        """Cryptographically signs an action payload using KYA principles."""
        canonical_payload = json.dumps(payload, sort_keys=True)
        # Using HMAC-SHA256 equivalent logic for demonstration
        return hashlib.sha256(f"{canonical_payload}:{self._signing_key}".encode()).hexdigest()

    async def evaluate_action(self, action_type: str, payload: Dict[str, Any]) -> SafetyDecision:
        """
        Evaluates an action using LLM-as-judge against compliance policies.
        Assigns Risk Tiers:
        - LOW: Auto-approve with explanation.
        - MEDIUM: Trigger human review via shared workspace.
        - HIGH: Mandatory human sign-off before execution.
        """
        action_id = f"kya_{int(time.time())}_{hashlib.md5(action_type.encode()).hexdigest()[:6]}"
        
        parser = JsonOutputParser(pydantic_object=SafetyDecision)
        
        prompt = ChatPromptTemplate.from_template(
            """
            SYSTEM: You are the Policy Enforcement Layer (PEL) for a KYB Autonomous Agent.
            Your task is to judge if a proposed action violates safety or compliance policies.
            
            POLICIES:
            {policies}
            
            ACTION TYPE: {action_type}
            PAYLOAD: {payload}
            
            RISK TIERING RULES:
            - LOW: Routine data gathering, public registry searches, internal reasoning.
            - MEDIUM: Accessing semi-private data, external API calls with costs, document parsing of non-public files.
            - HIGH: PII access, final risk assessment for major entities, jurisdictional overrides, data deletion.
            
            DECISION REQUIREMENTS:
            - If HIGH risk, authorized MUST be True only if 'has_consent' is present and True, but requires_hitl MUST be True.
            - If policy violation detected, authorized MUST be False.
            - Provide a detailed explanation for the 'explanation' field.
            
            {format_instructions}
            """
        )
        
        chain = prompt | self.llm | parser
        
        try:
            decision_dict = await chain.ainvoke({
                "policies": self.policy_rules,
                "action_type": action_type,
                "payload": json.dumps(payload),
                "format_instructions": parser.get_format_instructions()
            })
            
            # Ensure action_id is preserved
            decision_dict["action_id"] = action_id
            decision = SafetyDecision(**decision_dict)
            
        except Exception as e:
            # Fallback to safe default on LLM failure
            decision = SafetyDecision(
                authorized=False,
                risk_tier=RiskTier.HIGH,
                reason="PEL Failure",
                action_id=action_id,
                requires_hitl=True,
                explanation=f"Safety judge failed to respond: {str(e)}. Escalating to high-risk fallback."
            )

        if decision.authorized:
            # Cryptographic signing of the authorized action (KYA Principle)
            auth_payload = {
                "agent_id": self.agent_id,
                "action_id": action_id,
                "action_type": action_type,
                "risk_tier": decision.risk_tier.value,
                "timestamp": time.time(),
                "policy_version": "1.0.0"
            }
            decision.signature = self._generate_signature(auth_payload)

        return decision

# Singleton instance
guard = AutonomyGuard(agent_id="KYB_Investigator_001")
