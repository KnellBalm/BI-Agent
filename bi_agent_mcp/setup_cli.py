"""bi-agent-mcp 대화형 설치 마법사."""

import getpass
import json
import sys
from pathlib import Path

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

DB_TYPES = ["PostgreSQL", "MySQL", "BigQuery"]


def _prompt(msg: str, default: str = "") -> str:
    """입력 프롬프트. 빈 입력 시 default 반환."""
    if default:
        val = input(f"{msg} [{default}]: ").strip()
        return val if val else default
    return input(f"{msg}: ").strip()


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

    if raw.lower() == "all":
        selected_names = client_names
    else:
        indices = []
        for tok in raw.split():
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

    # 직접 경로 입력 처리
    result = []
    for name in selected_names:
        info = dict(CLIENTS[name])
        if name == "직접 경로 입력":
            path_str = _prompt("설정 파일 경로 입력 (예: ~/.config/myapp/mcp.json)")
            info["config_path"] = path_str
            info["name"] = name
        else:
            info["name"] = name
        result.append(info)

    return result


def _select_db_type() -> str:
    """DB 타입 선택."""
    print("\n🗄️  데이터베이스 타입 선택\n")
    for i, db in enumerate(DB_TYPES, 1):
        print(f"  {i}) {db}")
    print()

    while True:
        raw = _prompt("DB 타입 번호 입력").strip()
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(DB_TYPES):
                return DB_TYPES[idx]
        except ValueError:
            pass
        print("  올바른 번호를 입력하세요.")


def _collect_db_env(db_type: str) -> dict:
    """DB 연결 정보 수집 후 환경변수 dict 반환."""
    print(f"\n🔌 {db_type} 연결 정보 입력\n")

    if db_type == "PostgreSQL":
        host = _prompt("Host", "localhost")
        port = _prompt("Port", "5432")
        dbname = _prompt("Database name")
        user = _prompt("User")
        password = getpass.getpass("Password: ")
        return {
            "BI_AGENT_PG_HOST": host,
            "BI_AGENT_PG_PORT": port,
            "BI_AGENT_PG_DBNAME": dbname,
            "BI_AGENT_PG_USER": user,
            "BI_AGENT_PG_PASSWORD": password,
        }

    if db_type == "MySQL":
        host = _prompt("Host", "localhost")
        port = _prompt("Port", "3306")
        dbname = _prompt("Database name")
        user = _prompt("User")
        password = getpass.getpass("Password: ")
        return {
            "BI_AGENT_MYSQL_HOST": host,
            "BI_AGENT_MYSQL_PORT": port,
            "BI_AGENT_MYSQL_DBNAME": dbname,
            "BI_AGENT_MYSQL_USER": user,
            "BI_AGENT_MYSQL_PASSWORD": password,
        }

    # BigQuery
    project_id = _prompt("GCP Project ID")
    dataset = _prompt("Dataset")
    credentials_path = _prompt("Service account JSON 경로 (선택, 엔터로 건너뜀)").strip()
    env: dict = {
        "BI_AGENT_BQ_PROJECT_ID": project_id,
        "BI_AGENT_BQ_DATASET": dataset,
    }
    if credentials_path:
        env["BI_AGENT_BQ_CREDENTIALS_PATH"] = credentials_path
    return env


def _build_mcp_entry(env: dict) -> dict:
    """MCP 서버 엔트리 생성."""
    return {
        "command": sys.executable,
        "args": ["-m", "bi_agent_mcp"],
        "env": env,
    }


def _write_config(client: dict, mcp_entry: dict) -> None:
    """클라이언트 설정 파일에 bi-agent 엔트리 기록."""
    name = client["name"]
    raw_path = client["config_path"]
    if not raw_path:
        print(f"  ⚠️  {name}: 설정 파일 경로가 없습니다. 건너뜁니다.")
        return

    config_path = Path(raw_path).expanduser()

    # 디렉토리 생성
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # 기존 파일 읽기
    existing: dict = {}
    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = {}

    # mcpServers 키 업데이트 (다른 서버 보존)
    if "mcpServers" not in existing:
        existing["mcpServers"] = {}
    existing["mcpServers"]["bi-agent"] = mcp_entry

    # 파일 쓰기
    try:
        with config_path.open("w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"  ✅ {name}: {config_path}")
    except OSError as e:
        print(f"  ❌ {name}: 파일 쓰기 실패 - {e}")


def setup() -> None:
    """bi-agent-mcp 대화형 설치 마법사."""
    print("🚀 bi-agent-mcp 설정 마법사")
    print("=" * 40)

    # 1. 클라이언트 선택
    selected_clients = _select_clients()

    # 2. DB 타입 선택
    db_type = _select_db_type()

    # 3. DB 연결 정보 입력
    env = _collect_db_env(db_type)

    # 4. MCP 엔트리 생성 (sys.executable 사용)
    mcp_entry = _build_mcp_entry(env)

    # 5. 각 클라이언트 설정 파일 작성
    print("\n📝 설정 파일 작성 중...\n")
    for client in selected_clients:
        _write_config(client, mcp_entry)

    # 6. 완료 메시지
    print("\n✅ 설정 완료!")
    print("선택한 클라이언트를 재시작하면 bi-agent가 활성화됩니다.")
    print("\n사용 예시:")
    print('  "orders 테이블 스키마 보여줘"')
    print('  "지난 30일 일별 매출 조회해줘"')


if __name__ == "__main__":
    setup()
