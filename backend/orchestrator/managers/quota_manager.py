import os
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .auth_manager import auth_manager

logger = logging.getLogger(__name__)

class QuotaManager:
    """
    모든 LLM 공급자의 할당량(Quota) 및 구독 혜택을 통합 관리하는 클래스.
    '과금 제로(Zero-Billing)' 정책을 위해 실시간 사용량을 트래킹하고 Fallback 시점을 결정합니다.
    """
    def __init__(self):
        self.usage_cache_path = auth_manager.home_dir / "usage_cache.json"
        self.usage_data = self._load_usage_cache()
        self.mcp_client = None
        self.gcp_server_path = os.path.abspath("backend/mcp_servers/gcp_manager_server.js")

    def _load_usage_cache(self) -> Dict[str, Any]:
        """로컬 캐시에서 사용량 정보를 로드합니다."""
        if os.path.exists(self.usage_cache_path):
            try:
                with open(self.usage_cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "providers" not in data:
                        return self._create_default_usage()
                    return data
            except Exception:
                pass
        return self._create_default_usage()

    def _create_default_usage(self) -> Dict[str, Any]:
        return {
            "providers": {
                "gemini": {"exhausted": False, "reset_at": None, "daily_count": 0, "limit": 1500, "last_reset": datetime.now().isoformat()},
                "claude": {"exhausted": False, "reset_at": None, "daily_count": 0, "limit": 50, "last_reset": datetime.now().isoformat()},
                "openai": {"exhausted": False, "reset_at": None, "daily_count": 0, "limit": 100, "last_reset": datetime.now().isoformat()},
                "ollama": {"exhausted": False, "reset_at": None, "daily_count": 0, "limit": 999999, "last_reset": datetime.now().isoformat()}
            },
            "last_sync": datetime.now().isoformat()
        }

    def _save_usage_cache(self):
        try:
            with open(self.usage_cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.usage_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save usage cache: {e}")

    def get_provider_status(self, provider: str) -> Dict[str, Any]:
        """특정 공급자의 현재 할당량 상태를 반환합니다."""
        status = self.usage_data["providers"].get(provider, {"exhausted": True})
        
        # 리셋 시간 확인 로직 (초 단위 간략화)
        if status.get("exhausted") and status.get("reset_at"):
            reset_dt = datetime.fromisoformat(status["reset_at"])
            if datetime.now() > reset_dt:
                status["exhausted"] = False
                status["reset_at"] = None
                self._save_usage_cache()
        
        return status

    def can_use_provider(self, provider: str) -> bool:
        """해당 공급자를 과금 없이 사용할 수 있는지 확인합니다."""
        status = self.get_provider_status(provider)
        if status.get("exhausted"):
            return False
        
        # 일일 한도 체크 (Zero-Billing 마진 포함)
        if status.get("daily_count", 0) >= status.get("limit", 1500):
            return False
            
        return True

    def increment_usage(self, provider: str):
        """사용량을 1회 증가시킵니다."""
        if provider not in self.usage_data["providers"]:
            self.usage_data["providers"][provider] = {"exhausted": False, "daily_count": 0}
        
        # 날짜 기반 카운트 리셋
        today = datetime.now().strftime("%Y-%m-%d")
        last_date = self.usage_data["providers"][provider].get("last_date")
        
        if last_date != today:
            self.usage_data["providers"][provider]["daily_count"] = 1
            self.usage_data["providers"][provider]["last_date"] = today
        else:
            self.usage_data["providers"][provider]["daily_count"] += 1
            
        self._save_usage_cache()

    def report_limit_reached(self, provider: str, reset_in_seconds: int = 60):
        """429 에러 등을 받았을 때 소진 상태로 기록합니다."""
        if provider not in self.usage_data["providers"]:
            self.usage_data["providers"][provider] = {}
            
        import datetime as dt
        self.usage_data["providers"][provider]["exhausted"] = True
        reset_time = datetime.now() + dt.timedelta(seconds=reset_in_seconds)
        self.usage_data["providers"][provider]["reset_at"] = reset_time.isoformat()
        self._save_usage_cache()
        logger.warning(f"Provider {provider} limit reached. Reset at {reset_time}")

    async def sync_with_gcp(self, project_id: str):
        # TODO: GCP 특정 할당량 동기화 로직 유지 (기존 코드 참고)
        pass

    async def close(self):
        if self.mcp_client:
            await self.mcp_client.disconnect()

quota_manager = QuotaManager()
