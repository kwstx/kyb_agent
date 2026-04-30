from typing import List, Optional, Dict, Any, Annotated, TypedDict
from pydantic import BaseModel, Field
import operator
import datetime

class AudienceSummary(BaseModel):
    compliance_officer: str
    regulator: str

class XAIArtifact(BaseModel):
    chain_of_thought: List[Dict[str, Any]]
    sources: List[Dict[str, str]] # [{ "source": "registry", "citation": "..." }]
    confidence_calibration: Dict[str, Any] # { "score": 0.95, "method": "direct_llm", "uncertainty_factors": [...] }
    feature_importance: Dict[str, float] # SHAP/LIME style weights for key risk factors
    summaries: AudienceSummary
    timestamp: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat())

class RegistryData(BaseModel):
    company_name: str
    registration_number: Optional[str]
    status: str
    jurisdiction: str
    incorporation_date: Optional[str]
    raw_data: Dict[str, Any]

class OwnershipEntity(BaseModel):
    name: str
    type: str  # Individual, Corporate
    percentage: float
    is_ubo: bool

class OwnershipStructure(BaseModel):
    entities: List[OwnershipEntity]
    layers: int
    resolved: bool

class DocumentChunk(BaseModel):
    text: str
    metadata: Dict[str, Any] # page, doc_type, confidence, etc.

class DocumentEvidence(BaseModel):
    doc_type: str
    findings: List[str]
    confidence: float
    chunks: List[DocumentChunk] = Field(default_factory=list)
    source_files: List[str] = Field(default_factory=list)

class RiskRating(BaseModel):
    score: float # 0.0 to 1.0
    factors: List[str]
    summary: str

class KYBProfile(BaseModel):
    registry: Optional[RegistryData] = None
    ownership: Optional[OwnershipStructure] = None
    documents: List[DocumentEvidence] = Field(default_factory=list)
    risk_assessment: Optional[RiskRating] = None
    entities_resolved: bool = False
    xai_report: Optional[XAIArtifact] = None
    signature: Optional[str] = None # Digital signature of the JSON artifact

class AgentState(TypedDict):
    # LangGraph state typically uses TypedDict
    company_query: str
    registration_number: Optional[str]
    uploaded_docs: List[str] # Paths or IDs
    plan: List[str]
    current_task: Optional[str]
    results: KYBProfile
    # Reasoning fields
    reasoning_history: Annotated[List[Dict[str, Any]], operator.add]
    hypotheses: Annotated[List[Dict[str, Any]], operator.add]
    # Use Annotated with operator.add for lists to append instead of overwrite if needed
    logs: Annotated[List[str], operator.add]
    next_node: str # For routing
    # Privacy & SSI
    consent_scope: List[str] # ["storage", "disclosure", "selective_sanctions"]
    consent_granted: bool
    vc_link: Optional[str]
