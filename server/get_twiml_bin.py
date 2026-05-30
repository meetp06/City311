import os
import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

async def check_twiml_bin():
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    
    if not account_sid or not auth_token:
        print("Error: TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN is missing in the environment.")
        return
        
    bin_sid = "EH58165b0f2ee134854eda0096e89f530b"
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/TwiML/Bins/{bin_sid}.json"
    auth = (account_sid, auth_token)
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, auth=auth)
            if resp.status_code == 200:
                data = resp.json()
                print("Successfully retrieved TwiML Bin:")
                print(f"Friendly Name: {data.get('friendly_name')}")
                print(f"TwiML URL: {data.get('url')}")
                print("\nXML Code:")
                print(data.get('xml'))
            else:
                # If template API doesn't work directly, let's list them
                print(f"Status code: {resp.status_code}. Attempting to list all TwiML Bins...")
                list_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/TwiML/Bins.json"
                resp_list = await client.get(list_url, auth=auth)
                if resp_list.status_code == 200:
                    data = resp_list.json()
                    bins = data.get("twiml_bins", [])
                    for b in bins:
                        print(f"\nBin SID: {b.get('sid')}")
                        print(f"Friendly Name: {b.get('friendly_name')}")
                        print("XML:")
                        print(b.get('xml'))
                else:
                    print(f"Failed to list TwiML bins. Status: {resp_list.status_code}")
                    print(resp_list.text)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(check_twiml_bin())
