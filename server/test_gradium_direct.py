import asyncio
import os
import json
import base64
from dotenv import load_dotenv
from websockets.asyncio.client import connect

load_dotenv(override=True)

async def test_direct_gradium():
    api_key = os.environ.get("GRADIUM_API_KEY")
    voice_id = os.getenv("GRADIUM_VOICE_ID", "Eu9iL_CYe8N-Gkx_")
    if not voice_id or not voice_id.strip():
        voice_id = "Eu9iL_CYe8N-Gkx_"
        
    url = "wss://api.gradium.ai/api/speech/tts"
    headers = {
        "x-api-key": api_key,
        "x-api-source": "test-script"
    }
    
    print(f"Connecting to Gradium: {url}")
    print(f"Using Voice ID: {voice_id}")
    print(f"Using API Key: {api_key[:10]}...")
    
    try:
        async with connect(url, additional_headers=headers) as websocket:
            print("Successfully connected to Gradium WebSocket!")
            
            # Send setup message
            setup_msg = {
                "type": "setup",
                "output_format": "pcm",
                "voice_id": voice_id,
                "close_ws_on_eos": False,
                "client_req_id": "test-direct-ctx"
            }
            await websocket.send(json.dumps(setup_msg))
            print("Sent setup message.")
            
            # Send text message
            text_msg = {
                "type": "text",
                "text": "Hello, this is a live test of the Gradium Text-to-Speech service. Everything looks good!",
                "client_req_id": "test-direct-ctx"
            }
            await websocket.send(json.dumps(text_msg))
            print("Sent text message.")
            
            # Send end_of_stream message
            eos_msg = {
                "type": "end_of_stream",
                "client_req_id": "test-direct-ctx"
            }
            await websocket.send(json.dumps(eos_msg))
            print("Sent end-of-stream message.")
            
            # Receive response frames
            audio_frames_received = 0
            total_audio_bytes = 0
            
            while True:
                message = await websocket.recv()
                msg = json.loads(message)
                msg_type = msg.get("type")
                
                print(f"Received message type: {msg_type}")
                
                if msg_type == "audio":
                    audio_data = base64.b64decode(msg["audio"])
                    audio_frames_received += 1
                    total_audio_bytes += len(audio_data)
                elif msg_type == "end_of_stream":
                    print("Received end_of_stream from server. Finished synthesis.")
                    break
                elif msg_type == "error":
                    print(f"Received error from server: {msg}")
                    break
                elif msg_type == "text":
                    print(f"Word timestamp: {msg.get('text')} at {msg.get('start_s')}s")
                    
            print(f"Success! Received {audio_frames_received} audio frames, total {total_audio_bytes} bytes.")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(test_direct_gradium())
