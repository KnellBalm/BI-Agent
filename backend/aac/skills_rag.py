"""
SkillsRAGManager — skills/ 폴더 마크다운 지식 베이스 검색
Deterministic Keyword-Weighted RAG (환각 방지 설계)
"""
import os
import re
from pathlib import Path
from typing import Optional


class SkillsRAGManager:
    def __init__(self, skills_dir: str = "skills/"):
        self.skills_dir = Path(skills_dir)
        self._docs: dict[str, str] = {}  # filename -> content
        if self.skills_dir.exists():
            self.load_skills()

    def load_skills(self) -> dict[str, str]:
        """skills/ 폴더의 .md 파일을 모두 읽어 캐시"""
        self._docs = {}
        for md_file in self.skills_dir.glob("**/*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                self._docs[md_file.name] = content
            except Exception:
                pass
        return self._docs

    def retrieve(self, query: str, top_k: int = 3) -> list[str]:
        """
        Keyword-Weighted RAG:
        score = filename_match_score * 2.0 + keyword_freq_score * 1.0
        정규화 후 top_k 반환
        """
        if not self._docs:
            return []

        # 쿼리를 소문자 단어 목록으로 분리
        query_words = re.findall(r"\w+", query.lower())
        if not query_words:
            return []

        scored: list[tuple[float, str]] = []

        for filename, content in self._docs.items():
            filename_lower = filename.lower()
            content_lower = content.lower()
            content_words = re.findall(r"\w+", content_lower)
            total_words = len(content_words) or 1

            # 파일명 매칭 점수: 쿼리 단어가 파일명에 있으면 +2.0 per word
            filename_score = sum(
                2.0 for w in query_words if w in filename_lower
            )

            # 본문 키워드 빈도 점수: 등장 횟수를 총 단어 수로 정규화 * 1.0
            keyword_count = sum(content_words.count(w) for w in query_words)
            freq_score = (keyword_count / total_words) * 1.0

            total_score = filename_score + freq_score
            if total_score > 0:
                scored.append((total_score, content))

        # 점수 내림차순 정렬 후 top_k 반환
        scored.sort(key=lambda x: x[0], reverse=True)
        return [content for _, content in scored[:top_k]]

    def format_context(self, docs: list[str]) -> str:
        """LLM 주입용 컨텍스트 포맷팅"""
        if not docs:
            return ""
        parts = ["## 참고 지식 베이스\n"]
        for i, doc in enumerate(docs, 1):
            parts.append(f"### 참고 {i}\n{doc}\n")
        return "\n".join(parts)
