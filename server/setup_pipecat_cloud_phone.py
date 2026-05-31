import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

async def setup():
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    
    if not account_sid or not auth_token:
        print("Error: TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN is missing in the environment.")
        return
        
    dashboard_url = os.getenv("DASHBOARD_URL", "https://your-ngrok-subdomain.ngrok-free.dev")
    webhook_url = f"{dashboard_url}/twilio/voice"
    print(f"Setting Twilio Voice Webhook URL to: {webhook_url}")
    
    # Get the SID of our phone number +19564764454
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
        
        payload = {
            "VoiceUrl": webhook_url,
            "VoiceMethod": "POST"
        }
        
        resp_update = await client.post(update_url, auth=auth, data=payload)
        if resp_update.status_code == 200:
            print("Twilio phone number webhook URL updated successfully to point to Pipecat Cloud proxy endpoint!")
        else:
            print(f"Failed to update Twilio number: {resp_update.status_code}")
            print(resp_update.text)

if __name__ == "__main__":
    asyncio.run(setup())
