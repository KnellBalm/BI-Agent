"""
Google Analytics 4 Data API 연결 및 리포트 조회 도구.
"""
import logging
from typing import Dict, List, Optional

from bi_agent_mcp.auth.oauth import get_credentials, run_oauth_flow
from bi_agent_mcp import config

logger = logging.getLogger(__name__)

# 메모리 상에 GA4 클라이언트 보관 (property_id -> dict)
_ga4_connections: Dict[str, dict] = {}


def connect_ga4(property_id: str) -> str:
    """[GA4] GA4 속성에 연결 시도. (OAuth 2.0 PKCE 인증 활용)
    미인증 상태면 브라우저를 열어 Google 로그인 수행.
    
    Args:
        property_id: GA4 Property ID (예: '123456789')
        
    Returns:
        성공 메시지 및 연결 ID
    """
    service_name = "bi-agent-ga4"
    scopes = ["https://www.googleapis.com/auth/analytics.readonly"]
    client_id = config.GOOGLE_CLIENT_ID
    client_secret = config.GOOGLE_CLIENT_SECRET

    if not client_id or not client_secret:
        return "[ERROR] GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET 환경변수가 필요합니다."

    try:
        # 먼저 키체인에 저장된 자격 증명을 불러옴
        creds = get_credentials(service_name, client_id, client_secret)
        
        # 유효하지 않거나 없으면 OAuth Flow 진행
        if not creds or not creds.valid:
            logger.info("새로운 GA4 OAuth 인증을 시작합니다.")
            creds = run_oauth_flow(client_id, client_secret, scopes, service_name)
            
        # GA4 데이터 클라이언트 생성 (지연 import)
        try:
            from google.analytics.data.v1beta import BetaAnalyticsDataClient
        except ImportError:
            return "[ERROR] google-analytics-data 패키지가 설치되지 않았습니다. pip install google-analytics-data"
        client = BetaAnalyticsDataClient(credentials=creds)
        _ga4_connections[property_id] = {
            "client": client,
            "connected": True
        }
        
        return f"[SUCCESS] GA4 Property ({property_id}) 연결 성공"
        
    except Exception as e:
        logger.error(f"GA4 연결 실패: {e}")
        return f"[ERROR] GA4 연결 실패: {e}"


def get_ga4_report(
    property_id: str,
    metrics: List[str],
    dimensions: List[str],
    start_date: str = "30daysAgo",
    end_date: str = "today"
) -> str:
    """
    [GA4] GA4 리포트 조회 및 마크다운 테이블 반환.

    Args:
        property_id: 연결된 GA4 Property ID
        metrics: 조회할 측정항목 리스트 (예: ["sessions", "totalUsers"])
        dimensions: 조회할 측정기준 리스트 (예: ["date", "deviceCategory"])
        start_date: 시작일 (YYYY-MM-DD 또는 '30daysAgo', 기본값: '30daysAgo')
        end_date: 종료일 (YYYY-MM-DD 또는 'today', 기본값: 'today')

    Returns:
        마크다운 형식의 테이블 문자열
    """
    if property_id not in _ga4_connections:
        return f"[ERROR] 먼저 connect_ga4({property_id}) 를 호출하여 연결하세요."
        
    client = _ga4_connections[property_id]["client"]

    try:
        from google.analytics.data.v1beta.types import DateRange, Dimension, Metric, RunReportRequest
        from google.api_core.exceptions import InvalidArgument, PermissionDenied, ResourceExhausted
    except ImportError:
        return "[ERROR] google-analytics-data 패키지가 설치되지 않았습니다."

    req_metrics = [Metric(name=m) for m in metrics]
    req_dimensions = [Dimension(name=d) for d in dimensions]
    req_date_ranges = [DateRange(start_date=start_date, end_date=end_date)]
    
    try:
        request = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=req_dimensions,
            metrics=req_metrics,
            date_ranges=req_date_ranges,
            limit=config.QUERY_LIMIT  # 한 번에 너무 많은 데이터를 가져오지 않도록 리밋 적용
        )
        response = client.run_report(request)
        
        # 마크다운 포맷 생성
        headers = dimensions + metrics
        md_table = [
            f"| {' | '.join(headers)} |",
            f"| {' | '.join(['---'] * len(headers))} |"
        ]
        
        if not response.rows:
            return "해당 기간에 데이터가 없습니다."
            
        for row in response.rows:
            dim_vals = [dm.value for dm in row.dimension_values]
            met_vals = [mt.value for mt in row.metric_values]
            line = dim_vals + met_vals
            md_table.append(f"| {' | '.join(line)} |")
            
        result = "\n".join(md_table)
        return result
        
    except InvalidArgument as e:
        logger.error(f"GA4 잘못된 요청 (metric/dimension 이름 확인): {e}")
        return f"[ERROR] 잘못된 요청 파라미터: {e}"
    except PermissionDenied as e:
        logger.error(f"GA4 권한 없음 (property_id 접근 권한 확인): {e}")
        return f"[ERROR] GA4 접근 권한이 없습니다: {e}"
    except ResourceExhausted as e:
        logger.error(f"GA4 API 할당량 초과: {e}")
        return f"[ERROR] GA4 API 할당량이 초과되었습니다: {e}"
    except Exception as e:
        logger.error(f"GA4 API 호출 실패: {e}")
        return f"[ERROR] 리포트 생성 실패: {e}"
