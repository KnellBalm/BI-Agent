import os
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.agents.data_source.mcp_client import MCPClient

from backend.orchestrator.auth_manager import auth_manager

logger = logging.getLogger(__name__)

class QuotaManager:
    """
    Gemini API 할당량 및 과금 관리를 담당하는 클래스
    """
    def __init__(self, config_str: Optional[str] = None):
        self.configs = self._parse_config(config_str)
        self.current_index = 0
        # 사용자 홈 디렉토리의 .bi-agent 폴더를 사용하도록 변경
        self.usage_cache_path = auth_manager.home_dir / "usage_cache.json"
        self.usage_data = self._load_usage_cache()
        self.mcp_client = None
        self.gcp_server_path = os.path.abspath("backend/mcp_servers/gcp_manager_server.js")

    def _parse_config(self, config_str: Optional[str]) -> List[Dict[str, Any]]:
        if not config_str:
            # auth_manager에서 키를 가져와서 동적으로 설정 생성
            key = auth_manager.get_gemini_key()
            if key:
                return [{"key": key, "type": "free", "name": "Default User Key"}]
            config_str = os.getenv("GEMINI_API_CONFIGS", "[]")
        try:
            return json.loads(config_str)
        except json.JSONDecodeError:
            logger.error("Failed to parse GEMINI_API_CONFIGS. Ensure it is a valid JSON list.")
            return []

    def _load_usage_cache(self) -> Dict[str, Any]:
        if os.path.exists(self.usage_cache_path):
            try:
                with open(self.usage_cache_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"keys": {}, "last_sync": None}

    def _save_usage_cache(self):
        with open(self.usage_cache_path, 'w') as f:
            json.dump(self.usage_data, f, indent=2)

    async def _init_mcp(self):
        if not self.mcp_client:
            self.mcp_client = MCPClient(self.gcp_server_path)
            await self.mcp_client.connect()

    async def sync_with_gcp(self, project_id: str):
        """GCP API를 통해 실시간 할당량 및 결제 정보를 동기화합니다."""
        await self._init_mcp()
        try:
            # 1. 할당량 조회
            quota_res = await self.mcp_client.call_tool("get_quota_usage", {"projectId": project_id})
            # 2. 결제 정보 조회
            billing_res = await self.mcp_client.call_tool("get_billing_info", {"projectId": project_id})
            
            # MCP 결과에서 텍스트 추출 및 JSON 파싱
            def parse_mcp_res(res):
                if hasattr(res, 'content') and len(res.content) > 0:
                    try:
                        return json.loads(res.content[0].text)
                    except (AttributeError, json.JSONDecodeError):
                        return str(res.content[0])
                return str(res)

            quota_data = parse_mcp_res(quota_res)
            billing_data = parse_mcp_res(billing_res)
            
            self.usage_data["last_sync"] = datetime.now().isoformat()
            self.usage_data["quota_sync_raw"] = quota_data
            self.usage_data["billing_info"] = billing_data
            self._save_usage_cache()
            logger.info(f"Synced with GCP for project {project_id}")
        except Exception as e:
            logger.error(f"GCP Sync failed: {e}")
            logger.error(f"GCP Sync failed: {e}")

    async def get_active_key_config(self) -> Optional[Dict[str, Any]]:
        """사용 가능한 최적의 키 설정을 반환합니다."""
        if not self.configs:
            return None

        # 가용한 키를 찾을 때까지 순환
        for _ in range(len(self.configs)):
            idx = self.current_index % len(self.configs)
            config = self.configs[idx]
            key_id = config.get("key")
            
            # 차단 여부 확인 (429 에러 기록 등)
            if not self.usage_data["keys"].get(key_id, {}).get("exhausted", False):
                # 유료 키의 경우 추가 체크 (Daily Limit 등)
                if config.get("type") == "paid":
                    # 모델별 안전 기본 한도 설정
                    model_name = os.getenv("GEMINI_MODEL", "flash").lower()
                    if "pro" in model_name:
                        default_limit = 45 # Pro 무료 한도 50회 대비 마진
                    else:
                        default_limit = 1400 # Flash 무료 한도 1,500회 대비 마진

                    daily_limit = config.get("daily_limit", default_limit) 
                    current_usage = self.usage_data["keys"].get(key_id, {}).get("daily_count", 0)
                    
                    if current_usage >= daily_limit:
                        logger.warning(f"Paid key {key_id[:8]} reached safe limit ({daily_limit}) for model {model_name}. Stopping to prevent billing.")
                        self.current_index += 1
                        continue
                
                return config
            
            self.current_index += 1
        
        return None

    async def report_exhausted(self):
        """현재 키가 429 에러 등으로 소진되었음을 기록합니다."""
        config = await self.get_active_key_config()
        if config:
            key_id = config.get("key")
            if key_id not in self.usage_data["keys"]:
                self.usage_data["keys"][key_id] = {}
            self.usage_data["keys"][key_id]["exhausted"] = True
            self.usage_data["keys"][key_id]["exhausted_at"] = datetime.now().isoformat()
            self._save_usage_cache()
            logger.error(f"Key {key_id[:8]} reported as exhausted.")
            self.current_index += 1

    def increment_usage(self, key_id: str):
        """로컬 사용량 카운트를 증가시킵니다."""
        if key_id not in self.usage_data["keys"]:
            self.usage_data["keys"][key_id] = {}
        
        # 날짜가 바뀌었으면 카운트 초기화 로직 필요 (단순화함)
        today = datetime.now().strftime("%Y-%m-%d")
        last_date = self.usage_data["keys"][key_id].get("last_used_date")
        
        if last_date != today:
            self.usage_data["keys"][key_id]["daily_count"] = 1
            self.usage_data["keys"][key_id]["last_used_date"] = today
        else:
            self.usage_data["keys"][key_id]["daily_count"] = self.usage_data["keys"][key_id].get("daily_count", 0) + 1
        
        self._save_usage_cache()

    async def close(self):
        if self.mcp_client:
            await self.mcp_client.disconnect()
