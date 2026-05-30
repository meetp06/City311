import os
import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

async def check_twilio():
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    
    if not account_sid or not auth_token:
        print("Error: TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN is missing in the environment.")
        return
        
    print(f"Twilio Account SID: {account_sid}")
    
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/IncomingPhoneNumbers.json"
    auth = (account_sid, auth_token)
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, auth=auth)
            if resp.status_code == 200:
                data = resp.json()
                print("Successfully retrieved incoming phone numbers:")
                numbers = data.get("incoming_phone_numbers", [])
                for num in numbers:
                    print(f"\nPhone Number: {num.get('phone_number')}")
                    print(f"  Friendly Name: {num.get('friendly_name')}")
                    print(f"  Voice URL: {num.get('voice_url')}")
                    print(f"  Voice Method: {num.get('voice_method')}")
                    print(f"  SMS URL: {num.get('sms_url')}")
            else:
                print(f"Failed to fetch phone numbers. Status code: {resp.status_code}")
                print(resp.text)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(check_twilio())
