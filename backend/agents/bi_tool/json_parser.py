import json
import os
from typing import Any, Dict, List, Optional

class BIJsonParser:
    """
    BI 솔루션 JSON 파일을 로드하고 특정 요소를 검색/수정하는 클래스
    """
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.data: Dict[str, Any] = {}
        if os.path.exists(file_path):
            self.load()

    def load(self):
        """JSON 파일을 로드합니다."""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)

    def save(self, output_path: str = None):
        """현재 데이터를 JSON 파일로 저장합니다."""
        path = output_path or self.file_path
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def find_datamodel_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """이름으로 데이터 모델을 찾습니다."""
        for dm in self.data.get("datamodel", []):
            if dm.get("name") == name:
                return dm
        return None

    def find_report_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """이름으로 레포트를 찾습니다."""
        for report in self.data.get("report", []):
            if report.get("name") == name:
                return report
        return None

    def list_datamodels(self) -> List[str]:
        """데이터 모델 이름 목록을 반환합니다."""
        return [dm.get("name") for dm in self.data.get("datamodel", [])]

    def list_reports(self) -> List[str]:
        """레포트 이름 목록을 반환합니다."""
        return [r.get("name") for r in self.data.get("report", [])]
