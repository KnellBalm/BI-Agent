"""
AaC Plan Parser — plan.md 마크다운 파일 파서
python-frontmatter 기반 YAML 헤더 + 본문 분리, 3단계 폴백
"""
from dataclasses import dataclass, field
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
