import os
import time
import json
import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

async def setup():
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    
    if not account_sid or not auth_token:
        print("Error: TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN is missing in the environment.")
        return
        
    print("Step 1: Starting ngrok tunnel on port 7860...")
    # Start ngrok in background
    import subprocess
    # Run ngrok as a background process redirecting output to prevent blocking
    ngrok_proc = subprocess.Popen(
        ["ngrok", "http", "7860"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait for ngrok to spin up
    time.sleep(3.0)
    
    # Query ngrok local API to get the public URL
    print("Step 2: Retrieving public ngrok URL...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:4040/api/tunnels")
            if resp.status_code == 200:
                tunnels = resp.json().get("tunnels", [])
                if not tunnels:
                    print("Error: No active ngrok tunnels found. Is your ngrok authenticated?")
                    return
                # Look for the public https URL
                public_url = None
                for t in tunnels:
                    if t.get("proto") == "https":
                        public_url = t.get("public_url")
                        break
                if not public_url:
                    public_url = tunnels[0].get("public_url")
                
                print(f"Active ngrok tunnel URL: {public_url}")
            else:
                print(f"Error calling ngrok API: {resp.status_code}")
                return
    except Exception as e:
        print(f"Could not connect to ngrok local API: {e}")
        print("Please check if ngrok is running and try again.")
        return
        
    # Extract hostname
    ngrok_host = public_url.replace("https://", "").replace("http://", "")
    
    # Step 3: Update Twilio Incoming Phone Number webhook
    print(f"Step 3: Updating Twilio number +19564764454 webhook to point to https://{ngrok_host}/")
    phone_number_sid = None
    list_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/IncomingPhoneNumbers.json"
    auth = (account_sid, auth_token)
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(list_url, auth=auth)
        if resp.status_code == 200:
            numbers = resp.json().get("incoming_phone_numbers", [])
            for num in numbers:
                if num.get("phone_number") == "+19564764454":
                    phone_number_sid = num.get("sid")
                    break
        else:
            print(f"Error listing phone numbers: {resp.status_code}")
            return
            
        if not phone_number_sid:
            print("Error: Could not find Twilio Phone Number SID for +19564764454.")
            return
            
        print(f"Found phone number SID: {phone_number_sid}")
        update_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/IncomingPhoneNumbers/{phone_number_sid}.json"
        
        # We point Twilio directly to the root of the ngrok host POST endpoint (where the bot serves the TwiML response)
        payload = {
            "VoiceUrl": f"https://{ngrok_host}/",
            "VoiceMethod": "POST"
        }
        
        resp_update = await client.post(update_url, auth=auth, data=payload)
        if resp_update.status_code == 200:
            print("Twilio phone number webhook URL updated successfully!")
        else:
            print(f"Failed to update Twilio number: {resp_update.status_code}")
            print(resp_update.text)
            return

    print("\n--- Setup Complete ---")
    print(f"1. Twilio calls to (956) 476-4454 will now route to your local bot.")
    print(f"2. Restart the voice bot with the command:")
    print(f"   uv run bot-nemotron.py -t twilio -x {ngrok_host}")
    print("----------------------\n")

if __name__ == "__main__":
    import asyncio
    asyncio.run(setup())
