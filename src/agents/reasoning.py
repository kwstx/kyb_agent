from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from src.schema import RegistryData

class ReasoningAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o")

    async def cross_reference(self, registry_data: RegistryData, document_facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Cross-reference extracted document facts against registry data to find contradictions.
        """
        facts_str = "\n".join([f"- {f['content']} (Source: {f['metadata'].get('doc_id')})" for f in document_facts])
        
        prompt = f"""
        You are a Senior KYB Compliance Investigator. 
        Your task is to compare the 'Official Registry Data' with 'Extracted Document Facts' and identify any contradictions, discrepancies, or missing information.
        
        Official Registry Data:
        {registry_data.model_dump_json() if registry_data else "None"}
        
        Extracted Document Facts:
        {facts_str}
        
        Analyze each fact against the registry data. 
        Return a list of findings, specifically flagging 'Contradictions' for deeper investigation.
        Format your response as a JSON list of objects:
        [
            {{"fact": "...", "contradiction": true/false, "explanation": "...", "severity": "low/medium/high"}}
        ]
        """
        
        response = await self.llm.ainvoke(prompt)
        # In a real system, you'd parse and validate the JSON
        return response.content
