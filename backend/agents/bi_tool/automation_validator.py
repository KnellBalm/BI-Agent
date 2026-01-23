import logging
from typing import Dict, Any, List, Set

class AutomationValidator:
    """
    BI 솔루션 JSON 설정의 무결성을 검증하는 클래스
    """
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.errors = []
        self.warnings = []

    def validate_all(self) -> bool:
        """모든 검증 항목을 실행합니다."""
        self.errors = []
        self.warnings = []
        
        self._check_connector_references()
        self._check_datamodel_visual_mapping()
        self._check_duplicate_ids()
        
        return len(self.errors) == 0

    def _check_connector_references(self):
        """데이터 모델이 유효한 커넥터를 참조하는지 확인합니다."""
        connector_ids = {c.get("id") for c in self.data.get("connector", [])}
        for dm in self.data.get("datamodel", []):
            c_id = dm.get("connector_id")
            if c_id and c_id not in connector_ids:
                self.errors.append(f"DataModel '{dm.get('name')}' references missing connector ID: {c_id}")

    def _check_datamodel_visual_mapping(self):
        """시각화 요소가 실제 존재하는 데이터 모델을 참조하는지 확인합니다."""
        dm_ids = {dm.get("id") for dm in self.data.get("datamodel", [])}
        for vis in self.data.get("visual", []):
            dm_id = vis.get("datamodelId")
            if dm_id and dm_id not in dm_ids:
                self.errors.append(f"Visual '{vis.get('name')}' references missing datamodel ID: {dm_id}")

    def _check_duplicate_ids(self):
        """중복된 ID가 있는지 확인합니다."""
        all_ids = []
        for section in ["connector", "datamodel", "visual", "report"]:
            ids = [item.get("id") for item in self.data.get(section, []) if item.get("id")]
            all_ids.extend(ids)
        
        seen = set()
        dupes = set()
        for x in all_ids:
            if x in seen:
                dupes.add(x)
            seen.add(x)
        
        if dupes:
            self.warnings.append(f"Duplicate IDs found in solution: {list(dupes)}")

    def get_report(self) -> Dict[str, List[str]]:
        """검증 결과 레포트를 반환합니다."""
        return {
            "is_valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings
        }
