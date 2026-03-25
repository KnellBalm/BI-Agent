"""bi_agent_mcp.tools.orchestration 단위 테스트."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch

import bi_agent_mcp.tools.orchestration as orch_module
from bi_agent_mcp.tools.orchestration import (
    create_analysis_plan,
    get_analysis_plan,
    update_analysis_step,
    add_analysis_step,
    synthesize_findings,
    list_analysis_plans,
    complete_analysis_plan,
    delete_analysis_plan,
)


@pytest.fixture(autouse=True)
def patch_plans_dir(tmp_path, monkeypatch):
    """_PLANS_DIR을 tmp_path로 override."""
    monkeypatch.setattr(orch_module, "_PLANS_DIR", tmp_path / "plans")
    yield tmp_path / "plans"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_plan(goal="테스트 목표", steps=None, tags=None):
    """플랜을 생성하고 plan_id를 추출해 반환."""
    result = create_analysis_plan(goal=goal, steps=steps, tags=tags)
    # "플랜 생성 완료 (ID: `<id>`)" 형식에서 ID 추출
    for line in result.splitlines():
        if "ID:" in line and "`" in line:
            plan_id = line.split("`")[1]
            return plan_id
    raise AssertionError(f"plan_id 추출 실패: {result}")


# ---------------------------------------------------------------------------
# TestCreateAnalysisPlan
# ---------------------------------------------------------------------------

class TestCreateAnalysisPlan:
    def test_create_basic(self, patch_plans_dir):
        result = create_analysis_plan(goal="매출 분석")
        assert "플랜 생성 완료" in result
        assert "`" in result  # plan_id 포함
        # JSON 파일 생성 확인
        files = list(patch_plans_dir.glob("*.json"))
        assert len(files) == 1

    def test_create_with_steps(self, patch_plans_dir):
        steps = [
            {"title": "데이터 수집", "description": "DB 쿼리", "tools_hint": ["run_query"]},
            {"title": "트렌드 분석", "description": "월별 추이", "tools_hint": ["trend_analysis"]},
        ]
        result = create_analysis_plan(goal="분기 리뷰", steps=steps)
        plan_id = _make_plan.__wrapped__ if hasattr(_make_plan, "__wrapped__") else None
        # plan_id 파싱
        pid = result.split("`")[1]
        plan_file = patch_plans_dir / f"{pid}.json"
        data = json.loads(plan_file.read_text())
        assert len(data["steps"]) == 2
        assert data["steps"][0]["idx"] == 0
        assert data["steps"][1]["idx"] == 1

    def test_create_empty_goal(self):
        result = create_analysis_plan(goal="")
        assert result.startswith("[ERROR]")

    def test_create_no_duplicate_plan_id(self, patch_plans_dir, monkeypatch):
        """uuid가 이미 존재하는 ID를 먼저 반환해도 새 ID로 재시도."""
        # 미리 파일을 만들어 충돌 유발
        patch_plans_dir.mkdir(parents=True, exist_ok=True)
        fixed_ids = iter(["aabbccdd", "aabbccdd", "11223344"])
        original_uuid = orch_module.uuid

        class FakeUUID:
            class uuid4:
                def __init__(self):
                    self._hex = next(fixed_ids)

                @property
                def hex(self):
                    return self._hex

        # 첫 번째 ID로 파일 미리 생성
        (patch_plans_dir / "aabbccdd.json").write_text("{}", encoding="utf-8")

        monkeypatch.setattr(orch_module, "uuid", FakeUUID)
        result = create_analysis_plan(goal="충돌 테스트")
        assert "11223344" in result


# ---------------------------------------------------------------------------
# TestGetAnalysisPlan
# ---------------------------------------------------------------------------

class TestGetAnalysisPlan:
    def test_get_existing(self, patch_plans_dir):
        plan_id = _make_plan(goal="분석 목표 확인")
        result = get_analysis_plan(plan_id)
        assert "분석 목표 확인" in result

    def test_get_nonexistent(self):
        result = get_analysis_plan("nonexistent_id")
        assert result.startswith("[ERROR]")


# ---------------------------------------------------------------------------
# TestUpdateAnalysisStep
# ---------------------------------------------------------------------------

class TestUpdateAnalysisStep:
    def test_update_valid_transition(self, patch_plans_dir):
        steps = [{"title": "단계0", "description": ""}]
        plan_id = _make_plan(steps=steps)
        result = update_analysis_step(plan_id, step_idx=0, status="in_progress")
        assert "in_progress" in result
        assert "[ERROR]" not in result

    def test_update_with_findings(self, patch_plans_dir):
        steps = [{"title": "단계0", "description": ""}]
        plan_id = _make_plan(steps=steps)
        update_analysis_step(plan_id, step_idx=0, status="in_progress")
        update_analysis_step(plan_id, step_idx=0, status="completed", findings="매출 10% 하락 확인")
        plan_file = patch_plans_dir / f"{plan_id}.json"
        data = json.loads(plan_file.read_text())
        assert data["steps"][0]["findings"] == "매출 10% 하락 확인"

    def test_update_invalid_step_idx(self, patch_plans_dir):
        steps = [{"title": "단계0", "description": ""}]
        plan_id = _make_plan(steps=steps)
        result = update_analysis_step(plan_id, step_idx=99, status="completed")
        assert result.startswith("[ERROR]")

    def test_update_nonstandard_transition_warns(self, patch_plans_dir):
        steps = [{"title": "단계0", "description": ""}]
        plan_id = _make_plan(steps=steps)
        # pending → completed (비표준: pending은 in_progress/skipped만 허용)
        result = update_analysis_step(plan_id, step_idx=0, status="completed")
        assert "⚠️" in result


# ---------------------------------------------------------------------------
# TestAddAnalysisStep
# ---------------------------------------------------------------------------

class TestAddAnalysisStep:
    def test_add_at_end(self, patch_plans_dir):
        steps = [{"title": "기존 단계0"}, {"title": "기존 단계1"}]
        plan_id = _make_plan(steps=steps)
        result = add_analysis_step(plan_id, title="새 단계")
        assert "새 단계" in result
        plan_file = patch_plans_dir / f"{plan_id}.json"
        data = json.loads(plan_file.read_text())
        assert len(data["steps"]) == 3
        assert data["steps"][-1]["title"] == "새 단계"
        assert data["steps"][-1]["idx"] == 2

    def test_add_insert_after(self, patch_plans_dir):
        steps = [{"title": "A"}, {"title": "B"}]
        plan_id = _make_plan(steps=steps)
        add_analysis_step(plan_id, title="중간 단계", insert_after=0)
        plan_file = patch_plans_dir / f"{plan_id}.json"
        data = json.loads(plan_file.read_text())
        assert data["steps"][1]["title"] == "중간 단계"
        assert data["steps"][1]["idx"] == 1

    def test_add_negative_insert_after(self, patch_plans_dir):
        steps = [{"title": "A"}, {"title": "B"}]
        plan_id = _make_plan(steps=steps)
        add_analysis_step(plan_id, title="맨 앞 단계", insert_after=-1)
        plan_file = patch_plans_dir / f"{plan_id}.json"
        data = json.loads(plan_file.read_text())
        assert data["steps"][0]["title"] == "맨 앞 단계"
        assert data["steps"][0]["idx"] == 0

    def test_add_max_steps(self, patch_plans_dir):
        # 50개 단계로 플랜 생성
        steps = [{"title": f"단계{i}"} for i in range(50)]
        plan_id = _make_plan(steps=steps)
        result = add_analysis_step(plan_id, title="초과 단계")
        assert result.startswith("[ERROR]")
        assert "50" in result


# ---------------------------------------------------------------------------
# TestSynthesizeFindings
# ---------------------------------------------------------------------------

class TestSynthesizeFindings:
    def _setup_plan_with_completed_step(self, patch_plans_dir):
        steps = [{"title": "수집 단계", "description": ""}]
        plan_id = _make_plan(steps=steps)
        update_analysis_step(plan_id, step_idx=0, status="in_progress")
        update_analysis_step(
            plan_id, step_idx=0, status="completed",
            findings="월별 매출 데이터 수집 완료. 3월 급감 확인."
        )
        return plan_id

    def test_synthesize_summary(self, patch_plans_dir):
        plan_id = self._setup_plan_with_completed_step(patch_plans_dir)
        result = synthesize_findings(plan_id, format="summary")
        assert "수집 단계" in result
        assert "3월 급감" in result

    def test_synthesize_no_completed(self, patch_plans_dir):
        steps = [{"title": "미완료 단계"}]
        plan_id = _make_plan(steps=steps)
        result = synthesize_findings(plan_id, format="summary")
        assert result.startswith("[INFO]")

    def test_synthesize_executive_format(self, patch_plans_dir):
        plan_id = self._setup_plan_with_completed_step(patch_plans_dir)
        result = synthesize_findings(plan_id, format="executive")
        assert "수집 단계" in result
        # executive는 한 줄 요약 포함
        assert "**수집 단계**" in result


# ---------------------------------------------------------------------------
# TestListAnalysisPlans
# ---------------------------------------------------------------------------

class TestListAnalysisPlans:
    def test_list_empty(self, patch_plans_dir):
        result = list_analysis_plans()
        assert "저장된 분석 플랜이 없습니다." in result

    def test_list_with_status_filter(self, patch_plans_dir):
        plan_id1 = _make_plan(goal="플랜 A")
        plan_id2 = _make_plan(goal="플랜 B")
        # plan_id2를 completed로 변경
        complete_analysis_plan(plan_id2, final_status="completed")

        result = list_analysis_plans(status="in_progress")
        assert "플랜 A" in result
        assert "플랜 B" not in result


# ---------------------------------------------------------------------------
# TestCompleteAndDelete
# ---------------------------------------------------------------------------

class TestCompleteAndDelete:
    def test_complete_plan(self, patch_plans_dir):
        plan_id = _make_plan(goal="완료 테스트")
        result = complete_analysis_plan(plan_id, final_status="completed")
        assert "completed" in result
        plan_file = patch_plans_dir / f"{plan_id}.json"
        data = json.loads(plan_file.read_text())
        assert data["status"] == "completed"

    def test_complete_with_pending_steps(self, patch_plans_dir):
        steps = [{"title": "미완료 단계"}]
        plan_id = _make_plan(steps=steps)
        result = complete_analysis_plan(plan_id, final_status="completed")
        assert "⚠️" in result
        assert "미완료 단계" in result

    def test_delete_existing(self, patch_plans_dir):
        plan_id = _make_plan(goal="삭제 테스트")
        result = delete_analysis_plan(plan_id)
        assert "삭제됨" in result
        assert not (patch_plans_dir / f"{plan_id}.json").exists()

    def test_delete_nonexistent(self):
        result = delete_analysis_plan("doesnotexist")
        assert result.startswith("[ERROR]")
