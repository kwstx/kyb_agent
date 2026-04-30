from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.schema import AgentState
import json

class Supervisor:
    def __init__(self, model: str = "gpt-4o"):
        self.llm = ChatOpenAI(model=model)

    async def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        The Supervisor analyzes the current state and results to determine the next step.
        """
        company = state["company_query"]
        reg_num = state.get("registration_number", "Unknown")
        results = state["results"]
        
        prompt = f"""
        You are the KYB Supervisor Agent. Your goal is to conduct a thorough investigation of: {company} (Reg: {reg_num}).
        
        Current Status:
        - Registry Data: {'Present' if results.registry else 'Missing'}
        - Ownership Structure: {'Present' if results.ownership else 'Missing'}
        - Entity Resolution: {'Complete' if results.entities_resolved else 'Pending'}
        - Documents Processed: {len(results.documents)}
        - Risk Assessment: {'Present' if results.risk_assessment else 'Missing'}
        
        Available Nodes:
        1. gather_registry_data: Retrieve official records.
        2. map_ownership: Analyze registry/docs to find owners.
        3. resolve_entities: Link owners to the Knowledge Graph and check for duplicates/linkages.
        4. process_documents: Analyze uploaded files.
        5. reasoning_investigation: Perform deep reasoning, self-critique, and hypothesis branching for complex structures or high-ambiguity cases.
        6. assess_risk: Final evaluation based on all evidence.
        7. end: Investigation complete.
        
        Instructions:
        - If registry data is missing, prioritize gather_registry_data.
        - If ownership is mapped but resolve_entities hasn't run, go to resolve_entities.
        - Once registry/ownership is present and resolved, if documents are uploaded but not processed, go to process_documents.
        - FOR COMPLEX STRUCTURES (multiple layers, trusts, or unresolved entities), use reasoning_investigation before assess_risk.
        - If all data is gathered and resolved, go to assess_risk.
        - If everything is done, go to end.
        
        Respond with ONLY a JSON object: {{"next_node": "node_name", "reasoning": "why"}}
        """
        
        messages = [
            SystemMessage(content="You are a senior compliance supervisor."),
            HumanMessage(content=prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        decision = json.loads(response.content)
        
        return {
            "next_node": decision["next_node"],
            "logs": [f"Supervisor decision: {decision['next_node']} - {decision['reasoning']}"]
        }
