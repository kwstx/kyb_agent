import httpx
import asyncio
import json
import websockets
from typing import Optional, Dict, Any, AsyncGenerator

class KYBClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.ws_url = self.base_url.replace("http", "ws")
        self.http_client = httpx.AsyncClient()

    async def submit_request(self, company_name: str, jurisdiction: str, mode: str = "real_time", webhook_url: Optional[str] = None) -> str:
        payload = {
            "company_name": company_name,
            "jurisdiction": jurisdiction,
            "mode": mode,
            "webhook_url": webhook_url
        }
        response = await self.http_client.post(f"{self.base_url}/api/v1/kyb", json=payload)
        response.raise_for_status()
        return response.json()["request_id"]

    async def submit_batch(self, requests: List[Dict[str, Any]], webhook_url: Optional[str] = None) -> Dict[str, Any]:
        payload = {
            "requests": requests,
            "webhook_url": webhook_url
        }
        response = await self.http_client.post(f"{self.base_url}/api/v1/kyb/batch", json=payload)
        response.raise_for_status()
        return response.json()

    async def stream_investigation(self, request_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        async with websockets.connect(f"{self.ws_url}/api/v1/ws/{request_id}") as websocket:
            # Optionally send a start command if needed
            # await websocket.send(json.dumps({"action": "start", "request": ...}))
            
            async for message in websocket:
                yield json.loads(message)

    async def get_status(self, request_id: str) -> Dict[str, Any]:
        response = await self.http_client.get(f"{self.base_url}/api/v1/status/{request_id}")
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self.http_client.aclose()
