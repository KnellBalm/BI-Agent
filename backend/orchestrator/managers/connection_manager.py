import json
import os
from typing import Dict, Any, List, Optional

class ConnectionManager:
    """
    데이터 소스 연결 정보(DB, Excel 등)를 영구 저장하고 관리하는 클래스
    """
    def __init__(self, storage_path: str = "backend/data/connections.json"):
        self.storage_path = os.path.abspath(storage_path)
        self.connections = self._load_connections()

    def _load_connections(self) -> Dict[str, Any]:
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_connections(self):
        dir_path = os.path.dirname(self.storage_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(self.connections, f, indent=4, ensure_ascii=False)

    async def ping_connection(self, conn_id: str) -> Dict[str, Any]:
        """연결 상태를 확인합니다."""
        info = self.get_connection(conn_id)
        if not info:
            return {"success": False, "message": f"연결 '{conn_id}'를 찾을 수 없습니다."}
        
        type_ = info.get("type")
        server_path = info.get("server_path")
        
        # 1. 서버 파일 존재 여부 확인
        if server_path and not os.path.exists(server_path):
            return {"success": False, "message": f"MCP 서버 파일을 찾을 수 없습니다: {server_path}"}
            
        # 2. 파일 기반(Excel 등)인 경우 데이터 파일 존재 확인
        file_path = info.get("file_path")
        if type_ == "excel" and file_path and not os.path.exists(file_path):
            return {"success": False, "message": f"Excel 파일을 찾을 수 없습니다: {file_path}"}
            
        # 3. 실제 연결 시도 (Optional/Future: MCP connect 실행 후 disconnect)
        # 현재는 기본 설정 확인만 수행
        return {"success": True, "message": f"'{conn_id}' 연결 설정이 유효합니다."}

    def get_connection(self, conn_id: str) -> Optional[Dict[str, Any]]:
        """ID로 연결 정보를 조회합니다."""
        info = self.connections.get(conn_id)
        if info:
            # ID가 누락된 경우 주입 (Agent에서 식별용으로 사용)
            if "id" not in info:
                info["id"] = conn_id
        return info

    def list_connections(self) -> List[Dict[str, Any]]:
        """모든 연결 목록을 반환합니다."""
        result = []
        for cid, info in self.connections.items():
            item = info.copy()
            item["id"] = cid
            result.append(item)
        return result

    def delete_connection(self, conn_id: str):
        """연결 정보를 삭제합니다."""
        if conn_id in self.connections:
            del self.connections[conn_id]
            self._save_connections()
            return True
        return False

    def register_connection(self, conn_id: str, conn_type: str, config: Dict[str, Any]):
        """새로운 연결 정보를 등록하거나 업데이트합니다."""
        # Ensure config is a dict and handle potential list-style input (though unlikely here)
        if not isinstance(config, dict):
            config = {"path": str(config)}
            
        conn_info = {
            "type": conn_type,
            "config": config,
            "ssh": config.pop("ssh", None) if isinstance(config, dict) else None,
            "name": config.get("name", conn_id)
        }

        # 필드 검증 (최소한의 수준)
        if not conn_type:
            raise ValueError("Connection type is required")
        
        self.connections[conn_id] = conn_info
        self._save_connections()
        return True
