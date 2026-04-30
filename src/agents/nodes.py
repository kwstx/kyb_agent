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

from src.privacy.consent import consent_manager
from src.privacy.ssi import ssi_issuer
from src.safety.guard import guard, RiskTier
from src.tools.audit import audit_store

async def guardrails_node(state: AgentState) -> Dict[str, Any]:
    """
    Policy Enforcement Layer that evaluates the next planned action.
    Blocks actions violating compliance or requiring human intervention.
    """
    next_node = state.get("next_node", "end")
    
    # Contextual payload for safety evaluation
    payload = {
        "has_consent": state.get("consent_granted", False),
        "consent_scope": state.get("consent_scope", []),
        "company_query": state.get("company_query"),
        "registration_number": state.get("registration_number")
    }
    
    # Evaluate the proposed transition
    evaluation = await guard.evaluate_action(action_type=f"transition_to_{next_node}", payload=payload)
    
    logs = [f"Safety Evaluation for {next_node}: {evaluation.reason}"]
    if evaluation.signature:
        logs.append(f"Action Signed. KYA-ID: {evaluation.action_id} | SIG: {evaluation.signature[:16]}...")

    # Handle escalation based on risk tiers
    requires_signoff = evaluation.requires_hitl
    
    if evaluation.risk_tier == RiskTier.HIGH:
        logs.append("CRITICAL: High-risk action detected. Mandatory human sign-off required.")
    elif evaluation.risk_tier == RiskTier.MEDIUM:
        logs.append("WARNING: Medium-risk action detected. Triggering human review via shared workspace.")

    # Log to immutable audit store
    audit_store.log_action(
        agent_id=guard.agent_id,
        action_id=evaluation.action_id,
        action_type=f"transition_to_{next_node}",
        risk_tier=evaluation.risk_tier.value,
        signature=evaluation.signature,
        authorized=evaluation.authorized,
        explanation=evaluation.explanation
    )

    return {
        "safety_evaluation": evaluation.model_dump(),
        "requires_human_signoff": requires_signoff,
        "logs": logs
    }

async def consent_management_node(state: AgentState) -> Dict[str, Any]:
    """Ensures consent is captured and logs the cryptographic proof."""
    company_id = state.get("registration_number") or state["company_query"]
    
    # Simulate capturing consent (in a real app, this would be an API call or UI interaction)
    # We'll assume the user provided 'storage' and 'selective_disclosure' consent
    scopes = state.get("consent_scope", ["storage", "selective_disclosure"])
    
    logs = []
    for scope in scopes:
        res = consent_manager.grant_consent(company_id, scope)
        logs.append(f"Consent GRANTED for scope: {scope}. Proof: {res['signature'][:16]}...")
        
    return {
        "consent_granted": True,
        "requires_human_signoff": False,
        "human_approval_granted": False,
        "logs": logs
    }

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

async def privacy_cleanup_and_ssi_node(state: AgentState) -> Dict[str, Any]:
    """Generates W3C VC and performs data minimization/cleanup."""
    results = state["results"]
    company_id = state.get("registration_number") or state["company_query"]
    logs = ["Initiating privacy cleanup and VC generation."]

    # 1. Generate Verifiable Credential
    # We selectively disclose only registration and sanctions status for the standard link
    selective_fields = ["company_name", "registration_status", "sanctions_check", "verification_date"]
    vc = ssi_issuer.generate_kyb_vc(results.model_dump(), selective_fields=selective_fields)
    wallet_link = ssi_issuer.generate_wallet_link(vc)
    
    logs.append(f"W3C Verifiable Credential generated. Wallet link: {wallet_link}")

    # 2. Data Minimization & Cleanup
    # If storage consent was NOT granted, we must delete ephemeral data
    # (In this mock, we assume 'storage' scope was checked)
    if "storage" not in state.get("consent_scope", []):
        logs.append("Storage consent not granted. Deleting ephemeral document data.")
        # Wipe sensitive ephemeral data from results
        state["results"].documents = []
        # In a real system, we'd also trigger deletion in the Vector DB/S3
        # vector_memory.delete_case(company_id) 
    else:
        logs.append("Storage consent active. Persisting investigation artifacts.")

    return {
        "vc_link": wallet_link,
        "results": state["results"],
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
