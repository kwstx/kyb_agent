import asyncio
import os
import sys
from sdk.python.kyb_sdk import KYBClient
import uvicorn
import threading
import time

async def run_sdk_demo():
    print("Starting KYB API and SDK Demo...")
    
    # 1. Start the API in a background thread
    from src.api.app import app
    def start_api():
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")
    
    api_thread = threading.Thread(target=start_api, daemon=True)
    api_thread.start()
    
    # Give the API a moment to start
    time.sleep(2)
    
    # 2. Initialize SDK Client
    client = KYBClient(base_url="http://127.0.0.1:8000")
    
    # 3. Submit a KYB Request
    print("\nSubmitting KYB Request for 'Antigravity AI Corp'...")
    request_id = await client.submit_request(
        company_name="Antigravity AI Corp",
        jurisdiction="US",
        mode="real_time"
    )
    print(f"Request Submitted. ID: {request_id}")
    
    # 4. Stream Intermediate Reasoning Steps
    print("\nStreaming Reasoning Steps:")
    try:
        async for step in client.stream_investigation(request_id):
            if step.get("type") == "intermediate_step":
                node = step.get("node")
                data = step.get("data", {})
                logs = data.get("logs", [])
                
                print(f"\n[NODE: {node}]")
                for log in logs:
                    print(f"  > {log}")
            
            elif step.get("status") == "completed":
                print("\nInvestigation Completed!")
                profile = step.get("profile")
                print(f"Final Status: {profile.get('status', 'N/A')}")
                print(f"Risk Score: {profile.get('risk_assessment', {}).get('score', 'N/A')}")
                break
    except Exception as e:
        print(f"❌ Error during streaming: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(run_sdk_demo())
