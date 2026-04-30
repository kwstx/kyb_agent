import uuid
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from src.api.v1.schemas import KYBRequest, KYBResponse, Mode
from src.graph import create_kyb_graph
from typing import Dict, List
import httpx

app = FastAPI(
    title="Antigravity KYB API",
    description="REST + WebSocket API for Autonomous KYB Investigations",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for active sessions (for demo purposes, use Redis in production)
active_tasks: Dict[str, asyncio.Task] = {}
graph = create_kyb_graph()

async def notify_webhook(url: str, payload: dict):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json=payload)
        except Exception as e:
            print(f"Failed to notify webhook {url}: {e}")

async def run_kyb_investigation(request_id: str, request: KYBRequest, websocket: WebSocket = None):
    # Prepare initial state
    initial_state = {
        "company_query": request.company_name,
        "jurisdiction": request.jurisdiction,
        "registration_number": request.registration_number,
        "uploaded_docs": [],
        "plan": ["gather_registry_data", "map_ownership", "assess_risk"],
        "results": {
            "registry": None,
            "ownership": None,
            "documents": [],
            "risk_assessment": None,
            "entities_resolved": False
        },
        "reasoning_history": [],
        "hypotheses": [],
        "logs": ["Initial request received."],
        "next_node": "gather_registry_data",
        "consent_scope": ["storage", "disclosure"],
        "consent_granted": False,
        "requires_human_signoff": False,
        "human_approval_granted": False
    }
    
    config = {"configurable": {"thread_id": request_id}}
    
    try:
        # Stream intermediate steps
        async for event in graph.astream(initial_state, config=config):
            # Extract node and data
            for node, data in event.items():
                step_info = {
                    "request_id": request_id,
                    "type": "intermediate_step",
                    "node": node,
                    "data": {
                        "logs": data.get("logs", []),
                        "next_node": data.get("next_node")
                    }
                }
                
                if websocket:
                    await websocket.send_json(step_info)
        
        # Once finished, send final response
        state = await graph.aget_state(config)
        final_results = state.values.get("results")
        
        # Convert Pydantic models in results to dicts if they aren't already
        def serialize(obj):
            if hasattr(obj, "dict"):
                return obj.dict()
            if isinstance(obj, list):
                return [serialize(i) for i in obj]
            if isinstance(obj, dict):
                return {k: serialize(v) for k, v in obj.items()}
            return obj

        response_profile = serialize(final_results)
        
        response = {
            "request_id": request_id,
            "status": "completed",
            "profile": response_profile
        }
        
        if websocket:
            await websocket.send_json(response)
            
        if request.webhook_url:
            await notify_webhook(str(request.webhook_url), response)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_resp = {"request_id": request_id, "status": "error", "error": str(e)}
        if websocket:
            await websocket.send_json(error_resp)
        if request.webhook_url:
            await notify_webhook(str(request.webhook_url), error_resp)
    finally:
        if request_id in active_tasks:
            del active_tasks[request_id]

@app.post("/api/v1/kyb", response_model=KYBResponse)
async def create_kyb_task(request: KYBRequest, background_tasks: BackgroundTasks):
    request_id = str(uuid.uuid4())
    
    if request.mode == Mode.REAL_TIME:
        # For real-time, the client is expected to connect via WebSocket
        # but we return the ID immediately
        return KYBResponse(request_id=request_id, status="accepted")
    else:
        # Batch mode: just start it in background
        background_tasks.add_task(run_kyb_investigation, request_id, request)
        return KYBResponse(request_id=request_id, status="queued")

@app.websocket("/api/v1/ws/{request_id}")
async def websocket_endpoint(websocket: WebSocket, request_id: str):
    await websocket.accept()
    try:
        # Wait for the client to send the initial request if they haven't POSTed yet
        # or just listen for instructions. 
        # For simplicity, we assume they POSTed first and are now connecting to listen.
        
        # Here we could wait for the task to be associated with this WS
        # and pipe the events.
        
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg.get("action") == "start":
                # If they want to start via WS
                req_data = msg.get("request")
                kyb_req = KYBRequest(**req_data)
                asyncio.create_task(run_kyb_investigation(request_id, kyb_req, websocket))
            
    except WebSocketDisconnect:
        print(f"Client disconnected from {request_id}")

from src.api.v1.schemas import KYBRequest, KYBResponse, Mode, BatchKYBRequest

@app.post("/api/v1/kyb/batch")
async def create_kyb_batch(batch_request: BatchKYBRequest, background_tasks: BackgroundTasks):
    batch_id = str(uuid.uuid4())
    request_ids = []
    
    for req in batch_request.requests:
        request_id = str(uuid.uuid4())
        request_ids.append(request_id)
        # Force batch mode for items in batch request
        req.mode = Mode.BATCH
        background_tasks.add_task(run_kyb_investigation, request_id, req)
    
    return {
        "batch_id": batch_id,
        "request_ids": request_ids,
        "status": "processing"
    }

@app.get("/api/v1/status/{request_id}", response_model=KYBResponse)
async def get_status(request_id: str):
    # In a real app, check DB/Checkpointer
    return KYBResponse(request_id=request_id, status="processing")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
