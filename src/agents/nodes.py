from typing import Dict, Any
from src.schema import AgentState, RegistryData, OwnershipStructure, RiskRating, OwnershipEntity
from langchain_openai import ChatOpenAI
import json

llm = ChatOpenAI(model="gpt-4o")

async def gather_registry_data_node(state: AgentState) -> Dict[str, Any]:
    # Simulate tool call to a global registry
    query = state["company_query"]
    
    # In a real app, this would use a tool like 'opencorporates' or 'global_registry_search'
    # For now, we simulate the structured output
    mock_data = RegistryData(
        company_name=query,
        registration_number=state.get("registration_number") or "REG-12345",
        status="Active",
        jurisdiction="Delaware",
        incorporation_date="2020-01-01",
        raw_data={"source": "mock_registry_api", "confidence": 0.98}
    )
    
    state["results"].registry = mock_data
    return {
        "results": state["results"],
        "logs": [f"Registry data gathered for {query}"]
    }

async def map_ownership_node(state: AgentState) -> Dict[str, Any]:
    # Analyze registry data to find owners
    registry = state["results"].registry
    
    # Simulate recursive tool use or reasoning to resolve layers
    mock_ownership = OwnershipStructure(
        entities=[
            OwnershipEntity(name="Founder A", type="Individual", percentage=60.0, is_ubo=True),
            OwnershipEntity(name="Holding Corp X", type="Corporate", percentage=40.0, is_ubo=False)
        ],
        layers=2,
        resolved=True
    )
    
    state["results"].ownership = mock_ownership
    return {
        "results": state["results"],
        "logs": ["Ownership structure mapped and UBOs identified."]
    }

async def process_documents_node(state: AgentState) -> Dict[str, Any]:
    # Simulate OCR and extraction
    docs = state.get("uploaded_docs", [])
    
    # In reality, this would use a vision model or PDF parser
    # state["results"].documents.append(...)
    
    return {
        "logs": [f"Processed {len(docs)} documents."]
    }

async def assess_risk_node(state: AgentState) -> Dict[str, Any]:
    # Chain-of-thought reasoning to assess risk
    results = state["results"]
    
    prompt = f"""
    Assess the KYB risk for this entity:
    Registry: {results.registry.model_dump_json() if results.registry else 'N/A'}
    Ownership: {results.ownership.model_dump_json() if results.ownership else 'N/A'}
    
    Provide a risk score (0-1) and key factors.
    Respond in JSON format.
    """
    
    response = await llm.ainvoke(prompt)
    # Parse and validate with Pydantic
    try:
        data = json.loads(response.content)
        risk = RiskRating(**data)
    except:
        risk = RiskRating(score=0.1, factors=["Low data available"], summary="Defaulting to low risk due to parsing error")
    
    state["results"].risk_assessment = risk
    return {
        "results": state["results"],
        "logs": [f"Risk assessment completed. Score: {risk.score}"]
    }
