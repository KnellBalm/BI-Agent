# GCP Guide: API Quota & Billing Monitoring Setup

BI-Agent가 실시간으로 할당량을 확인하고 과금을 방지하기 위해서는 GCP 프로젝트에서 몇 가지 설정이 필요합니다. 아래 단계를 따라해 주세요.

## 1. Google Cloud 콘솔 접속
[Google Cloud Console](https://console.cloud.google.com/)에 접속하여 사용할 프로젝트를 선택합니다.

## 2. 필요한 API 활성화 (가장 중요)
시스템이 할당량과 결제 정보를 읽어올 수 있도록 다음 두 API를 활성화해야 합니다.

1. **Service Usage API & Cloud Monitoring API**:
   - 상단 검색창에 `Cloud Monitoring API`를 입력하고 클릭합니다.
   - **[사용]** 또는 **[ENABLE]** 버튼을 클릭합니다.
   - 같은 방식으로 `Service Usage API`도 검색하여 활성화되어 있는지 확인합니다.

2. **Cloud Billing API**:
   - 상단 검색창에 `Cloud Billing API`를 입력하고 클릭합니다.
   - **[사용]** 또는 **[ENABLE]** 버튼을 클릭합니다.

## 3. 계정 권한 확인 (IAM)
현재 사용 중인 계정(`naca9318@gmail.com`)이 결제 정보를 읽을 수 있는 권한이 있어야 합니다.

1. 왼쪽 메뉴에서 **[IAM 및 관리자]** -> **[IAM]**를 클릭합니다.
2. 본인의 계정 옆에 다음 역할(Role) 중 하나가 포함되어 있는지 확인합니다:
   - `프로젝트 소유자 (Owner)`
   - `결제 계정 뷰어 (Billing Account Viewer)` (결제 정보 확인용)
   - `서비스 사용 뷰어 (Service Usage Viewer)` (할당량 확인용)

## 4. 로컬 환경 인증 업데이트
터미널에서 다음 명령어를 실행하여 브라우저 창이 뜨면 로그인 및 권한 허용을 완료해 주세요.

```bash
gcloud auth application-default login
```
> [!NOTE]
> 이 명령어는 Python 라이브러리가 사용자 대신 GCP API에 접근할 수 있도록 로컬 인증 토큰을 생성합니다.

## 5. 프로젝트 ID 확인
콘솔 상단 대시보드에서 **프로젝트 ID**를 복사해 두세요. (예: `my-project-1234`)
이 ID는 이후 `.env` 설정에 사용됩니다.
