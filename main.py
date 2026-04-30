import asyncio
import os
from dotenv import load_dotenv
from src.graph import create_kyb_graph
from src.schema import KYBProfile

load_dotenv()

async def main():
    # Initialize state
    initial_state = {
        "company_query": "Antigravity AI Corp",
        "registration_number": "DEL-999000",
        "uploaded_docs": ["certificate_of_inc.pdf"],
        "plan": [],
        "current_task": None,
        "results": KYBProfile(),
        "logs": [],
        "next_node": ""
    }

    # Create the graph
    app = create_kyb_graph()

    print("--- Starting KYB Investigation ---")
    
    # Run the graph
    async for output in app.astream(initial_state):
        for node_name, state_update in output.items():
            print(f"\n[Node: {node_name}]")
            if "logs" in state_update:
                for log in state_update["logs"]:
                    print(f"  > {log}")

    print("\n--- Investigation Complete ---")
    # Final state can be retrieved from the last output or by running app.ainvoke
    final_state = await app.ainvoke(initial_state)
    print("\nFinal Risk Assessment:")
    if final_state["results"].risk_assessment:
        print(f"Score: {final_state['results'].risk_assessment.score}")
        print(f"Summary: {final_state['results'].risk_assessment.summary}")

if __name__ == "__main__":
    asyncio.run(main())
