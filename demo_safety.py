import asyncio
from src.graph import create_kyb_graph
from src.schema import AgentState, KYBProfile
from src.safety.guard import guard

async def run_demo():
    print("--- KYB Agent Guardrails & Safety Demo ---")
    
    # 1. Initialize state for a simple investigation
    state = AgentState(
        company_query="Global Tech Corp",
        registration_number="GTC-7788",
        uploaded_docs=[],
        plan=[],
        current_task=None,
        results=KYBProfile(),
        reasoning_history=[],
        hypotheses=[],
        logs=[],
        next_node="gather_registry_data",
        consent_scope=["storage"], # Missing selective_sanctions or specific pii consent if needed
        consent_granted=True,
        vc_link=None,
        safety_evaluation=None,
        requires_human_signoff=False,
        human_approval_granted=False
    )

    # 2. Compile the graph
    app = create_kyb_graph()
    
    # 3. Simulate a high-risk transition
    # We'll set the next_node to something that triggers a high risk in our mock guard
    state["next_node"] = "assess_risk" # Let's say this is medium/high risk
    
    print(f"\nStep 1: Supervisor proposes '{state['next_node']}'...")
    
    # Run the guardrails node directly for demonstration
    from src.agents.nodes import guardrails_node
    result = await guardrails_node(state)
    
    print(f"Safety Decision: {result['safety_evaluation']['reason']}")
    print(f"Risk Tier: {result['safety_evaluation']['risk_tier']}")
    print(f"Requires Human Sign-off: {result['requires_human_signoff']}")
    print(f"Action Signature: {result['safety_evaluation']['signature'][:32]}...")
    
    # 4. Simulate a Compliance Violation (PII without consent)
    print("\nStep 2: Simulating PII access without proper consent scope...")
    state["consent_granted"] = False # Revoke consent
    state["next_node"] = "pii_data_extraction" # Custom type to trigger PII block
    
    # We evaluate this via the guard directly to show the block
    evaluation = await guard.evaluate_action("pii_data_extraction", {"has_consent": False})
    print(f"Action: pii_data_extraction | Authorized: {evaluation.authorized}")
    print(f"Reason: {evaluation.reason}")

if __name__ == "__main__":
    asyncio.run(run_demo())
