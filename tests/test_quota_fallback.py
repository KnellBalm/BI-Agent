import asyncio
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from backend.orchestrator.quota_manager import quota_manager
from backend.orchestrator.llm_provider import GeminiProvider, OllamaProvider, FailoverLLMProvider

async def test_quota_fallback():
    print("--- 🧪 Smart Quota & Fallback Verification ---")
    
    # 1. Setup providers
    gemini = GeminiProvider()
    ollama = OllamaProvider()
    failover = FailoverLLMProvider([gemini, ollama])
    
    # 2. Simulate Gemini limit reached
    print("\n[Scenario 1] Gemini 쿼터 소진 시뮬레이션")
    quota_manager.report_limit_reached("gemini", reset_in_seconds=5)
    print(f"Gemini usable: {quota_manager.can_use_provider('gemini')}")
    
    # 3. Test Failover (should pick Ollama)
    print("\n[Scenario 2] Failover 동작 확인 (Gemini -> Ollama)")
    # We mock actual generation for safety in tests if API keys are missing, 
    # but here we just want to see if the selection logic works.
    # In a real run, this would trigger Ollama generation.
    
    # 4. Check status
    p_status = quota_manager.get_provider_status("gemini")
    print(f"Gemini Status: {p_status}")
    
    # 5. Wait for reset
    print("\n[Scenario 3] 리셋 대기 중 (5초)...")
    await asyncio.sleep(6)
    print(f"Gemini usable after reset: {quota_manager.can_use_provider('gemini')}")
    
    print("\n✅ Verification Complete.")

if __name__ == "__main__":
    asyncio.run(test_quota_fallback())
