import asyncio
import json
import os
import hashlib
import time
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv

load_dotenv()

# Simplified version of the guard for standalone demo
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

class AutonomyGuard:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._signing_key = f"kya-secret-{agent_id}"
        self.llm = ChatOpenAI(model="gpt-4o")
        self.policy_rules = """
        1. NO direct access to PII without explicit consent.
        2. NO modification of historical audit logs.
        3. Mandatory escalation for jurisdictional overrides.
        """

    def _generate_signature(self, payload: Dict[str, Any]) -> str:
        canonical_payload = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(f"{canonical_payload}:{self._signing_key}".encode()).hexdigest()

    async def evaluate_action(self, action_type: str, payload: Dict[str, Any]) -> SafetyDecision:
        action_id = f"kya_{int(time.time())}_{hashlib.md5(action_type.encode()).hexdigest()[:6]}"
        parser = JsonOutputParser(pydantic_object=SafetyDecision)
        prompt = ChatPromptTemplate.from_template(
            "SYSTEM: You are the Policy Enforcement Layer.\nPOLICIES:\n{policies}\nACTION: {action_type}\nPAYLOAD: {payload}\n{format_instructions}"
        )
        chain = prompt | self.llm | parser
        decision_dict = await chain.ainvoke({
            "policies": self.policy_rules,
            "action_type": action_type,
            "payload": json.dumps(payload),
            "format_instructions": parser.get_format_instructions()
        })
        decision_dict["action_id"] = action_id
        decision = SafetyDecision(**decision_dict)
        if decision.authorized:
            auth_payload = {"agent_id": self.agent_id, "action_id": action_id, "action_type": action_type, "timestamp": time.time()}
            decision.signature = self._generate_signature(auth_payload)
        return decision

async def run_demo():
    print("=== STANDALONE GUARDRAILS DEMO ===")
    guard = AutonomyGuard(agent_id="KYB_Investigator_001")
    
    scenarios = [
        {"name": "Registry Search (Low Risk)", "type": "registry_search", "payload": {"company": "Acme Corp"}},
        {"name": "PII Access WITH Consent (High Risk)", "type": "pii_extraction", "payload": {"company": "Acme Corp", "has_consent": True}},
        {"name": "PII Access WITHOUT Consent (Blocked)", "type": "pii_extraction", "payload": {"company": "Acme Corp", "has_consent": False}},
    ]

    for s in scenarios:
        print(f"\n--- {s['name']} ---")
        decision = await guard.evaluate_action(s['type'], s['payload'])
        print(f"Authorized: {decision.authorized}")
        print(f"Risk Tier: {decision.risk_tier.value}")
        print(f"Reason: {decision.reason}")
        print(f"Explanation: {decision.explanation}")
        if decision.signature:
            print(f"Signature: {decision.signature[:24]}...")

if __name__ == "__main__":
    asyncio.run(run_demo())
