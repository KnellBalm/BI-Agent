"""python -m bi_agent_mcp 진입점."""
import sys


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        from bi_agent_mcp.setup_cli import setup
        sys.argv = [sys.argv[0]] + sys.argv[2:]  # 'setup' 인자 제거
        setup()
    else:
        from bi_agent_mcp.server import mcp
        mcp.run()


if __name__ == "__main__":
    main()
