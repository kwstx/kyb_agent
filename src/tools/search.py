from typing import Optional, Type, Dict, Any, List
from pydantic import BaseModel, Field
from .base import BaseResilientTool
from .secrets import secrets_manager
from langchain_community.tools.tavily_search import TavilySearchResults
import os

class AdverseMediaSearchSchema(BaseModel):
    query: str = Field(description="The search query for adverse media (e.g., 'Company Name fraud investigation')")
    max_results: int = Field(5, description="Maximum number of search results to return")

class WebSearchTool(BaseResilientTool):
    name: str = "web_search_adverse_media"
    description: str = "Search the web for adverse media, news, and unstructured data related to a company."
    args_schema: Type[BaseModel] = AdverseMediaSearchSchema

    def _run(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        api_key = secrets_manager.get_secret("TAVILY_API_KEY")
        if api_key:
            os.environ["TAVILY_API_KEY"] = api_key

        def fetch():
            tavily = TavilySearchResults(max_results=max_results)
            return tavily.invoke({"query": query})

        return self._run_with_resilience(fetch)
