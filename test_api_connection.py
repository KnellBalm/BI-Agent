import asyncio
import os
from dotenv import load_dotenv
import google.generativeai as genai

async def check_api():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    print(f"Checking API Key: {api_key[:10]}...")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('models/gemini-2.0-flash')
    
    try:
        response = await asyncio.to_thread(model.generate_content, "Hello, are you active?")
        print(f"Response: {response.text}")
        print("✅ API Key is working!")
    except Exception as e:
        print(f"❌ API Key failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_api())
