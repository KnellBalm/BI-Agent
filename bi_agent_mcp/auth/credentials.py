"""
bi-agent 자격증명 관리.

우선순위:
1. 환경변수
2. OS 키체인 (macOS Keychain / Linux libsecret / Windows Credential Manager)
3. 메모리 폴백 (keyring 미설치 시 경고)

보안 원칙:
- 비밀값을 로그에 절대 출력하지 않는다.
- 디스크에 평문으로 저장하지 않는다.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# 메모리 폴백 저장소 (keyring 미설치 환경용)
_memory_store: dict[str, str] = {}

_KEYRING_AVAILABLE = False
try:
    import keyring
    _KEYRING_AVAILABLE = True
except ImportError:
    logger.warning("keyring 패키지 미설치 — 자격증명이 메모리에만 저장됩니다. 재시작 시 사라집니다.")


def store_secret(service: str, key: str, value: str) -> None:
    """
    비밀값을 OS 키체인에 저장한다.
    keyring 미설치 시 메모리에 저장하고 경고를 출력한다.

    Args:
        service: 서비스 이름 (예: "bi-agent")
        key: 키 이름 (예: "ga4_123456789_refresh_token")
        value: 저장할 비밀값
    """
    if _KEYRING_AVAILABLE:
        keyring.set_password(service, key, value)
        logger.debug("키체인에 저장: %s / %s", service, key)
    else:
        _memory_store[f"{service}:{key}"] = value
        logger.warning("메모리에만 저장됨 (keyring 없음): %s / %s", service, key)


def get_secret(service: str, key: str) -> Optional[str]:
    """
    OS 키체인에서 비밀값을 조회한다.

    Args:
        service: 서비스 이름
        key: 키 이름

    Returns:
        저장된 값, 없으면 None
    """
    if _KEYRING_AVAILABLE:
        return keyring.get_password(service, key)
    return _memory_store.get(f"{service}:{key}")


def delete_secret(service: str, key: str) -> None:
    """OS 키체인에서 비밀값을 삭제한다."""
    if _KEYRING_AVAILABLE:
        try:
            keyring.delete_password(service, key)
        except keyring.errors.PasswordDeleteError:
            pass
    else:
        _memory_store.pop(f"{service}:{key}", None)


def get_env_or_secret(env_var: str, service: str, key: str) -> Optional[str]:
    """
    환경변수 우선 → 키체인 폴백으로 비밀값을 조회한다.

    Args:
        env_var: 환경변수 이름 (예: "BI_AGENT_PG_PASSWORD")
        service: 키체인 서비스 이름
        key: 키체인 키 이름

    Returns:
        환경변수 값 또는 키체인 값, 없으면 None
    """
    env_value = os.environ.get(env_var)
    if env_value:
        return env_value
    return get_secret(service, key)


def mask_password(value: str) -> str:
    """
    비밀번호를 마스킹한다. list_connections 출력 등 사용자 표시용.

    Args:
        value: 원본 비밀값

    Returns:
        "****" (길이에 무관하게 고정)
    """
    return "****"
