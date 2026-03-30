"""
AWS QuickSight 연동 도구.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import boto3 as _boto3
    from botocore.exceptions import ClientError as _ClientError
    _HAS_BOTO3 = True
except ImportError:
    _HAS_BOTO3 = False

_quicksight_connections: dict = {}
# {conn_id: {"client": boto3_client, "account_id": "...", "region": "..."}}


def connect_quicksight(
    conn_id: str,
    account_id: str,
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    region_name: str = "us-east-1",
) -> str:
    """[QuickSight] AWS QuickSight 연결 등록.

    Args:
        conn_id: 연결 식별자 (예: "qs_prod")
        account_id: AWS 계정 ID (12자리 숫자)
        aws_access_key_id: AWS Access Key ID (None이면 환경변수/IAM Role 사용)
        aws_secret_access_key: AWS Secret Access Key (None이면 환경변수/IAM Role 사용)
        region_name: AWS 리전 (기본값: us-east-1)

    Returns:
        연결 성공/실패 메시지
    """
    if not _HAS_BOTO3:
        return "[ERROR] boto3 패키지가 필요합니다: pip install boto3"

    if not account_id:
        return "[ERROR] account_id가 필요합니다."

    try:
        kwargs = {"region_name": region_name}
        if aws_access_key_id:
            kwargs["aws_access_key_id"] = aws_access_key_id
        if aws_secret_access_key:
            kwargs["aws_secret_access_key"] = aws_secret_access_key

        client = _boto3.client("quicksight", **kwargs)
        # 연결 확인: 데이터셋 목록 조회
        client.list_data_sets(AwsAccountId=account_id)

        _quicksight_connections[conn_id] = {
            "client": client,
            "account_id": account_id,
            "region": region_name,
        }
        return f"[SUCCESS] QuickSight 연결 성공 (conn_id={conn_id}, account_id={account_id}, region={region_name})"
    except _ClientError as e:
        return f"[ERROR] AWS 오류: {e.response['Error']['Message']}"
    except Exception as e:
        return f"[ERROR] QuickSight 연결 실패: {e}"


def list_quicksight_datasets(conn_id: str) -> str:
    """[QuickSight] QuickSight 데이터셋 목록 조회.

    Args:
        conn_id: 연결 식별자

    Returns:
        데이터셋 목록 마크다운 테이블
    """
    if conn_id not in _quicksight_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    conn = _quicksight_connections[conn_id]
    client = conn["client"]
    account_id = conn["account_id"]

    try:
        response = client.list_data_sets(AwsAccountId=account_id)
        summaries = response.get("DataSetSummaries", [])

        if not summaries:
            return "등록된 데이터셋이 없습니다."

        lines = [
            f"## QuickSight 데이터셋 ({len(summaries)}개)",
            "",
            "| DataSetId | Name | ImportMode | CreatedTime |",
            "| --- | --- | --- | --- |",
        ]
        for ds in summaries:
            ds_id = ds.get("DataSetId", "")
            name = ds.get("Name", "")
            import_mode = ds.get("ImportMode", "")
            created = str(ds.get("CreatedTime", ""))
            lines.append(f"| {ds_id} | {name} | {import_mode} | {created} |")

        return "\n".join(lines)
    except _ClientError as e:
        return f"[ERROR] AWS 오류: {e.response['Error']['Message']}"
    except Exception as e:
        return f"[ERROR] 데이터셋 목록 조회 실패: {e}"


def list_quicksight_analyses(conn_id: str) -> str:
    """[QuickSight] QuickSight 분석 목록 조회.

    Args:
        conn_id: 연결 식별자

    Returns:
        분석 목록 마크다운 테이블
    """
    if conn_id not in _quicksight_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    conn = _quicksight_connections[conn_id]
    client = conn["client"]
    account_id = conn["account_id"]

    try:
        response = client.list_analyses(AwsAccountId=account_id)
        summaries = response.get("AnalysisSummaryList", [])

        if not summaries:
            return "등록된 분석이 없습니다."

        lines = [
            f"## QuickSight 분석 ({len(summaries)}개)",
            "",
            "| AnalysisId | Name | Status | CreatedTime |",
            "| --- | --- | --- | --- |",
        ]
        for an in summaries:
            an_id = an.get("AnalysisId", "")
            name = an.get("Name", "")
            status = an.get("Status", "")
            created = str(an.get("CreatedTime", ""))
            lines.append(f"| {an_id} | {name} | {status} | {created} |")

        return "\n".join(lines)
    except _ClientError as e:
        return f"[ERROR] AWS 오류: {e.response['Error']['Message']}"
    except Exception as e:
        return f"[ERROR] 분석 목록 조회 실패: {e}"


def list_quicksight_dashboards(conn_id: str) -> str:
    """[QuickSight] QuickSight 대시보드 목록 조회.

    Args:
        conn_id: 연결 식별자

    Returns:
        대시보드 목록 마크다운 테이블
    """
    if conn_id not in _quicksight_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    conn = _quicksight_connections[conn_id]
    client = conn["client"]
    account_id = conn["account_id"]

    try:
        response = client.list_dashboards(AwsAccountId=account_id)
        summaries = response.get("DashboardSummaryList", [])

        if not summaries:
            return "등록된 대시보드가 없습니다."

        lines = [
            f"## QuickSight 대시보드 ({len(summaries)}개)",
            "",
            "| DashboardId | Name | CreatedTime |",
            "| --- | --- | --- |",
        ]
        for db in summaries:
            db_id = db.get("DashboardId", "")
            name = db.get("Name", "")
            created = str(db.get("CreatedTime", ""))
            lines.append(f"| {db_id} | {name} | {created} |")

        return "\n".join(lines)
    except _ClientError as e:
        return f"[ERROR] AWS 오류: {e.response['Error']['Message']}"
    except Exception as e:
        return f"[ERROR] 대시보드 목록 조회 실패: {e}"


def get_quicksight_embed_url(
    conn_id: str,
    dashboard_id: str,
    session_lifetime_minutes: int = 60,
) -> str:
    """[QuickSight] QuickSight 대시보드 익명 임베드 URL 생성.

    Args:
        conn_id: 연결 식별자
        dashboard_id: 임베드할 대시보드 ID
        session_lifetime_minutes: 세션 유효 시간 (분, 기본 60)

    Returns:
        임베드 URL 문자열 또는 에러 메시지
    """
    if conn_id not in _quicksight_connections:
        return f"[ERROR] 연결 ID '{conn_id}'를 찾을 수 없습니다."

    conn = _quicksight_connections[conn_id]
    client = conn["client"]
    account_id = conn["account_id"]

    region = conn.get("region", "us-east-1")
    dashboard_arn = f"arn:aws:quicksight:{region}:{account_id}:dashboard/{dashboard_id}"

    try:
        response = client.generate_embed_url_for_anonymous_user(
            AwsAccountId=account_id,
            SessionLifetimeInMinutes=session_lifetime_minutes,
            Namespace="default",
            AuthorizedResourceArns=[dashboard_arn],
            ExperienceConfiguration={"Dashboard": {"InitialDashboardId": dashboard_id}},
        )
        embed_url = response.get("EmbedUrl", "")
        if not embed_url:
            return "[ERROR] 임베드 URL을 가져오지 못했습니다."
        return embed_url
    except _ClientError as e:
        return f"[ERROR] AWS 오류: {e.response['Error']['Message']}"
    except Exception as e:
        return f"[ERROR] 임베드 URL 생성 실패: {e}"
