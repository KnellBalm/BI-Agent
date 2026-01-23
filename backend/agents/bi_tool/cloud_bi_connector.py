from typing import Dict, Any, List
import urllib.parse
import json

class CloudBIConnector:
    """
    Looker Studio 및 AWS Quicksight 연동을 지원하는 커넥터.
    클라우드 환경의 특성을 고려하여 Link API와 SDK 기반 분석 가이드를 제공합니다.
    """
    def __init__(self):
        # 기본 템플릿 정보 (PoC용)
        self.templates = {
            "sales_dashboard": "0b123456-7890-abcd-efgh-i1234567890j",
            "marketing_report": "1c234567-8901-bcde-fghi-j2345678901k"
        }

    # --- Looker Studio (Link API) ---
    def generate_looker_studio_url(self, template_key: str, report_name: str, ds_configs: List[Dict[str, str]]) -> str:
        """
        Looker Studio Link API를 사용하여 파라미터가 적용된 리포트 복제 URL을 생성합니다.
        ds_configs: [{"alias": "main_ds", "id": "bq_dataset_id"}] 형식
        """
        template_id = self.templates.get(template_key, template_key)
        base_url = "https://lookerstudio.google.com/reporting/create"
        
        params = {
            "c.reportId": template_id,
            "r.reportName": report_name
        }
        
        # 데이터 소스 바인딩 (별칭 기반)
        for i, ds in enumerate(ds_configs):
            alias = ds.get("alias", f"ds{i}")
            ds_id = ds.get("id")
            if ds_id:
                params[f"ds.{alias}.connector"] = "bigQuery"
                params[f"ds.{alias}.datasetId"] = ds_id

        full_url = f"{base_url}?{urllib.parse.urlencode(params)}"
        return full_url

    # --- AWS Quicksight (SDK-based Analysis & Blueprint) ---
    def analyze_quicksight_definition(self, definition: Dict[str, Any]) -> Dict[str, Any]:
        """
        Quicksight 분석 정의를 파싱하여 요약 및 수정 포인트를 도출합니다.
        """
        summary = {
            "sheet_count": len(definition.get("Sheets", [])),
            "visual_details": [],
            "potential_issues": []
        }
        
        for sheet in definition.get("Sheets", []):
            visuals = sheet.get("Visuals", [])
            summary["visual_details"].append({
                "sheet_name": sheet.get("Name"),
                "visual_count": len(visuals)
            })
            
            # 접근성이나 네이밍 규칙 체크 (예시)
            if not sheet.get("Name").strip():
                summary["potential_issues"].append(f"시트 ID '{sheet.get('SheetId')}'의 이름이 비어 있습니다.")

        return summary

    def generate_quicksight_blueprint(self, base_definition: Dict[str, Any], change_request: str) -> str:
        """
        변경 요청에 따른 Quicksight Analysis Definition Blueprint(JSON)를 생성합니다.
        """
        # 실제로는 LLM이 이 base_definition을 참고하여 JSON 수정을 제안함 (PoC에서는 구조만 반환)
        blueprint = {
            "Action": "UpdateAnalysis",
            "AnalysisId": base_definition.get("AnalysisId", "new-analysis-id"),
            "Definition": base_definition # 원본을 기반으로 수정된 정의
        }
        
        return json.dumps(blueprint, indent=2, ensure_ascii=False)

    def get_sdk_guide(self, tool: str, action: str) -> str:
        """
        개발자/관리자를 위한 SDK/CLI 명령어 가이드를 제공합니다.
        """
        if tool.lower() == "quicksight":
            return f"aws quicksight update-analysis --aws-account-id YOUR_ACCOUNT_ID --analysis-id {action} --definition file://blueprint.json"
        return "해당 도구의 SDK 가이드는 준비 중입니다."
