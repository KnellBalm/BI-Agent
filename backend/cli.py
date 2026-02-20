import os
import sys
import click

@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """BI-Agent: 데이터 분석을 위한 하이브리드 인터페이스 (AaC)"""
    if ctx.invoked_subcommand is None:
        # 인자가 없으면 기존 TUI 앱 실행
        from backend.orchestrator.bi_agent_console import run_app
        run_app()

@main.command()
def init():
    """현재 디렉토리에 plan.md 템플릿과 기본 환경을 초기화합니다."""
    try:
        from backend.aac.plan_parser import PlanParser
        template = PlanParser().generate_template()
        plan_path = "plan.md"
        if os.path.exists(plan_path):
            click.secho(f"⚠ {plan_path}가 이미 존재합니다.", fg="yellow")
        else:
            with open(plan_path, "w", encoding="utf-8") as f:
                f.write(template)
            click.secho(f"✓ {plan_path} 템플릿이 생성되었습니다. (경로: {os.getcwd()})", fg="green")
            click.secho("TUI 대화창을 열고 /edit 로 편집하거나 /build 로 분석을 시작하세요.", dim=True)
    except Exception as e:
        click.secho(f"초기화 중 오류 발생: {e}", fg="red")
        sys.exit(1)

if __name__ == "__main__":
    main()
