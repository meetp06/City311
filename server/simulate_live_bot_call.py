import asyncio
import os
import httpx
import uuid
import time

async def simulate_call():
    backend_url = "http://localhost:7861"
    call_id = f"call_sim_{uuid.uuid4().hex[:6]}"
    
    print(f"Simulating call: {call_id} to backend: {backend_url}")
    
    # 1. Call started
    payload_start = {
        "event_type": "call_started",
        "call_id": call_id,
        "data": {
            "caller_phone": "+1 (555) 901-3829"
        }
    }
    
    async with httpx.AsyncClient() as client:
        # Send call started
        print("Sending call_started...")
        r = await client.post(f"{backend_url}/api/webhook/event", json=payload_start)
        print(f"  Response: {r.status_code}")
        await asyncio.sleep(2.0)
        
        # 2. Assistant greets
        payload_greet = {
            "event_type": "transcript_added",
            "call_id": call_id,
            "data": {
                "role": "assistant",
                "text": "Hello, you've reached City 311. How can I help you today?"
            }
        }
        print("Sending assistant greeting...")
        r = await client.post(f"{backend_url}/api/webhook/event", json=payload_greet)
        print(f"  Response: {r.status_code}")
        await asyncio.sleep(3.0)
        
        # 3. Citizen speaks
        payload_citizen = {
            "event_type": "transcript_added",
            "call_id": call_id,
            "data": {
                "role": "citizen",
                "text": "Hi, there is a water leak at 400 Oak Avenue. Water is spraying everywhere."
            }
        }
        print("Sending citizen transcript...")
        r = await client.post(f"{backend_url}/api/webhook/event", json=payload_citizen)
        print(f"  Response: {r.status_code}")
        await asyncio.sleep(3.0)
        
        # 4. Tool call: report water leak
        payload_tool = {
            "event_type": "tool_called",
            "call_id": call_id,
            "data": {
                "tool": "report_water_leak",
                "args": {
                    "location": "400 Oak Avenue",
                    "severity": "severe"
                },
                "result": {
                    "ok": True,
                    "ticket_id": "WTR-99999",
                    "priority": "urgent"
                },
                "status": "success"
            }
        }
        print("Sending tool_called...")
        r = await client.post(f"{backend_url}/api/webhook/event", json=payload_tool)
        print(f"  Response: {r.status_code}")
        
        # 5. Ticket created
        payload_ticket = {
            "event_type": "ticket_created",
            "call_id": call_id,
            "data": {
                "ticket_id": "WTR-99999",
                "category": "Water Leak",
                "location": "400 Oak Avenue",
                "description": "Water leak reported. Severity: severe.",
                "status": "open",
                "priority": "urgent"
            }
        }
        print("Sending ticket_created...")
        r = await client.post(f"{backend_url}/api/webhook/event", json=payload_ticket)
        print(f"  Response: {r.status_code}")
        await asyncio.sleep(3.0)
        
        # 6. Assistant responds with ticket
        payload_response = {
            "event_type": "transcript_added",
            "call_id": call_id,
            "data": {
                "role": "assistant",
                "text": "I've filed an urgent water leak ticket WTR-99999 for 400 Oak Avenue. A crew will be dispatched."
            }
        }
        print("Sending assistant ticket confirmation...")
        r = await client.post(f"{backend_url}/api/webhook/event", json=payload_response)
        print(f"  Response: {r.status_code}")
        await asyncio.sleep(2.0)
        
        # 7. Call ended
        payload_end = {
            "event_type": "call_ended",
            "call_id": call_id,
            "data": {}
        }
        print("Sending call_ended...")
        r = await client.post(f"{backend_url}/api/webhook/event", json=payload_end)
        print(f"  Response: {r.status_code}")

if __name__ == "__main__":
    asyncio.run(simulate_call())
