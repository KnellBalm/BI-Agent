# bi-solve Workflow — Antigravity/Gemini

## 워크플로우 정의

이 워크플로우를 실행할 때 `skills/bi-solve.md` 파일을 읽고 그 안의 5개 Gate를 순서대로 따른다.

## 실행 트리거

사용자가 다음 중 하나를 말할 때 이 워크플로우를 활성화한다:
- "bi-solve", "분석 시작", "분석해줘"
- 비즈니스 문제를 설명하는 모든 입력

## Antigravity 전용 팁

Antigravity IDE 환경에서는 파일 시스템에 직접 접근할 수 있다.
- 사전 질문지 파일을 IDE에서 직접 열어 편집할 수 있다
- `context/sessions/` 디렉토리를 사이드바에 열어두면 편리하다
- Playbook 파일(`context/playbooks/`)을 참조 탭으로 열어두면 체크리스트를 보면서 진행할 수 있다

## Gate 실행 순서

`skills/bi-solve.md` 참조:
1. [G1] 문제 분류
2. [G2] 환경 체크
3. [G3] 프레임워크 승인 + 사전 질문지 생성
4. [G4] 가설 수립 및 모드 분기
5. [G5] 검증 완료
