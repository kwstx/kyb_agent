import asyncio
import hashlib
import json
import time
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

# Mocking the classes here for a standalone demo to avoid dependency issues
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
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._signing_key = f"agent-secret-key-{agent_id}" 

    def _generate_signature(self, payload: Dict[str, Any]) -> str:
        canonical_payload = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(f"{canonical_payload}:{self._signing_key}".encode()).hexdigest()

    async def evaluate_action(self, action_type: str, payload: Dict[str, Any]) -> SafetyDecision:
        action_id = f"act_{int(time.time())}_{hashlib.md5(action_type.encode()).hexdigest()[:8]}"
        is_pii_request = "pii" in action_type.lower() or "sensitive" in action_type.lower()
        has_consent = payload.get("has_consent", False)
        
        if is_pii_request and not has_consent:
            return SafetyDecision(
                authorized=False,
                risk_tier=RiskTier.HIGH,
                reason="Compliance Violation: PII access requested without explicit consent.",
                action_id=action_id,
                explanation="Blocked attempt to access sensitive data."
            )

        risk_tier = RiskTier.LOW
        requires_hitl = False
        if any(t in action_type.lower() for t in ["override", "assess_risk", "final_approval"]):
            risk_tier = RiskTier.HIGH
            requires_hitl = True
        elif any(t in action_type.lower() for t in ["registry", "document"]):
            risk_tier = RiskTier.MEDIUM
            requires_hitl = True
        
        auth_payload = {"agent_id": self.agent_id, "action_id": action_id, "action_type": action_type, "timestamp": time.time()}
        signature = self._generate_signature(auth_payload)

        return SafetyDecision(
            authorized=True, risk_tier=risk_tier, reason=f"Action '{action_type}' authorized.",
            action_id=action_id, signature=signature, requires_hitl=requires_hitl,
            explanation=f"Auto-approved." if not requires_hitl else f"Human review required."
        )

async def run_demo():
    print("--- AutonomyGuard Safety Layer Demo ---")
    guard = AutonomyGuard(agent_id="KYB_Investigator_001")
    
    # Test 1: Low Risk Action
    print("\n[Test 1] Action: initial_lookup")
    res = await guard.evaluate_action("initial_lookup", {"has_consent": True})
    print(f"Authorized: {res.authorized} | Risk: {res.risk_tier.value} | HITL: {res.requires_hitl}")
    print(f"Signature: {res.signature[:32]}...")

    # Test 2: Medium Risk Action (Human in the Loop)
    print("\n[Test 2] Action: transition_to_gather_registry_data")
    res = await guard.evaluate_action("transition_to_gather_registry_data", {"has_consent": True})
    print(f"Authorized: {res.authorized} | Risk: {res.risk_tier.value} | HITL: {res.requires_hitl}")
    print(f"Explanation: {res.explanation}")

    # Test 3: High Risk Action (Mandatory Sign-off)
    print("\n[Test 3] Action: transition_to_assess_risk")
    res = await guard.evaluate_action("transition_to_assess_risk", {"has_consent": True})
    print(f"Authorized: {res.authorized} | Risk: {res.risk_tier.value} | HITL: {res.requires_hitl}")

    # Test 4: Policy Violation (PII access without consent)
    print("\n[Test 4] Action: pii_data_extraction (Consent: False)")
    res = await guard.evaluate_action("pii_data_extraction", {"has_consent": False})
    print(f"Authorized: {res.authorized} | Risk: {res.risk_tier.value}")
    print(f"Reason: {res.reason}")

if __name__ == "__main__":
    asyncio.run(run_demo())
