import asyncio
import os
from backend.orchestrator.llm_provider import GeminiProvider, OllamaProvider, FailoverLLMProvider
from backend.orchestrator import QuotaManager

async def test_failover():
    print("=== Failover Test: Gemini to Ollama ===")
    
    # 1. QuotaManager (uses default auth_manager.home_dir / usage_cache.json)
    qm = QuotaManager()
    
    gemini = GeminiProvider(quota_manager=qm)
    ollama = OllamaProvider(model_name="llama3") # Ollama must be running locally
    
    llm = FailoverLLMProvider(providers=[gemini, ollama])
    
    print("\n[Test 1] Generating with Failover...")
    try:
        # This should fail on Gemini (no keys) and fallback to Ollama
        response = await llm.generate("Hello, are you Ollama or Gemini?")
        print(f"Response: {response}")
    except Exception as e:
        print(f"Test failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(test_failover())
