from typing import List, Optional, Dict, Any, Annotated, TypedDict
from pydantic import BaseModel, Field
import operator

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

class AgentState(TypedDict):
    # LangGraph state typically uses TypedDict
    company_query: str
    registration_number: Optional[str]
    uploaded_docs: List[str] # Paths or IDs
    plan: List[str]
    current_task: Optional[str]
    results: KYBProfile
    # Use Annotated with operator.add for lists to append instead of overwrite if needed
    logs: Annotated[List[str], operator.add]
    next_node: str # For routing
