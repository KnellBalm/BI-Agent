"""
bi-agent Google OAuth 2.0 PKCE 인증 흐름.

backend/orchestrator/managers/oauth_handler.py의 구현을 어댑터 패턴으로 래핑.
토큰 저장: credentials.json 파일 → OS 키체인 (credentials 모듈 사용).

흐름:
1. code_verifier / code_challenge(S256) 생성
2. 브라우저에서 Google 인증 URL 열기
3. localhost callback 서버에서 authorization code 수신 (포트: 8765 → 8766 → 8767)
4. authorization code → access_token + refresh_token 교환
5. refresh_token을 OS 키체인에 저장
6. get_credentials()로 저장된 토큰에서 Credentials 복원

보안 원칙:
- 토큰을 로그에 출력하지 않는다.
- 토큰을 디스크 평문 파일에 저장하지 않는다.
"""

import base64
import hashlib
import logging
import secrets
import socket
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
import google.oauth2.credentials

from bi_agent_mcp.auth.credentials import get_secret, store_secret
from bi_agent_mcp import config

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 상수
# ──────────────────────────────────────────────

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

_CALLBACK_PORTS = [8765, 8766, 8767]


# ──────────────────────────────────────────────
# PKCE 유틸
# ──────────────────────────────────────────────

def _generate_pkce_pair() -> tuple[str, str]:
    """PKCE code_verifier + code_challenge(S256) 쌍을 생성한다."""
    verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


# ──────────────────────────────────────────────
# 포트 선택
# ──────────────────────────────────────────────

def _find_available_port() -> tuple[int, str]:
    """사용 가능한 콜백 포트를 찾아 (port, redirect_uri)를 반환한다."""
    for port in _CALLBACK_PORTS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port, f"http://localhost:{port}/callback"
            except OSError:
                continue
    # 모두 사용 중이면 첫 번째 포트 강제 사용 (기존 프로세스가 종료됐을 수 있음)
    port = _CALLBACK_PORTS[0]
    return port, f"http://localhost:{port}/callback"


# ──────────────────────────────────────────────
# 로컬 콜백 서버
# ──────────────────────────────────────────────

class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    """브라우저 리다이렉트에서 authorization code를 수신하는 핸들러."""

    auth_code: Optional[str] = None
    error: Optional[str] = None

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" in params:
            _OAuthCallbackHandler.auth_code = params["code"][0]
            self._respond_html(
                "<h2>로그인 성공!</h2>"
                "<p>이 창을 닫고 터미널로 돌아가세요.</p>"
                "<script>setTimeout(()=>window.close(), 2000)</script>"
            )
        elif "error" in params:
            _OAuthCallbackHandler.error = params["error"][0]
            self._respond_html(
                f"<h2>로그인 실패</h2><p>{_OAuthCallbackHandler.error}</p>"
            )
        else:
            self._respond_html("<h2>대기 중...</h2>")

    def _respond_html(self, body: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html = (
            '<!DOCTYPE html><html><head><meta charset="utf-8">'
            "<style>body{font-family:sans-serif;display:flex;justify-content:center;"
            "align-items:center;height:100vh;background:#1a1a2e;color:#e0e0e0}</style>"
            f"</head><body>{body}</body></html>"
        )
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):  # noqa: A002
        logger.debug("OAuth callback: " + format % args)


def _run_callback_server(port: int, timeout: int = 120) -> Optional[str]:
    """
    지정한 포트에 로컬 HTTP 서버를 시작하고 authorization code를 기다린다.
    timeout 초 이내에 code가 오지 않으면 None 반환.
    """
    _OAuthCallbackHandler.auth_code = None
    _OAuthCallbackHandler.error = None

    server = HTTPServer(("127.0.0.1", port), _OAuthCallbackHandler)
    server.timeout = 1

    start = time.time()
    while time.time() - start < timeout:
        server.handle_request()
        if _OAuthCallbackHandler.auth_code or _OAuthCallbackHandler.error:
            break

    server.server_close()

    if _OAuthCallbackHandler.error:
        logger.error("OAuth error from Google: %s", _OAuthCallbackHandler.error)
        return None
    return _OAuthCallbackHandler.auth_code


# ──────────────────────────────────────────────
# 토큰 교환
# ──────────────────────────────────────────────

def _exchange_code_for_tokens(
    code: str,
    code_verifier: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> Optional[Dict[str, Any]]:
    """Authorization Code를 Access/Refresh Token으로 교환한다."""
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "code_verifier": code_verifier,
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(GOOGLE_TOKEN_URL, data=data)
            resp.raise_for_status()
            tokens = resp.json()
            logger.info("Token exchange succeeded")
            return {
                "access_token": tokens["access_token"],
                "refresh_token": tokens.get("refresh_token"),
                "expires_at": time.time() + tokens.get("expires_in", 3600),
                "token_type": tokens.get("token_type", "Bearer"),
            }
    except Exception as e:
        logger.error("Token exchange failed: %s", e)
        return None


# ──────────────────────────────────────────────
# 공개 인터페이스
# ──────────────────────────────────────────────

def run_oauth_flow(
    client_id: str,
    client_secret: str,
    scopes: List[str],
    service_name: str,
) -> google.oauth2.credentials.Credentials:
    """
    Google OAuth 2.0 PKCE 흐름 실행.

    oauth_handler.py의 google_oauth_login() 로직을 어댑터로 래핑.
    refresh_token은 credentials.store_secret(service_name, "refresh_token", value)로 저장.

    Args:
        client_id: GCP OAuth client ID
        client_secret: GCP OAuth client secret
        scopes: 요청할 OAuth 스코프 목록
        service_name: 키체인 서비스 이름 (예: "bi-agent-ga4")

    Returns:
        google.oauth2.credentials.Credentials

    Raises:
        RuntimeError: 인증 실패 시
    """
    # 1. PKCE 쌍 생성
    code_verifier, code_challenge = _generate_pkce_pair()

    # 2. 사용 가능한 포트 확보
    port, redirect_uri = _find_available_port()

    # 3. 인증 URL 생성
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    # 4. 브라우저 열기
    logger.info("브라우저에서 Google OAuth 로그인을 시작합니다 (포트: %d)", port)
    webbrowser.open(auth_url)

    # 5. 로컬 서버에서 콜백 대기 (최대 120초)
    code = _run_callback_server(port, timeout=120)
    if not code:
        raise RuntimeError("Authorization code를 받지 못했습니다 (timeout 또는 사용자 취소)")

    # 6. Code → Token 교환
    tokens = _exchange_code_for_tokens(code, code_verifier, client_id, client_secret, redirect_uri)
    if not tokens:
        raise RuntimeError("토큰 교환에 실패했습니다")

    # 7. refresh_token을 OS 키체인에 저장
    if tokens.get("refresh_token"):
        store_secret(service_name, "refresh_token", tokens["refresh_token"])
    if tokens.get("access_token"):
        store_secret(service_name, "access_token", tokens["access_token"])
    store_secret(service_name, "expires_at", str(tokens.get("expires_at", 0)))
    store_secret(service_name, "client_id", client_id)
    store_secret(service_name, "client_secret", client_secret)

    # 8. google.oauth2.credentials.Credentials 반환
    return google.oauth2.credentials.Credentials(
        token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token"),
        token_uri=GOOGLE_TOKEN_URL,
        client_id=client_id,
        client_secret=client_secret,
        scopes=scopes,
    )


def get_credentials(
    service_name: str,
    client_id: str,
    client_secret: str,
) -> Optional[google.oauth2.credentials.Credentials]:
    """
    저장된 refresh_token으로 Credentials를 복원한다.

    Args:
        service_name: 키체인 서비스 이름 (run_oauth_flow에 사용한 것과 동일)
        client_id: GCP OAuth client ID
        client_secret: GCP OAuth client secret

    Returns:
        google.oauth2.credentials.Credentials 또는 None (저장된 토큰 없음)
    """
    refresh_token = get_secret(service_name, "refresh_token")
    if not refresh_token:
        return None

    access_token = get_secret(service_name, "access_token")

    # client_id/secret은 인자 우선, 없으면 키체인 → config 순으로 폴백
    cid = client_id or get_secret(service_name, "client_id") or config.GOOGLE_CLIENT_ID
    csecret = client_secret or get_secret(service_name, "client_secret") or config.GOOGLE_CLIENT_SECRET

    return google.oauth2.credentials.Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri=GOOGLE_TOKEN_URL,
        client_id=cid,
        client_secret=csecret,
    )
