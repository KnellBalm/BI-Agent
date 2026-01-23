from typing import Any, Dict, List, Optional
from .json_parser import BIJsonParser
from .visual_decoder import VisualDecoder

class BIToolAgent:
    """
    BI 솔루션 JSON 설정을 지능적으로 수정하는 Agent
    """
    def __init__(self, parser: BIJsonParser):
        self.parser = parser

    def add_field_to_datamodel(self, datamodel_name: str, field_info: Dict[str, Any]):
        """데이터 모델에 새로운 필드를 추가합니다."""
        dm = self.parser.find_datamodel_by_name(datamodel_name)
        if dm:
            if "fields" not in dm:
                dm["fields"] = []
            dm["fields"].append(field_info)
            return True
        return False

    def update_dataset_query(self, datamodel_name: str, new_query: str):
        """데이터 모델의 데이터셋 쿼리를 업데이트합니다."""
        dm = self.parser.find_datamodel_by_name(datamodel_name)
        if dm and "dataset" in dm:
            dm["dataset"]["query"] = new_query
            return True
        return False

    def update_visual_text(self, report_name: str, element_id: str, new_text: str) -> bool:
        """레포트 내 특정 시각화 요소의 텍스트를 수정합니다."""
        try:
            report = self.parser.find_report_by_name(report_name)
            if not report or "etc" not in report:
                return False

            etc_data = VisualDecoder.decode_etc(report["etc"])
            visuals = etc_data.get("visual", [])
            
            found = False
            for v in visuals:
                if v.get("elementId") == element_id:
                    v["text"] = {"ko": new_text}
                    found = True
                    break
            
            if found:
                report["etc"] = VisualDecoder.encode_etc(etc_data)
                return True
        except Exception as e:
            print(f"Error in update_visual_text: {e}")
        return False

    def update_interaction_logic(self, report_name: str, update_data: Dict[str, Any]) -> bool:
        """
        레포트의 인터랙션 로직(varList, eventList)을 수정합니다.
        update_data 예시: {"vars": [{"name": "target", "value": 100}], "events": [...]}
        """
        try:
            report = self.parser.find_report_by_name(report_name)
            if not report or "etc" not in report:
                return False

            etc_data = VisualDecoder.decode_etc(report["etc"])
            modified = False

            # 변수(Variables) 업데이트
            if "vars" in update_data:
                var_list = etc_data.get("varList", [])
                for new_var in update_data["vars"]:
                    v_name = new_var.get("name")
                    for v in var_list:
                        if v.get("name") == v_name:
                            v.update(new_var)
                            modified = True
                etc_data["varList"] = var_list

            # 이벤트(Events) 업데이트
            if "events" in update_data:
                event_list = etc_data.get("eventList", [])
                # 단순화된 예시: eventCode 매칭 시 업데이트
                for new_event in update_data["events"]:
                    e_code = new_event.get("eventCode")
                    for e in event_list:
                        if e.get("eventCode") == e_code:
                            e.update(new_event)
                            modified = True
                etc_data["eventList"] = event_list

            if modified:
                report["etc"] = VisualDecoder.encode_etc(etc_data)
                return True
        except Exception as e:
            print(f"Error in update_interaction_logic: {e}")
        return False

    def list_all_components(self) -> Dict[str, List[str]]:
        """모든 데이터 모델과 레포트 목록을 반환합니다."""
        return {
            "datamodels": self.parser.list_datamodels(),
            "reports": self.parser.list_reports()
        }
