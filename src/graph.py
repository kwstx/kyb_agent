from langgraph.graph import StateGraph, END
from src.schema import AgentState
from src.agents.supervisor import Supervisor
from src.agents.nodes import (
    gather_registry_data_node,
    map_ownership_node,
    process_documents_node,
    assess_risk_node,
    resolve_entities_node
)

def create_kyb_graph():
    # Initialize the graph with our state schema
    workflow = StateGraph(AgentState)

    # Add the Supervisor
    supervisor = Supervisor()
    workflow.add_node("supervisor", supervisor)

    # Add worker nodes
    workflow.add_node("gather_registry_data", gather_registry_data_node)
    workflow.add_node("map_ownership", map_ownership_node)
    workflow.add_node("process_documents", process_documents_node)
    workflow.add_node("assess_risk", assess_risk_node)
    workflow.add_node("resolve_entities", resolve_entities_node)

    # Define edges
    # Start always goes to the supervisor for the initial plan
    workflow.set_entry_point("supervisor")

    # The supervisor decides where to go next
    def route_supervisor(state: AgentState):
        next_node = state.get("next_node")
        if next_node == "end":
            return END
        return next_node

    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "gather_registry_data": "gather_registry_data",
            "map_ownership": "map_ownership",
            "process_documents": "process_documents",
            "assess_risk": "assess_risk",
            "resolve_entities": "resolve_entities",
            END: END
        }
    )

    # Every worker node goes back to the supervisor to check the next step
    workflow.add_edge("gather_registry_data", "supervisor")
    workflow.add_edge("map_ownership", "supervisor")
    workflow.add_edge("process_documents", "supervisor")
    workflow.add_edge("assess_risk", "supervisor")
    workflow.add_edge("resolve_entities", "supervisor")

    return workflow.compile()
