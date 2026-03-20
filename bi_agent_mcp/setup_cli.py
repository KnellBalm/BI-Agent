"""bi-agent-mcp 대화형 설치 마법사.

사용법:
  bi-agent-mcp-setup           전체 설치 마법사 (권장)
  bi-agent-mcp-setup --quick   빠른 설치 (최소 정보)
  bi-agent-mcp-setup --add db          DB만 추가
  bi-agent-mcp-setup --add ga4         GA4만 추가
  bi-agent-mcp-setup --add amplitude   Amplitude만 추가
"""

import argparse
import getpass
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

CLIENTS = {
    "Claude Code CLI": {
        "config_path": "~/.claude/settings.json",
        "detect": lambda: Path("~/.claude").expanduser().exists(),
        "format": "claude_code",
    },
    "Claude Desktop": {
        "config_path": "~/Library/Application Support/Claude/claude_desktop_config.json",
        "detect": lambda: Path("~/Library/Application Support/Claude").expanduser().exists(),
        "format": "standard",
    },
    "Antigravity": {
        "config_path": "~/.gemini/antigravity/mcp_config.json",
        "detect": lambda: Path("~/.gemini/antigravity").expanduser().exists(),
        "format": "standard",
    },
    "Cursor": {
        "config_path": "~/.cursor/mcp.json",
        "detect": lambda: Path("~/.cursor").expanduser().exists(),
        "format": "standard",
    },
    "직접 경로 입력": {
        "config_path": None,
        "detect": lambda: True,
        "format": "standard",
    },
}

DB_TYPES = ["PostgreSQL", "MySQL", "BigQuery", "건너뜀"]


def _prompt(msg: str, default: str = "") -> str:
    """입력 프롬프트. 빈 입력 시 default 반환."""
    if default:
        val = input(f"{msg} [{default}]: ").strip()
        return val if val else default
    return input(f"{msg}: ").strip()


def _confirm(msg: str, default: bool = False) -> bool:
    """예/아니오 확인 프롬프트."""
    hint = "[Y/n]" if default else "[y/N]"
    raw = input(f"{msg} {hint}: ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes", "예", "ㅇ")


def _select_clients() -> list[dict]:
    """클라이언트 선택 단계."""
    client_names = list(CLIENTS.keys())
    detected = [name for name in client_names if CLIENTS[name]["detect"]()]

    print("\n📋 MCP 클라이언트 선택")
    print("  (감지된 클라이언트에 ✓ 표시)\n")

    for i, name in enumerate(client_names, 1):
        mark = "✓" if name in detected else " "
        print(f"  {i}) [{mark}] {name}")

    print()
    raw = _prompt("설정할 클라이언트 번호 입력 (복수 선택: '1 3', 전체: 'all')").strip()

    raw = raw.strip("'\"")
    if raw.lower() == "all":
        selected_names = client_names
    else:
        indices = []
        for tok in raw.replace(",", " ").split():
            tok = tok.strip("'\"")
            try:
                idx = int(tok) - 1
                if 0 <= idx < len(client_names):
                    indices.append(idx)
            except ValueError:
                pass
        selected_names = [client_names[i] for i in indices]

    if not selected_names:
        print("  선택된 클라이언트가 없습니다. 종료합니다.")
        sys.exit(0)

    result = []
    for name in selected_names:
        info = dict(CLIENTS[name])
        if name == "직접 경로 입력":
            path_str = _prompt("설정 파일 경로 입력 (예: ~/.config/myapp/mcp.json)")
            info["config_path"] = path_str
        info["name"] = name
        result.append(info)

    return result


def _collect_db_info() -> tuple[dict, dict] | None:
    """DB 연결 정보 수집. (env_params, secrets) 튜플 반환. 건너뜀 시 None."""
    print("\n🗄️  데이터베이스 타입 선택\n")
    for i, db in enumerate(DB_TYPES, 1):
        print(f"  {i}) {db}")
    print()

    while True:
        raw = _prompt("DB 타입 번호 입력").strip()
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(DB_TYPES):
                db_type = DB_TYPES[idx]
                break
        except ValueError:
            pass
        print("  올바른 번호를 입력하세요.")

    if db_type == "건너뜀":
        return None

    print(f"\n🔌 {db_type} 연결 정보 입력\n")

    if db_type == "PostgreSQL":
        host = _prompt("Host", "localhost")
        port = _prompt("Port", "5432")
        dbname = _prompt("Database name")
        user = _prompt("User")
        password = getpass.getpass("Password: ")
        env_params = {
            "BI_AGENT_PG_HOST": host,
            "BI_AGENT_PG_PORT": port,
            "BI_AGENT_PG_DBNAME": dbname,
            "BI_AGENT_PG_USER": user,
        }
        secrets = {"password": password} if password else {}
        return env_params, secrets

    if db_type == "MySQL":
        host = _prompt("Host", "localhost")
        port = _prompt("Port", "3306")
        dbname = _prompt("Database name")
        user = _prompt("User")
        password = getpass.getpass("Password: ")
        env_params = {
            "BI_AGENT_MYSQL_HOST": host,
            "BI_AGENT_MYSQL_PORT": port,
            "BI_AGENT_MYSQL_DBNAME": dbname,
            "BI_AGENT_MYSQL_USER": user,
        }
        secrets = {"password": password} if password else {}
        return env_params, secrets

    # BigQuery
    project_id = _prompt("GCP Project ID")
    dataset = _prompt("Dataset")
    credentials_path = _prompt("Service account JSON 경로 (선택, 엔터로 건너뜀)").strip()
    env_params: dict = {
        "BI_AGENT_BQ_PROJECT_ID": project_id,
        "BI_AGENT_BQ_DATASET": dataset,
    }
    if credentials_path:
        env_params["BI_AGENT_BQ_CREDENTIALS_PATH"] = credentials_path
    return env_params, {}


def _collect_ga4_info() -> tuple[dict, dict] | None:
    """GA4 설정 수집. (env_params, secrets) 반환. 건너뜀 시 None."""
    print("\n📊 Google Analytics 4 (선택 사항)")
    if not _confirm("GA4를 설정하시겠습니까?"):
        return None

    print()
    client_id = _prompt("Google Client ID")
    client_secret = getpass.getpass("Google Client Secret: ")
    property_id = _prompt("GA4 Property ID (선택, 엔터로 건너뜀)").strip()

    env_params: dict = {}
    if client_id:
        env_params["BI_AGENT_GOOGLE_CLIENT_ID"] = client_id
    if property_id:
        env_params["BI_AGENT_GA4_PROPERTY_ID"] = property_id

    secrets = {"client_secret": client_secret} if client_secret else {}
    return env_params, secrets


def _collect_amplitude_info() -> tuple[dict, dict] | None:
    """Amplitude 설정 수집. (env_params, secrets) 반환. 건너뜀 시 None."""
    print("\n📈 Amplitude (선택 사항)")
    if not _confirm("Amplitude를 설정하시겠습니까?"):
        return None

    print()
    api_key = _prompt("Amplitude API Key")
    secret_key = getpass.getpass("Amplitude Secret Key: ")

    env_params: dict = {}
    secrets = {}
    if api_key:
        secrets["api_key"] = api_key
    if secret_key:
        secrets["secret_key"] = secret_key
    return env_params, secrets


def _save_secrets(source_type: str, secrets: dict) -> list[str]:
    """시크릿을 OS keyring에 저장하고 저장된 키 목록 반환."""
    if not secrets:
        return []
    try:
        from bi_agent_mcp.auth.credentials import store_secret
        saved = []
        for k, v in secrets.items():
            if v:
                store_secret("bi-agent", f"{source_type}_{k}", v)
                saved.append(k)
        return saved
    except Exception as e:
        print(f"  ⚠️  keyring 저장 실패: {e}")
        print("  환경변수로 직접 설정해주세요.")
        return []


def _build_mcp_entry(env_params: dict) -> dict:
    """MCP 서버 엔트리 생성 (비밀 값 제외)."""
    return {
        "command": sys.executable,
        "args": ["-m", "bi_agent_mcp"],
        "env": {k: v for k, v in env_params.items() if v},
    }


def _write_config(client: dict, mcp_entry: dict) -> None:
    """클라이언트 설정 파일에 bi-agent 엔트리 기록."""
    name = client["name"]
    raw_path = client["config_path"]
    if not raw_path:
        print(f"  ⚠️  {name}: 설정 파일 경로가 없습니다. 건너뜁니다.")
        return

    config_path = Path(raw_path).expanduser()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    existing: dict = {}
    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = {}

    # claude_code 포맷과 standard 포맷 모두 mcpServers 구조를 사용
    # 단, claude_code는 기존 파일 구조(permissions 등)를 손상시키지 않도록 주의
    fmt = client.get("format", "standard")
    if fmt == "claude_code":
        # Claude Code settings.json: mcpServers 키만 업데이트
        if not isinstance(existing.get("mcpServers"), dict):
            existing["mcpServers"] = {}
        existing["mcpServers"]["bi-agent"] = mcp_entry
    else:
        if "mcpServers" not in existing:
            existing["mcpServers"] = {}
        existing["mcpServers"]["bi-agent"] = mcp_entry

    try:
        with config_path.open("w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"  ✅ {name}: {config_path}")
    except OSError as e:
        print(f"  ❌ {name}: 파일 쓰기 실패 - {e}")


def _parse_db_url(url: str) -> tuple[str, dict, dict] | None:
    """DB 연결 URL을 파싱해서 (db_type, env_params, secrets) 반환."""
    try:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()

        if scheme in ("postgresql", "postgres"):
            db_type = "postgresql"
            env_params = {
                "BI_AGENT_PG_HOST": parsed.hostname or "localhost",
                "BI_AGENT_PG_PORT": str(parsed.port or 5432),
                "BI_AGENT_PG_DBNAME": parsed.path.lstrip("/"),
                "BI_AGENT_PG_USER": parsed.username or "",
            }
            secrets = {"password": parsed.password or ""}
        elif scheme == "mysql":
            db_type = "mysql"
            env_params = {
                "BI_AGENT_MYSQL_HOST": parsed.hostname or "localhost",
                "BI_AGENT_MYSQL_PORT": str(parsed.port or 3306),
                "BI_AGENT_MYSQL_DBNAME": parsed.path.lstrip("/"),
                "BI_AGENT_MYSQL_USER": parsed.username or "",
            }
            secrets = {"password": parsed.password or ""}
        else:
            return None

        return db_type, env_params, secrets
    except Exception:
        return None


def _run_quick_setup() -> None:
    """빠른 설치 — 최소 정보만 요구."""
    print("🚀 bi-agent-mcp 빠른 설정")
    print("=" * 40)
    print()

    # DB 입력 방식 선택
    print("DB 연결 방식:")
    print("  1) URL 형식 (postgresql://user:pass@host/dbname)")
    print("  2) 개별 필드 입력")
    print()

    method = _prompt("방식 선택", "1")
    all_env_params: dict = {}
    saved_secrets: list[str] = []

    if method == "1":
        url = _prompt("연결 URL")
        result = _parse_db_url(url)
        if result:
            db_type, env_params, secrets = result
            all_env_params.update(env_params)
            saved = _save_secrets("db", secrets)
            if saved:
                print(f"  ✅ 패스워드가 OS keyring에 안전하게 저장되었습니다.")
                saved_secrets.extend([f"db.{k}" for k in saved])
        else:
            print("  ⚠️  URL 파싱 실패. 개별 필드로 입력합니다.")
            method = "2"

    if method != "1":
        result2 = _collect_db_info()
        if result2:
            env_params, secrets = result2
            all_env_params.update(env_params)
            saved = _save_secrets("db", secrets)
            if saved:
                print(f"  ✅ 패스워드가 OS keyring에 안전하게 저장되었습니다.")
                saved_secrets.extend([f"db.{k}" for k in saved])

    # 자동 감지된 클라이언트에 등록
    detected = [name for name, info in CLIENTS.items() if info["detect"]() and name != "직접 경로 입력"]
    if not detected:
        detected_clients = list(CLIENTS.values())[:1]
        print("\n  감지된 클라이언트가 없습니다. Claude Code CLI에 설정합니다.")
    else:
        print(f"\n  감지된 클라이언트: {', '.join(detected)}")
        if not _confirm("위 클라이언트에 설정하시겠습니까?", default=True):
            print("  건너뜁니다.")
            detected = []

    if all_env_params and detected:
        mcp_entry = _build_mcp_entry(all_env_params)
        print("\n📝 설정 파일 작성 중...\n")
        for name in detected:
            info = dict(CLIENTS[name])
            info["name"] = name
            _write_config(info, mcp_entry)

    print("\n✅ 빠른 설정 완료!")
    if saved_secrets:
        print(f"  🔐 보안: 시크릿이 OS keyring에 저장됨 ({', '.join(saved_secrets)})")
    print()
    print("  GA4 추가:       bi-agent-mcp-setup --add ga4")
    print("  Amplitude 추가: bi-agent-mcp-setup --add amplitude")


def _run_add_source(source_type: str) -> None:
    """개별 데이터 소스 추가."""
    source_type = source_type.lower()

    if source_type == "db":
        result = _collect_db_info()
        if not result:
            return
        env_params, secrets = result
        saved = _save_secrets("db", secrets)
        _update_client_configs(env_params)
        if saved:
            print(f"  🔐 보안: 시크릿이 OS keyring에 저장됨")

    elif source_type == "ga4":
        result = _collect_ga4_info()
        if not result:
            return
        env_params, secrets = result
        saved = _save_secrets("ga4", secrets)
        _update_client_configs(env_params)
        if saved:
            print(f"  🔐 보안: 시크릿이 OS keyring에 저장됨")

    elif source_type == "amplitude":
        result = _collect_amplitude_info()
        if not result:
            return
        env_params, secrets = result
        saved = _save_secrets("amplitude", secrets)
        _update_client_configs(env_params)
        if saved:
            print(f"  🔐 보안: 시크릿이 OS keyring에 저장됨")

    else:
        print(f"  ❌ 알 수 없는 소스 타입: {source_type}")
        print("  가능한 값: db, ga4, amplitude")
        sys.exit(1)

    print(f"\n✅ {source_type} 설정 완료!")


def _update_client_configs(env_params: dict) -> None:
    """기존 클라이언트 설정 파일의 bi-agent env 블록을 업데이트."""
    for name, info in CLIENTS.items():
        if name == "직접 경로 입력":
            continue
        if not info["detect"]():
            continue
        config_path = Path(info["config_path"]).expanduser()
        if not config_path.exists():
            continue

        try:
            with config_path.open("r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        bi_agent = existing.get("mcpServers", {}).get("bi-agent")
        if not bi_agent:
            continue

        # env 블록 업데이트 (기존 값 보존, 새 값 추가/덮어쓰기)
        if "env" not in bi_agent:
            bi_agent["env"] = {}
        bi_agent["env"].update({k: v for k, v in env_params.items() if v})

        try:
            with config_path.open("w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
                f.write("\n")
            print(f"  ✅ {name} 업데이트: {config_path}")
        except OSError as e:
            print(f"  ❌ {name}: 파일 쓰기 실패 - {e}")


def _run_full_setup() -> None:
    """전체 설치 마법사."""
    print("🚀 bi-agent-mcp 설정 마법사")
    print("=" * 40)

    # 1. 클라이언트 선택
    selected_clients = _select_clients()

    # 2. DB 설정
    print("\n🗄️  2단계: 데이터베이스 설정")
    db_result = _collect_db_info()

    # 3. GA4 설정
    ga4_result = _collect_ga4_info()

    # 4. Amplitude 설정
    amplitude_result = _collect_amplitude_info()

    # 모든 env_params 취합 (비밀 제외)
    all_env_params: dict = {}
    all_saved_secrets: list[str] = []

    if db_result:
        env_params, secrets = db_result
        all_env_params.update(env_params)
        saved = _save_secrets("db", secrets)
        if saved:
            all_saved_secrets.extend([f"DB {k}" for k in saved])
            print(f"  ✅ DB 패스워드가 OS keyring에 안전하게 저장되었습니다.")

    if ga4_result:
        env_params, secrets = ga4_result
        all_env_params.update(env_params)
        saved = _save_secrets("ga4", secrets)
        if saved:
            all_saved_secrets.extend([f"GA4 {k}" for k in saved])
            print(f"  ✅ GA4 시크릿이 OS keyring에 안전하게 저장되었습니다.")

    if amplitude_result:
        env_params, secrets = amplitude_result
        all_env_params.update(env_params)
        saved = _save_secrets("amplitude", secrets)
        if saved:
            all_saved_secrets.extend([f"Amplitude {k}" for k in saved])
            print(f"  ✅ Amplitude 키가 OS keyring에 안전하게 저장되었습니다.")

    # MCP 엔트리 생성 (비밀 값 제외)
    mcp_entry = _build_mcp_entry(all_env_params)

    # 클라이언트 설정 파일 작성
    print("\n📝 설정 파일 작성 중...\n")
    for client in selected_clients:
        _write_config(client, mcp_entry)

    # 완료 메시지
    print("\n✅ 설정 완료!")
    if all_saved_secrets:
        print(f"  🔐 보안: 시크릿이 OS keyring에 저장됨 (설정 파일에 평문 없음)")
        print(f"     저장된 항목: {', '.join(all_saved_secrets)}")
    print()
    print("  선택한 클라이언트를 재시작하면 bi-agent가 활성화됩니다.")
    print()
    print("  사용 예시:")
    print('    "orders 테이블 스키마 보여줘"')
    print('    "지난 30일 일별 매출 조회해줘"')
    print()
    print("  agent를 통한 추가 설정:")
    print('    LLM에게 "bi-agent 설정 상태 확인해줘" 라고 물어보세요.')


def setup() -> None:
    """bi-agent-mcp 설치 마법사 진입점."""
    parser = argparse.ArgumentParser(
        prog="bi-agent-mcp-setup",
        description="bi-agent-mcp 설치 마법사",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  bi-agent-mcp-setup                  전체 설치 마법사
  bi-agent-mcp-setup --quick          빠른 설치
  bi-agent-mcp-setup --add ga4        GA4 추가
  bi-agent-mcp-setup --add amplitude  Amplitude 추가
  bi-agent-mcp-setup --add db         DB 재설정
        """,
    )
    parser.add_argument("--quick", "-q", action="store_true", help="빠른 설치 (최소 정보만 입력)")
    parser.add_argument("--add", metavar="SOURCE", help="개별 데이터 소스 추가 (db/ga4/amplitude)")

    args = parser.parse_args()

    if args.add:
        _run_add_source(args.add)
    elif args.quick:
        _run_quick_setup()
    else:
        _run_full_setup()


if __name__ == "__main__":
    setup()
