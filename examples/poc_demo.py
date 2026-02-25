#!/usr/bin/env python3
"""
BI-Agent PoC Demo Script
========================
자연어 쿼리 → 데이터 조회 → JSON/Excel 파일 출력 E2E 파이프라인 검증

실행 방법:
    python3 examples/poc_demo.py

요구사항:
    - .env 파일에 GEMINI_API_KEY 또는 OLLAMA_MODEL 설정
    - pip install -e . (의존성 설치)
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))


def print_section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


async def main() -> None:
    print_section("🚀 BI-Agent PoC Demo 시작")

    # ──────────────────────────────────────────────
    # Step 1: AgentConnectionManager로 샘플 DB 확인/생성
    # ──────────────────────────────────────────────
    print_section("Step 1: 샘플 데이터베이스 준비")
    try:
        import json
        from backend.agents.data_source.connection_manager import (
            ConnectionManager as AgentConnectionManager,
        )
        agent_mgr = AgentConnectionManager(project_id="default")
        # registry_path 에서 직접 읽기 (list_connections 메서드 없음)
        registry_path = agent_mgr.registry_path
        if registry_path.exists():
            with open(registry_path, "r", encoding="utf-8") as f:
                conn_registry = json.load(f)
        else:
            conn_registry = {}
        if "sample_sales" in conn_registry:
            db_path = conn_registry["sample_sales"].get("config", {}).get("path", "")
            print(f"✅ 샘플 연결 발견: sample_sales → {db_path}")
        else:
            print(f"❌ sample_sales 연결 없음. 등록된 연결: {list(conn_registry.keys())}")
            return
    except Exception as e:
        print(f"❌ AgentConnectionManager 초기화 실패: {e}")
        return

    # ──────────────────────────────────────────────
    # Step 2: AgenticOrchestrator 초기화
    # ──────────────────────────────────────────────
    print_section("Step 2: AgenticOrchestrator 초기화")
    try:
        from backend.orchestrator.orchestrators.agentic_orchestrator import AgenticOrchestrator
        orchestrator = AgenticOrchestrator(use_checkpointer=False)
        print("✅ AgenticOrchestrator 초기화 성공")
    except Exception as e:
        print(f"❌ 초기화 실패: {e}")
        return

    # active_connection을 context에 명시적으로 설정
    context = {"active_connection": "sample_sales"}

    # ──────────────────────────────────────────────
    # Step 3: 스키마 분석
    # ──────────────────────────────────────────────
    print_section("Step 3: 스키마 분석 (analyze_schema)")
    try:
        registry = orchestrator._registry
        schema_result = registry.execute(
            "analyze_schema",
            {"table_name": "sales"},
            context=context,
        )
        print(schema_result[:800])
    except Exception as e:
        print(f"⚠️  스키마 분석 오류: {e}")

    # ──────────────────────────────────────────────
    # Step 4: 월별 매출 쿼리
    # ──────────────────────────────────────────────
    print_section("Step 4: 월별 매출 집계 쿼리")
    sql = (
        "SELECT strftime('%Y-%m', sale_date) AS month, "
        "SUM(amount) AS total_revenue, COUNT(*) AS sale_count "
        "FROM sales "
        "GROUP BY month "
        "ORDER BY month"
    )
    try:
        query_result = registry.execute(
            "query_database",
            {"query_description": sql},
            context=context,
        )
        print(query_result[:1200])
    except Exception as e:
        print(f"❌ 쿼리 실패: {e}")

    # ──────────────────────────────────────────────
    # Step 5: JSON + Excel 내보내기
    # ──────────────────────────────────────────────
    print_section("Step 5: 파일 내보내기 (JSON + Excel)")
    try:
        json_result = registry.execute("export_report", {"format_type": "json"})
        print(json_result)
        excel_result = registry.execute("export_report", {"format_type": "excel"})
        print(excel_result)
    except Exception as e:
        print(f"❌ 내보내기 실패: {e}")

    # ──────────────────────────────────────────────
    # Step 6: LLM ReAct 루프 테스트 (선택적)
    # ──────────────────────────────────────────────
    print_section("Step 6: LLM ReAct 루프 E2E 테스트")
    print("💬 쿼리: 'sales 테이블의 월별 매출 합계를 분석해줘'")
    print("⏳ LLM 응답 대기 중...\n")
    try:
        result = await orchestrator.run(
            "sales 테이블의 스키마를 먼저 확인하고, 월별 매출 합계를 SQL로 조회해줘",
            context=context,
        )
        print("📊 LLM 최종 응답:")
        print(result.get("final_response", "응답 없음")[:1500])
        print(f"\n반복 횟수: {result.get('iteration_count', 0)}")
        print(f"상태: {result.get('status', 'unknown')}")
    except Exception as e:
        print(f"⚠️  LLM ReAct 루프 오류: {e}")
        print("   (API 키 미설정이거나 네트워크 오류일 수 있습니다)")

    # ──────────────────────────────────────────────
    # 최종 결과 요약
    # ──────────────────────────────────────────────
    print_section("✅ 결과 요약")
    output_dir = Path("output")
    if output_dir.exists():
        files = list(output_dir.glob("*"))
        print(f"생성된 파일 ({len(files)}개):")
        for f in files:
            size_kb = f.stat().st_size / 1024
            print(f"  📄 {f.name}  ({size_kb:.1f} KB)")
    else:
        print("output/ 디렉토리 없음")

    print("\n🎉 PoC Demo 완료!")
    print("   TUI 실행: python3 run-bi-agent.py")


if __name__ == "__main__":
    asyncio.run(main())
