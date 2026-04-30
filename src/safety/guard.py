import hashlib
import json
import time
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class RiskTier(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class SafetyDecision(BaseModel):
    authorized: bool
    risk_tier: RiskTier
    reason: str
    action_id: str
    signature: Optional[str] = None
    requires_hitl: bool = False
    explanation: Optional[str] = None

class AutonomyGuard:
    """
    Policy Enforcement Layer for the KYB Agent.
    Implements Know Your Agent (KYA) principles and risk-based escalation.
    """
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        # In a real system, this would be a private key stored in an HSM or secure enclave.
        self._signing_key = f"agent-secret-key-{agent_id}" 

    def _generate_signature(self, payload: Dict[str, Any]) -> str:
        """Cryptographically signs an action payload using KYA principles."""
        canonical_payload = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(f"{canonical_payload}:{self._signing_key}".encode()).hexdigest()

    async def evaluate_action(self, action_type: str, payload: Dict[str, Any]) -> SafetyDecision:
        """
        Evaluates an action against compliance policies and assigns risk tiers.
        Wraps the agent runtime to block unauthorized or high-risk actions.
        """
        action_id = f"act_{int(time.time())}_{hashlib.md5(action_type.encode()).hexdigest()[:8]}"
        
        # Policy Check: No direct access to PII without explicit consent
        is_pii_request = "pii" in action_type.lower() or "sensitive" in action_type.lower()
        has_consent = payload.get("has_consent", False)
        
        if is_pii_request and not has_consent:
            return SafetyDecision(
                authorized=False,
                risk_tier=RiskTier.HIGH,
                reason="Compliance Violation: PII access requested without explicit consent.",
                action_id=action_id,
                explanation="Blocked attempt to access sensitive data. No valid consent token found in payload."
            )

        # Risk Tier Classification
        risk_tier = RiskTier.LOW
        requires_hitl = False
        
        # High Risk: Critical overrides or high-impact financial/legal actions
        high_risk_triggers = ["override", "delete", "transfer", "final_approval"]
        # Medium Risk: External interactions or data writes
        medium_risk_triggers = ["api_call", "registry_search", "document_parsing"]

        if any(t in action_type.lower() for t in high_risk_triggers):
            risk_tier = RiskTier.HIGH
            requires_hitl = True
        elif any(t in action_type.lower() for t in medium_risk_triggers):
            risk_tier = RiskTier.MEDIUM
            requires_hitl = True # Medium risk triggers human review per requirements
        
        # Cryptographic signing of the authorized action
        auth_payload = {
            "agent_id": self.agent_id,
            "action_id": action_id,
            "action_type": action_type,
            "risk_tier": risk_tier.value,
            "timestamp": time.time()
        }
        signature = self._generate_signature(auth_payload)

        return SafetyDecision(
            authorized=True,
            risk_tier=risk_tier,
            reason=f"Action '{action_type}' authorized.",
            action_id=action_id,
            signature=signature,
            requires_hitl=requires_hitl,
            explanation=f"Auto-approved at {risk_tier.value} risk level." if not requires_hitl else f"Human review required for {risk_tier.value} risk action."
        )

# Initialize the Policy Enforcement Layer
guard = AutonomyGuard(agent_id="KYB_Investigator_001")
