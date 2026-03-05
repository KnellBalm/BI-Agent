"""
OAuth Handler — Google OAuth 2.0 PKCE 플로우 (CLI 환경).

로컬에 일회성 HTTP 서버를 띄워 브라우저 콜백을 수신한다.
사용자는 브라우저에서 구글 로그인만 하면 되고, 나머지는 자동으로 처리된다.

흐름:
1. code_verifier / code_challenge 생성 (PKCE)
2. 브라우저에서 구글 인증 URL 열기
3. 로컬 서버(localhost:PORT)에서 callback 수신
4. authorization code → access_token + refresh_token 교환
5. credentials.json에 토큰 저장
"""
import asyncio
import base64
import hashlib
import json
import os
import secrets
import threading
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional
from urllib.parse import urlencode, urlparse, parse_qs

import httpx

from backend.utils.logger_setup import setup_logger

logger = setup_logger("oauth_handler", "oauth.log")

# ──────────────────────────────────────────────
# 상수
# ──────────────────────────────────────────────

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Google AI / Generative Language API 스코프
# .peruserquota를 붙이면 GCP 콘솔에서 '잘못된 범위' 에러 없이 더 잘 추가됩니다.
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/generative-language.peruserquota",
]

CALLBACK_PORT = 18921  # 고정 포트 (콜백용)
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback"

# GCP OAuth Client (BI-Agent 전용)
# 실제 운영 시에는 환경변수 또는 별도 설정 파일에서 로드
_DEFAULT_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
_DEFAULT_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")


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
                "<h2>✅ 로그인 성공!</h2>"
                "<p>이 창을 닫고 터미널로 돌아가세요.</p>"
                "<script>setTimeout(()=>window.close(), 2000)</script>"
            )
        elif "error" in params:
            _OAuthCallbackHandler.error = params["error"][0]
            self._respond_html(
                f"<h2>❌ 로그인 실패</h2><p>{_OAuthCallbackHandler.error}</p>"
            )
        else:
            self._respond_html("<h2>⏳ 대기 중...</h2>")

    def _respond_html(self, body: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
        <style>body{{font-family:sans-serif;display:flex;justify-content:center;
        align-items:center;height:100vh;background:#1a1a2e;color:#e0e0e0}}</style>
        </head><body>{body}</body></html>"""
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        """HTTP 서버 로그를 콘솔 대신 logger로 보냄."""
        logger.debug(f"OAuth callback server: {format % args}")


def _run_callback_server(timeout: int = 120) -> Optional[str]:
    """
    로컬 HTTP 서버를 시작하고 authorization code를 기다린다.
    timeout 초 이내에 code가 오지 않으면 None 반환.
    """
    _OAuthCallbackHandler.auth_code = None
    _OAuthCallbackHandler.error = None

    server = HTTPServer(("127.0.0.1", CALLBACK_PORT), _OAuthCallbackHandler)
    server.timeout = 1  # poll interval

    start = time.time()
    while time.time() - start < timeout:
        server.handle_request()
        if _OAuthCallbackHandler.auth_code or _OAuthCallbackHandler.error:
            break

    server.server_close()

    if _OAuthCallbackHandler.error:
        logger.error(f"OAuth error from Google: {_OAuthCallbackHandler.error}")
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
) -> Optional[Dict[str, Any]]:
    """Authorization Code를 Access/Refresh Token으로 교환한다."""
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
        "code_verifier": code_verifier,
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(GOOGLE_TOKEN_URL, data=data)
            resp.raise_for_status()
            tokens = resp.json()
            logger.info("Successfully exchanged code for tokens")
            return {
                "access_token": tokens["access_token"],
                "refresh_token": tokens.get("refresh_token"),
                "expires_at": time.time() + tokens.get("expires_in", 3600),
                "token_type": tokens.get("token_type", "Bearer"),
            }
    except Exception as e:
        logger.error(f"Token exchange failed: {e}")
        return None


def refresh_access_token(
    refresh_token: str,
    client_id: str = "",
    client_secret: str = "",
) -> Optional[Dict[str, Any]]:
    """Refresh Token으로 새 Access Token을 발급받는다."""
    client_id = client_id or _DEFAULT_CLIENT_ID
    client_secret = client_secret or _DEFAULT_CLIENT_SECRET

    if not client_id or not client_secret:
        logger.warning("OAuth client credentials not configured, cannot refresh")
        return None

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(GOOGLE_TOKEN_URL, data=data)
            resp.raise_for_status()
            tokens = resp.json()
            return {
                "access_token": tokens["access_token"],
                "refresh_token": refresh_token,  # 기존 유지
                "expires_at": time.time() + tokens.get("expires_in", 3600),
                "token_type": tokens.get("token_type", "Bearer"),
            }
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        return None


# ──────────────────────────────────────────────
# 메인 로그인 플로우
# ──────────────────────────────────────────────

def google_oauth_login(
    client_id: str = "",
    client_secret: str = "",
) -> Optional[Dict[str, Any]]:
    """
    Google OAuth 2.0 PKCE 로그인 전체 플로우.
    
    Returns:
        토큰 dict (access_token, refresh_token, expires_at) 또는 None
    """
    client_id = client_id or _DEFAULT_CLIENT_ID
    client_secret = client_secret or _DEFAULT_CLIENT_SECRET

    if not client_id:
        logger.error("GOOGLE_OAUTH_CLIENT_ID is not set")
        return None

    # 1. PKCE 쌍 생성
    code_verifier, code_challenge = _generate_pkce_pair()

    # 2. 인증 URL 생성
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",    # refresh_token 받기 위해
        "prompt": "consent",         # 항상 동의 화면 표시
    }
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    # 3. 브라우저 열기
    logger.info(f"Opening browser for Google OAuth login")
    webbrowser.open(auth_url)

    # 4. 로컬 서버에서 콜백 대기 (최대 120초)
    code = _run_callback_server(timeout=120)
    if not code:
        return None

    # 5. Code → Token 교환
    tokens = _exchange_code_for_tokens(code, code_verifier, client_id, client_secret)
    return tokens


def is_token_expired(token_data: Dict[str, Any]) -> bool:
    """토큰이 만료되었는지 확인한다. 5분 여유를 둔다."""
    expires_at = token_data.get("expires_at", 0)
    return time.time() > (expires_at - 300)
