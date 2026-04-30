from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from enum import Enum

class Mode(str, Enum):
    REAL_TIME = "real_time"
    BATCH = "batch"

class KYBRequest(BaseModel):
    company_name: str = Field(..., description="Legal name of the company to investigate")
    jurisdiction: str = Field(..., description="Country or state code (e.g., US, GB, DE)")
    registration_number: Optional[str] = Field(None, description="Official registration number if known")
    mode: Mode = Field(Mode.REAL_TIME, description="Processing mode")
    webhook_url: Optional[HttpUrl] = Field(None, description="URL to receive completion and event notifications")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context or client identifiers")

class ReasoningStep(BaseModel):
    node: str
    message: str
    timestamp: float

class Evidence(BaseModel):
    source: str
    url: Optional[str] = None
    snippet: Optional[str] = None
    confidence: float

class KYBProfile(BaseModel):
    company_name: str
    status: str
    risk_score: float
    summary: str
    ownership_structure: List[Dict[str, Any]]
    sanctions_check: Dict[str, Any]
    evidence: List[Evidence]
    explanations: List[str]
    raw_data_refs: List[str]

class BatchKYBRequest(BaseModel):
    requests: List[KYBRequest]
    webhook_url: Optional[HttpUrl] = None

class KYBResponse(BaseModel):
    request_id: str
    status: str
    profile: Optional[KYBProfile] = None
    error: Optional[str] = None
