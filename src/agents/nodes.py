from typing import Dict, Any, List
from src.schema import AgentState, RegistryData, OwnershipStructure, RiskRating, OwnershipEntity
from langchain_openai import ChatOpenAI
import json
from src.agents.entity_resolution import EntityResolutionAgent
from datetime import datetime
from src.memory import VectorMemory, GraphMemory

llm = ChatOpenAI(model="gpt-4o")
er_agent = EntityResolutionAgent()
vector_memory = VectorMemory()
graph_memory = GraphMemory()

async def initial_memory_lookup_node(state: AgentState) -> Dict[str, Any]:
    """Retrieves historical data and similar cases to inform the investigation."""
    company_id = state.get("registration_number") or state["company_query"]
    logs = []
    
    # 1. Long-term memory lookup (Knowledge Graph)
    historical_profile = graph_memory.get_historical_profile(company_id)
    if historical_profile:
        logs.append(f"Retrieved historical profile for {company_id} from knowledge graph.")
        # We'll store this in the state for later delta detection or reference
        state["results"].registry = RegistryData.model_validate_json(historical_profile["registry"]) if historical_profile.get("registry") else None
        state["results"].ownership = OwnershipStructure.model_validate_json(historical_profile["ownership"]) if historical_profile.get("ownership") else None
    
    # 2. Medium-term memory lookup (Vector DB)
    query_text = f"KYB investigation for {state['company_query']}"
    similar_cases = vector_memory.search_similar_cases(query_text)
    if similar_cases:
        logs.append(f"Found {len(similar_cases)} similar past cases for context.")
        # In a real agent, we'd add these to the context window as few-shot examples
        state["hypotheses"].append({"type": "similarity_context", "cases": similar_cases})

    return {
        "results": state["results"],
        "hypotheses": state["hypotheses"],
        "logs": logs
    }

async def gather_registry_data_node(state: AgentState) -> Dict[str, Any]:
    # Simulate tool call to a global registry
    query = state["company_query"]
    
    # In a real app, this would use a tool like 'opencorporates' or 'global_registry_search'
    # For now, we simulate the structured output
    new_registry_data = RegistryData(
        company_name=query,
        registration_number=state.get("registration_number") or "REG-12345",
        status="Active",
        jurisdiction="Delaware",
        incorporation_date="2020-01-01",
        raw_data={"source": "mock_registry_api", "confidence": 0.98}
    )
    
    # Delta detection if we have historical data
    logs = [f"Registry data gathered for {query}"]
    if state["results"].registry:
        deltas = graph_memory.detect_deltas({"registry": state["results"].registry.model_dump_json()}, new_registry_data)
        if deltas:
            logs.append(f"Deltas detected: {', '.join(deltas)}")
        else:
            logs.append("No changes detected since last investigation. Focusing on validation.")

    state["results"].registry = new_registry_data
    return {
        "results": state["results"],
        "logs": logs
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

from src.tools.document import DocumentProcessor
from src.agents.document_understanding import DocumentUnderstandingAgent
from src.agents.reasoning import ReasoningAgent

doc_processor = DocumentProcessor()
doc_understanding = DocumentUnderstandingAgent()
reasoning_agent = ReasoningAgent()

from src.schema import DocumentChunk, DocumentEvidence

async def process_documents_node(state: AgentState) -> Dict[str, Any]:
    docs = state.get("uploaded_docs", [])
    logs = []
    
    current_evidence = DocumentEvidence(
        doc_type="investigation_batch",
        findings=[],
        confidence=0.0,
        chunks=[],
        source_files=docs
    )
    
    all_chunks = []
    
    for doc_path in docs:
        # 1. OCR / Extraction
        extraction = doc_processor.process(doc_path)
        logs.append(f"Extracted text from {doc_path} using {extraction.metadata['engine']}")
        
        # 2. Analyze and Index
        doc_id = doc_path.split("/")[-1]
        chunks_data = await doc_understanding.analyze_and_index(extraction, doc_id)
        
        for c in chunks_data:
            all_chunks.append(DocumentChunk(text=c["text"], metadata=c["metadata"]))
            
        logs.append(f"Indexed {len(chunks_data)} chunks from {doc_id}")
        
    current_evidence.chunks = all_chunks
    
    # 3. Cross-reference with Registry Data if available
    registry = state["results"].registry
    if registry and docs:
        facts = await doc_understanding.query_facts(f"Details about {registry.company_name}")
        contradictions = await reasoning_agent.cross_reference(registry, facts)
        
        logs.append("Cross-referenced document facts with registry data.")
        current_evidence.findings.append(str(contradictions))
        current_evidence.confidence = 0.85 # Simplified
        
    state["results"].documents.append(current_evidence)

    return {
        "results": state["results"],
        "logs": logs
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
    
    # Update Memory Systems
    company_id = state.get("registration_number") or state["company_query"]
    
    # 1. Update Long-term Knowledge Graph
    graph_memory.update_knowledge_base(company_id, state["results"])
    
    # 2. Update Medium-term Vector Memory
    vector_memory.add_case(state["results"].model_dump(), {"query": state["company_query"]})
    
    return {
        "results": state["results"],
        "logs": [f"Risk assessment completed. Score: {risk.score}", "Knowledge base and vector memory updated."]
    }

async def resolve_entities_node(state: AgentState) -> Dict[str, Any]:
    """Node for resolving discovered entities against the knowledge graph."""
    logs = []
    ownership = state["results"].ownership
    
    if not ownership or not ownership.entities:
        return {"logs": ["No ownership data to resolve."]}
        
    source_metadata = {
        "url": state["results"].registry.raw_data.get("source", "unknown") if state["results"].registry else "unknown",
        "timestamp": datetime.now().isoformat()
    }
    
    # Run ER logic
    parent_id = state.get("registration_number") or state["company_query"]
    resolution_results = await er_agent.resolve_entities(ownership.entities, source_metadata, parent_id)
    
    for res in resolution_results:
        logs.append(f"Entity {res['entity']}: {res['status']} (confidence: {res.get('confidence', 1.0)})")
        if "subtask" in res:
            logs.append(f"CRITICAL: Spawning sub-task: {res['subtask']}")
            # In a real system, this would append to a task queue or update the plan
            state["plan"].append(res["subtask"])
            
    state["results"].entities_resolved = True
            
    return {
        "results": state["results"],
        "plan": state["plan"],
        "logs": logs
    }

async def reasoning_investigation_node(state: AgentState) -> Dict[str, Any]:
    """Node for complex reasoning and planning using the Investigator/Critic loop."""
    # Note: reasoning_agent.run_investigation_loop handles adding logs and updating results
    updated_state = await reasoning_agent.run_investigation_loop(state)
    
    return {
        "results": updated_state["results"],
        "reasoning_history": updated_state.get("reasoning_history", []),
        "hypotheses": updated_state.get("hypotheses", []),
        "logs": updated_state["logs"]
    }
