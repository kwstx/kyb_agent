from typing import Optional, Type, Dict, Any
from pydantic import BaseModel, Field
import httpx
from .base import BaseResilientTool
from .secrets import secrets_manager

class CorporateSearchSchema(BaseModel):
    company_name: str = Field(description="The name of the company to search for")
    jurisdiction: Optional[str] = Field(None, description="The jurisdiction code (e.g., 'gb', 'us_de')")

class CorporateRegistryTool(BaseResilientTool):
    name: str = "corporate_registry_search"
    description: str = "Search for company details in global corporate registries via OpenCorporates."
    args_schema: Type[BaseModel] = CorporateSearchSchema

    def _run(self, company_name: str, jurisdiction: Optional[str] = None) -> Dict[str, Any]:
        api_key = secrets_manager.get_secret("OPENCORPORATES_API_KEY")
        base_url = "https://api.opencorporates.com/v0.4/companies/search"
        
        params = {"q": company_name}
        if jurisdiction:
            params["jurisdiction_code"] = jurisdiction
        if api_key:
            params["api_token"] = api_key

        def fetch():
            with httpx.Client(timeout=30.0) as client:
                response = client.get(base_url, params=params)
                response.raise_for_status()
                return response.json()

        return self._run_with_resilience(fetch)

class CompanyDetailsSchema(BaseModel):
    company_number: str = Field(description="The registration number of the company")
    jurisdiction: str = Field(description="The jurisdiction code (e.g., 'gb')")

class CorporateDetailsTool(BaseResilientTool):
    name: str = "corporate_registry_details"
    description: str = "Get detailed information about a specific company from corporate registries."
    args_schema: Type[BaseModel] = CompanyDetailsSchema

    def _run(self, company_number: str, jurisdiction: str) -> Dict[str, Any]:
        api_key = secrets_manager.get_secret("OPENCORPORATES_API_KEY")
        url = f"https://api.opencorporates.com/v0.4/companies/{jurisdiction}/{company_number}"
        
        params = {}
        if api_key:
            params["api_token"] = api_key

        def fetch():
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                return response.json()

        return self._run_with_resilience(fetch)
