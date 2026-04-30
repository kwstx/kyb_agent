from langgraph.graph import StateGraph, END
from src.schema import AgentState
from src.agents.supervisor import Supervisor
from src.agents.nodes import (
    gather_registry_data_node,
    map_ownership_node,
    process_documents_node,
    assess_risk_node,
    resolve_entities_node,
    reasoning_investigation_node,
    initial_memory_lookup_node,
    consent_management_node,
    privacy_cleanup_and_ssi_node,
    guardrails_node
)
from src.memory import get_checkpointer

def create_kyb_graph():
    # Initialize the graph with our state schema
    workflow = StateGraph(AgentState)

    # Add memory lookup node
    workflow.add_node("memory_lookup", initial_memory_lookup_node)

    # Add the Supervisor
    supervisor = Supervisor()
    workflow.add_node("supervisor", supervisor)

    # Add worker nodes
    workflow.add_node("gather_registry_data", gather_registry_data_node)
    workflow.add_node("map_ownership", map_ownership_node)
    workflow.add_node("process_documents", process_documents_node)
    workflow.add_node("assess_risk", assess_risk_node)
    workflow.add_node("resolve_entities", resolve_entities_node)
    workflow.add_node("reasoning_investigation", reasoning_investigation_node)
    workflow.add_node("consent_management", consent_management_node)
    workflow.add_node("privacy_cleanup", privacy_cleanup_and_ssi_node)
    workflow.add_node("guardrails", guardrails_node)

    # Define edges
    # Start with consent management to ensure legal compliance
    workflow.set_entry_point("consent_management")
    
    # After consent, go to memory lookup
    workflow.add_edge("consent_management", "memory_lookup")
    
    # After lookup, go to supervisor to plan the investigation
    workflow.add_edge("memory_lookup", "supervisor")

    # The supervisor decides where to go next
    def route_supervisor(state: AgentState):
        next_node = state.get("next_node")
        if next_node == "end":
            return "privacy_cleanup"
        return "guardrails" # Always go through guardrails first

    def route_guardrails(state: AgentState):
        if state.get("requires_human_signoff") and not state.get("human_approval_granted"):
            # This is where the graph would interrupt if compiled with interrupts
            # For this implementation, we'll route to END or a pause state if we had one
            return "supervisor" # Go back to supervisor to wait/replan if blocked
        
        return state.get("next_node")

    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "guardrails": "guardrails",
            "privacy_cleanup": "privacy_cleanup"
        }
    )

    workflow.add_conditional_edges(
        "guardrails",
        route_guardrails,
        {
            "gather_registry_data": "gather_registry_data",
            "map_ownership": "map_ownership",
            "process_documents": "process_documents",
            "assess_risk": "assess_risk",
            "resolve_entities": "resolve_entities",
            "reasoning_investigation": "reasoning_investigation",
            "supervisor": "supervisor"
        }
    )

    # Every worker node goes back to the supervisor to check the next step
    workflow.add_edge("gather_registry_data", "supervisor")
    workflow.add_edge("map_ownership", "supervisor")
    workflow.add_edge("process_documents", "supervisor")
    workflow.add_edge("assess_risk", "supervisor")
    workflow.add_edge("resolve_entities", "supervisor")
    workflow.add_edge("reasoning_investigation", "supervisor")
    
    # After cleanup, we are done
    workflow.add_edge("privacy_cleanup", END)

    # Compile with checkpointer for short-term conversational memory
    return workflow.compile(checkpointer=get_checkpointer())
