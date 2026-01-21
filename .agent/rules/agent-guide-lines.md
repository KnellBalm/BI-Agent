# BI-Agent 프로젝트 개발 가이드라인

## 1. LLM 및 과금 정책 (Zero-Cost Policy)
- **과금 최소화**: 반드시 Gemini Free Tier를 최우선으로 사용하며, Paid Tier는 보조적으로 활용한다.
- **Quota Management**: `GEMINI_API_KEYS` (쉼표로 구분된 멀티 키) 설정을 지원하고, 할당량 소진 시 자동으로 다음 키로 로테이션하거나 에러를 반환하여 의도치 않은 결제를 방지한다.
- **폐쇄망 대응**: 외부 API 사용이 불가능한 환경을 위해 로컬 Ollama를 백업 모델로 활용할 수 있도록 설계한다.

## 2. 인터페이스 표준 (TUI Priority)
- **TUI 우선**: 웹 UI보다는 터미널 기반의 `TUI (Terminal User Interface)`를 주력 인터페이스로 삼는다.
- **Visual Library**: `rich` 또는 `textual` 라이브러리를 사용하여 시각적으로 풍부하고 직관적인 터미널 경험을 제공한다.
- **로그 시각화**: Agent의 사고 과정(Chain of Thought)과 데이터 처리 상태를 생동감 있게 표현한다.

## 3. 데이터 연동 및 환경 구성
- **SaaS First**: Snowflake, BigQuery, Amazon S3 등 주요 SaaS 데이터 소스를 MCP(Model Context Protocol) 서버를 통해 연동한다.
- **환경 격리**: Python 코드는 반드시 `venv` 가상 환경 내에서 실행하며, 의존성 관리를 엄격히 한다.
- **MCP Path**: 개발 환경에서는 `connections.json`에 MCP 서버의 절대 경로를 사용하되, 배포 시에는 npx 등을 통한 상대적인 호출이 가능하도록 유연하게 설계한다.

## 4. 문서화 및 관리
- **동기화**: 기능 구현 시 반드시 `docs/PLAN.md`와 `docs/TODO.md`를 함께 업데이트하여 프로젝트 진행 상황을 투명하게 유지한다.
- **GitHub 기반**: 모든 변경 사항은 구체적인 커밋 메시지와 함께 관리한다.
