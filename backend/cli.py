"""
BI-Agent CLI 진입점.

bi-agent 명령어를 실행하면 Markdown-Driven REPL이 시작됩니다.
"""
import asyncio
import click


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """BI-Agent: Markdown-Driven 데이터 분석 CLI"""
    if ctx.invoked_subcommand is None:
        from backend.main import repl
        asyncio.run(repl())


if __name__ == "__main__":
    main()
