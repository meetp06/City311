import asyncio
import os
import aiohttp
from dotenv import load_dotenv

load_dotenv(override=True)

async def test_direct_nemotron():
    url = os.getenv("NEMOTRON_LLM_URL", "http://nemotron-fleet-alb-1322439314.us-west-2.elb.amazonaws.com/v1")
    model = os.getenv("NEMOTRON_LLM_MODEL", "nvidia/nemotron-3-super")
    api_key = os.getenv("NEMOTRON_LLM_API_KEY", "EMPTY")
    
    print(f"Connecting to Nemotron LLM at: {url}")
    print(f"Using Model: {model}")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Hello, who are you? Answer in one short sentence."}
        ],
        "max_tokens": 300,
        "temperature": 0.7
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{url}/chat/completions", headers=headers, json=payload) as response:
                print(f"Response status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print("Successfully received completion response!")
                    import pprint
                    pprint.pprint(data)
                    if 'choices' in data and data['choices']:
                        choice = data['choices'][0]
                        if 'message' in choice and 'content' in choice['message']:
                            print(f"Response content: {choice['message']['content']}")
                        else:
                            print(f"Message content not found in choice: {choice}")
                    else:
                        print(f"Choices not found in response: {data}")
                else:
                    error_text = await response.text()
                    print(f"Failed to query LLM. Status: {response.status}. Error: {error_text}")
    except Exception as e:
        print(f"An error occurred while connecting to Nemotron LLM: {e}")

if __name__ == "__main__":
    asyncio.run(test_direct_nemotron())
