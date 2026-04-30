import asyncio
import json
from src.safety.guard import guard, RiskTier
from src.agents.nodes import guardrails_node
from src.schema import AgentState, KYBProfile

async def run_demo():
    print("=== Robust Guardrails & Safety Layer Demo ===")
    
    # 1. Low Risk Scenario: Registry Search
    state_low = {
        "next_node": "gather_registry_data",
        "company_query": "Test Corp",
        "consent_granted": True,
        "consent_scope": ["storage"]
    }
    print("\n[Scenario 1: Registry Search (Low Risk)]")
    result_low = await guardrails_node(state_low)
    for log in result_low["logs"]:
        print(f"  {log}")

    # 2. Medium Risk Scenario: Document Parsing
    state_med = {
        "next_node": "process_documents",
        "company_query": "Test Corp",
        "consent_granted": True,
        "consent_scope": ["storage"]
    }
    print("\n[Scenario 2: Document Parsing (Medium Risk)]")
    result_med = await guardrails_node(state_med)
    for log in result_med["logs"]:
        print(f"  {log}")

    # 3. High Risk Scenario: PII Access WITH Consent
    state_high_auth = {
        "next_node": "pii_extraction", # Simulated node name that triggers PII policy
        "company_query": "Test Corp",
        "consent_granted": True,
        "consent_scope": ["pii_access"]
    }
    print("\n[Scenario 3: PII Access WITH Consent (High Risk)]")
    result_high_auth = await guardrails_node(state_high_auth)
    for log in result_high_auth["logs"]:
        print(f"  {log}")

    # 4. High Risk Scenario: PII Access WITHOUT Consent (Should be Blocked)
    state_high_blocked = {
        "next_node": "pii_extraction",
        "company_query": "Test Corp",
        "consent_granted": False,
        "consent_scope": []
    }
    print("\n[Scenario 4: PII Access WITHOUT Consent (BLOCKED)]")
    result_high_blocked = await guardrails_node(state_high_blocked)
    for log in result_high_blocked["logs"]:
        print(f"  {log}")

if __name__ == "__main__":
    asyncio.run(run_demo())
