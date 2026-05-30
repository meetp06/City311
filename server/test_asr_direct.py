import asyncio
import os
import json
from dotenv import load_dotenv
from websockets.asyncio.client import connect

load_dotenv(override=True)

async def test_direct_asr():
    url = os.getenv("NVIDIA_ASR_URL", "ws://44.241.251.184:8080")
    print(f"Connecting to NVIDIA ASR WebSocket at: {url}")
    
    try:
        async with connect(url) as websocket:
            print("Successfully opened connection to ASR WebSocket!")
            
            # Wait for ready message
            print("Waiting for 'ready' message from server...")
            try:
                ready_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(ready_msg)
                print(f"Received initial message: {data}")
                if data.get("type") == "ready":
                    print("ASR Service is connected and ready to receive audio!")
                else:
                    print(f"Unexpected initial message type: {data.get('type')}")
            except asyncio.TimeoutError:
                print("Timed out waiting for 'ready' message, but connection is open.")
            
            # Send a reset message
            print("Testing sending a reset command...")
            reset_msg = {"type": "reset", "finalize": True}
            await websocket.send(json.dumps(reset_msg))
            print("Reset command sent successfully.")
            
            print("Connection test completed successfully!")
            
    except Exception as e:
        print(f"An error occurred while connecting to NVIDIA ASR: {e}")

if __name__ == "__main__":
    asyncio.run(test_direct_asr())
