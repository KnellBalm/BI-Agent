"""
AaC Plan Parser — plan.md 마크다운 파일 파서
python-frontmatter 기반 YAML 헤더 + 본문 분리, 3단계 폴백
"""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
import re
import os
import logging

logger = logging.getLogger(__name__)


@dataclass
class AnalysisIntent:
    goal: str = ""
    data_sources: list = field(default_factory=list)
    metrics: list = field(default_factory=list)
    context: str = ""
    raw_yaml: dict = field(default_factory=dict)
    raw_body: str = ""


class AnalysisStage(Enum):
    """ALIVE 분석 스테이지."""
    ASK = "ask"
    LOOK = "look"
    INVESTIGATE = "investigate"
    VOICE = "voice"
    EVOLVE = "evolve"

    def next(self) -> Optional['AnalysisStage']:
        """다음 스테이지를 반환합니다. EVOLVE이면 None."""
        members = list(AnalysisStage)
        idx = members.index(self)
        return members[idx + 1] if idx < len(members) - 1 else None

    @property
    def has_bi_exec(self) -> bool:
        """v1에서 BI-EXEC 실행을 지원하는 스테이지 (1-3)."""
        return self in (AnalysisStage.ASK, AnalysisStage.LOOK, AnalysisStage.INVESTIGATE)

    @property
    def file_prefix(self) -> str:
        """스테이지 파일 번호 접두사 (예: '01')."""
        members = list(AnalysisStage)
        idx = members.index(self)
        return f"{idx + 1:02d}"


@dataclass
class AnalysisProject:
    """ALIVE 분석 프로젝트 상태."""
    id: str
    title: str
    type: str          # "full" | "quick"
    status: AnalysisStage
    connection: str
    data_sources: list
    path: Path         # 폴더 경로
    created: str
    updated: str
    tags: list = field(default_factory=list)

    def current_stage_file(self) -> Path:
        """현재 스테이지의 MD 파일 경로."""
        return self.path / f"{self.status.file_prefix}-{self.status.value}.md"

    def stage_file(self, stage: 'AnalysisStage') -> Path:
        """지정된 스테이지의 MD 파일 경로."""
        return self.path / f"{stage.file_prefix}-{stage.value}.md"

    def completed_stage_files(self) -> list:
        """현재 스테이지 이전의 완료된 스테이지 파일 경로 목록."""
        members = list(AnalysisStage)
        current_idx = members.index(self.status)
        return [self.stage_file(s) for s in members[:current_idx]]


class PlanParser:
    """plan.md 마크다운 파일을 파싱하여 AnalysisIntent로 변환."""

    def parse(self, content: str) -> AnalysisIntent:
        """3단계 폴백으로 content를 파싱하여 AnalysisIntent 반환.

        1단계: python-frontmatter로 YAML 헤더 파싱
        2단계: 정규식으로 마크다운 헤딩 추출
        3단계: LLM stub (경고 로그 + 빈 AnalysisIntent 반환)
        """
        # 1단계: python-frontmatter
        try:
            import frontmatter
            post = frontmatter.loads(content)
            meta = dict(post.metadata)
            body = post.content

            if meta:
                return AnalysisIntent(
                    goal=meta.get("goal", ""),
                    data_sources=meta.get("data_sources", []),
                    metrics=meta.get("metrics", []),
                    context=body.strip(),
                    raw_yaml=meta,
                    raw_body=body,
                )
        except Exception as e:
            logger.debug("frontmatter 파싱 실패, 정규식 폴백: %s", e)

        # 2단계: 정규식으로 헤딩 추출
        try:
            goal = ""
            context = ""

            goal_match = re.search(
                r"^##\s+목표\s*\n(.*?)(?=^##|\Z)",
                content,
                re.MULTILINE | re.DOTALL,
            )
            if goal_match:
                goal = goal_match.group(1).strip()

            bg_match = re.search(
                r"^##\s+배경\s*\n(.*?)(?=^##|\Z)",
                content,
                re.MULTILINE | re.DOTALL,
            )
            if bg_match:
                context = bg_match.group(1).strip()

            if goal or context:
                return AnalysisIntent(
                    goal=goal,
                    context=context,
                    raw_body=content,
                )
        except Exception as e:
            logger.debug("정규식 파싱 실패, LLM stub 폴백: %s", e)

        # 3단계: LLM stub
        logger.warning(
            "plan.md 파싱 실패: frontmatter와 정규식 모두 실패. "
            "빈 AnalysisIntent를 반환합니다. LLM 기반 파싱은 추후 구현 예정입니다."
        )
        return AnalysisIntent(raw_body=content)

    def parse_file(self, path: str) -> AnalysisIntent:
        """파일을 읽어 parse()를 호출."""
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return self.parse(content)

    def generate_template(self) -> str:
        """분석 계획 마크다운 템플릿 반환."""
        return '''\
---
goal: "여기에 분석 목표를 입력하세요"
data_sources:
  - "연결된 데이터소스 ID"
metrics:
  - "분석할 지표 1"
  - "분석할 지표 2"
---

## 배경 및 목적
이 분석의 배경과 목적을 여기에 작성하세요.

## 세부 분석 요구사항
- 분석 요구사항 1
- 분석 요구사항 2

## 기대 결과물
- 예상 차트 또는 인사이트를 여기에 작성하세요.
'''

    def parse_stage_file(self, path: str) -> dict:
        """ALIVE 스테이지 MD 파일에서 구조화된 데이터를 추출합니다.

        Returns:
            dict with keys: stage, title, question, scope, hypotheses,
                          success_criteria, data_requirements, observations
        """
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        result = {
            'stage': None,
            'title': None,
            'question': None,
            'scope': None,
            'hypotheses': [],
            'success_criteria': [],
            'data_requirements': {},
            'observations': [],
        }

        # 제목 추출 (# ASK - 제목)
        title_match = re.match(r'^#\s+(\w+)\s+-\s+(.+)$', content, re.MULTILINE)
        if title_match:
            result['stage'] = title_match.group(1).lower()
            result['title'] = title_match.group(2).strip()

        # 각 섹션 추출
        sections = {
            'question': r'^##\s+Question\s*\n(.*?)(?=^##|\Z)',
            'scope': r'^##\s+Scope\s*\n(.*?)(?=^##|\Z)',
            'observations': r'^##\s+Initial Observations\s*\n(.*?)(?=^##|\Z)',
        }

        for key, pattern in sections.items():
            m = re.search(pattern, content, re.MULTILINE | re.DOTALL)
            if m:
                text = m.group(1).strip()
                if key == 'observations':
                    # 리스트 항목 추출
                    result[key] = [
                        line.lstrip('- ').strip()
                        for line in text.splitlines()
                        if line.strip().startswith('-')
                    ]
                else:
                    result[key] = text

        # 가설 목록 추출
        hyp_match = re.search(
            r'^##\s+Hypothesis Tree\s*\n(.*?)(?=^##|\Z)',
            content, re.MULTILINE | re.DOTALL
        )
        if hyp_match:
            result['hypotheses'] = [
                re.sub(r'^\d+\.\s+', '', line).strip()
                for line in hyp_match.group(1).splitlines()
                if re.match(r'^\d+\.', line.strip())
            ]

        return result
