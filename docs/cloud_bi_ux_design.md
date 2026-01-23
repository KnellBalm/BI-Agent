# Cloud BI Interaction UX Design (Looker Studio & Quicksight)

클라우드 기반 BI 도구는 직접적인 파일(XML/JSON) 수정이 제한적이거나 API 권한 설정이 복잡한 경우가 많습니다. 따라서 BI-Agent는 다음과 같은 UX 전략을 취합니다.

## 1. Looker Studio: Template-Link UX
Looker Studio는 URL 파라미터를 통해 리포트를 복제하고 데이터 소스를 바인딩할 수 있는 **Link API**를 제공합니다.

- **Workflow**:
  1. 에이전트가 사용자의 요구사항에 맞는 리포트 템플릿 ID를 선정.
  2. 사용자의 데이터 소스(BigQuery 등) 정보가 포함된 **커스텀 생성 URL** 생성.
  3. TUI 창에 `[Open Looker Studio Template]` 링크 제공.
  4. 사용자가 클릭 시 브라우저에서 즉시 리포트가 생성되며, 에이전트는 이후 필요한 UI 조작을 **Ask Mode**로 가이드.

## 2. AWS Quicksight: Blueprint + UI Guide
Quicksight는 AWS SDK를 통해 대시보드 정의(JSON)를 완벽하게 제어할 수 있지만, 사용자가 직접 SDK를 다루기는 어렵습니다.

- **Workflow**:
  1. 에이전트가 `DescribeAnalysisDefinition`을 통해 현재 구조 분석.
  2. 수정이 필요한 부분의 **CloudFormation/CDK Blueprint (JSON)** 생성.
  3. 동시에, AWS Console UI에서 수행해야 할 단계를 **Step-by-Step**으로 안내.
  4. 고급 사용자를 위해 AWS CLI 명령어를 생성하여 제안.

## 3. 공통: 실시간 가이드 (Live Navigator)
- TUI의 Side Log 창을 활용하여 사용자가 BI 툴 화면에서 길을 잃지 않도록 현재 위치(Context)에 기반한 도움말을 지속적으로 노출합니다.
