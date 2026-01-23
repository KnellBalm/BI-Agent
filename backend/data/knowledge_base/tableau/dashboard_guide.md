# Tableau 대시보드 레이아웃 가이드

Tableau 대시보드를 구성하고 레이아웃을 설정하는 방법에 대한 가이드입니다.

## 1. 대시보드 기본 구성

### 대시보드 생성
**단계별 절차**:
1. 하단 탭에서 "새 대시보드" 아이콘 (모니터 모양) 클릭
2. 대시보드 크기 선택:
   - 고정 크기: Desktop (1000x800), Tablet, Phone
   - 범위: 최소/최대 크기 설정
   - 자동: 브라우저 크기에 맞춤
3. 왼쪽 패널에서 워크시트 및 개체 선택
4. 드래그 앤 드롭으로 대시보드 캔버스에 배치

**JSON 구조 예시**:
```json
{
  "dashboard": {
    "name": "Sales Overview",
    "size": {
      "type": "fixed",
      "width": 1000,
      "height": 800
    },
    "layout_type": "tiled"
  }
}
```

## 2. 레이아웃 컨테이너

### 타일 방식 (Tiled)
**특징**:
- 개체들이 격자 형태로 정렬
- 자동으로 공간 분할
- 위치 조정 시 다른 개체가 자동으로 이동

**사용 시나리오**:
- 정형화된 대시보드 구조
- 균등한 공간 배분 필요 시

### 부동 방식 (Floating)
**특징**:
- 개체를 자유롭게 겹쳐서 배치
- 픽셀 단위 위치 조정
- Z-축 순서 조정 가능

**사용 시나리오**:
- 복잡한 시각적 디자인
- 툴팁이나 설명 오버레이

**JSON 구조 예시**:
```json
{
  "layout_container": {
    "type": "floating",
    "position": {
      "x": 100,
      "y": 50,
      "width": 400,
      "height": 300
    },
    "z_index": 2
  }
}
```

## 3. 레이아웃 컨테이너 활용

### 수평 컨테이너
**단계별 절차**:
1. 왼쪽 패널에서 "수평" 컨테이너를 캔버스에 드래그
2. 컨테이너 내부에 워크시트 또는 개체 추가
3. 개체들이 자동으로 좌우로 배치됨

**활용 예시**:
- 상단 필터 바
- 나란히 배치된 KPI 카드

### 수직 컨테이너
**단계별 절차**:
1. "수직" 컨테이너를 캔버스에 드래그
2. 컨테이너 내부에 개체 추가
3. 개체들이 자동으로 위아래로 배치됨

**활용 예시**:
- 사이드바 내비게이션
- 스택 형태의 차트 배열

**JSON 구조 예시**:
```json
{
  "container": {
    "type": "horizontal",
    "children": [
      {
        "type": "worksheet",
        "name": "Sales by Region",
        "width_percentage": 50
      },
      {
        "type": "worksheet",
        "name": "Profit Trend",
        "width_percentage": 50
      }
    ]
  }
}
```

## 4. 워크시트 배치 및 크기 조정

### 워크시트 추가
**단계별 절차**:
1. 왼쪽 패널의 "시트" 섹션에서 워크시트 선택
2. 대시보드 캔버스의 원하는 위치로 드래그
3. 파란색 영역이 표시되면 드롭하여 배치
4. 모서리 또는 경계선을 드래그하여 크기 조정

**크기 조정 옵션**:
- **고정**: 정확한 픽셀 크기 지정
- **비율**: 컨테이너 크기의 백분율
- **자동**: 내용에 맞춰 자동 조정

### 워크시트 제목 및 범례
**단계별 절차**:
1. 워크시트 우측 상단의 드롭다운 메뉴 클릭
2. "제목" 체크박스로 표시/숨김 설정
3. "범례" 체크박스로 범례 표시/숨김
4. 제목 더블클릭으로 텍스트 및 스타일 편집

## 5. 필터 및 인터랙티브 요소

### 필터 추가
**단계별 절차**:
1. 워크시트에서 필터로 사용할 필드를 우클릭
2. "필터 표시" 선택
3. 대시보드로 돌아가면 필터 카드가 표시됨
4. 필터 타입 변경: 필터 카드 드롭다운 > "단일 값(목록)", "단일 값(슬라이더)" 등 선택

**필터 범위 설정**:
- 모든 워크시트 적용
- 선택한 워크시트만 적용
- 현재 워크시트만 적용

**JSON 구조 예시**:
```json
{
  "filter": {
    "field": "Region",
    "type": "single_value_list",
    "apply_to": "all_worksheets",
    "position": "right",
    "width": 200
  }
}
```

### 액션 설정
**단계별 절차**:
1. 대시보드 메뉴 > "액션" 선택
2. "액션 추가" > 액션 유형 선택:
   - **필터 액션**: 한 워크시트에서 선택 시 다른 워크시트 필터링
   - **하이라이트 액션**: 관련 데이터 강조 표시
   - **URL 액션**: 외부 링크 또는 웹 페이지 열기
   - **시트로 이동 액션**: 다른 대시보드나 시트로 이동
3. 소스 시트 및 대상 시트 선택
4. 실행 방법 선택: 마우스오버, 선택, 메뉴

**필터 액션 예시**:
```json
{
  "action": {
    "type": "filter",
    "name": "Region to Sales Filter",
    "source_sheet": "Map View",
    "target_sheets": ["Sales Detail", "Profit Analysis"],
    "trigger": "select",
    "clear_action": "show_all_values"
  }
}
```

## 6. 대시보드 개체

### 텍스트 개체
**단계별 절차**:
1. 왼쪽 패널에서 "텍스트" 개체를 캔버스에 드래그
2. 텍스트 편집 창에서 내용 입력
3. 서식 설정: 글꼴, 크기, 색상, 정렬
4. 동적 텍스트 삽입: "삽입" 메뉴 > 워크시트 이름, 필터 값 등

**활용 예시**:
- 대시보드 제목 및 설명
- 동적 부제 (선택된 필터 값 표시)
- 주석 및 인사이트

### 이미지 개체
**단계별 절차**:
1. "이미지" 개체를 캔버스에 드래그
2. 이미지 파일 선택 또는 URL 입력
3. 크기 조정 옵션 선택:
   - 맞춤
   - 채우기
   - 중앙
   - 늘이기
4. URL 액션 추가 가능 (클릭 시 링크)

### 웹 페이지 개체
**단계별 절차**:
1. "웹 페이지" 개체를 캔버스에 드래그
2. URL 입력 (예: 회사 웹사이트, Google Analytics)
3. 선택적으로 워크시트 필터 값을 URL 매개변수로 전달

## 7. 대시보드 크기 및 레이아웃 최적화

### 반응형 디자인
**단계별 절차**:
1. 대시보드 크기를 "자동" 또는 "범위"로 설정
2. 레이아웃 컨테이너를 사용하여 구조화
3. "장치 디자이너"를 사용하여 데스크톱, 태블릿, 폰 레이아웃 개별 설정
4. 각 장치 유형별로 레이아웃 조정 및 일부 개체 숨김

**장치별 레이아웃 예시**:
```json
{
  "responsive_layout": {
    "desktop": {
      "size": {"width": 1200, "height": 800},
      "visible_sheets": ["all"]
    },
    "tablet": {
      "size": {"width": 768, "height": 1024},
      "visible_sheets": ["summary", "main_chart"]
    },
    "phone": {
      "size": {"width": 375, "height": 667},
      "visible_sheets": ["summary"]
    }
  }
}
```

### 성능 최적화
**권장 사항**:
1. 대시보드당 워크시트 수 제한 (10개 이하 권장)
2. 복잡한 계산 필드 최소화
3. 데이터 추출 사용
4. 불필요한 필터 및 액션 제거
5. 시트별 데이터 필터 적용

## 8. 대시보드 서식 및 스타일

### 배경 및 테두리
**단계별 절차**:
1. 대시보드 메뉴 > "서식" > "대시보드" 선택
2. 배경 색상 설정
3. 테두리 스타일 및 색상 설정
4. 그림자 효과 추가/제거

### 일관된 색상 팔레트
**단계별 절차**:
1. 기본 설정 > "색상" 관리
2. 사용자 지정 팔레트 생성
3. 모든 워크시트에 일관되게 적용

**JSON 구조 예시**:
```json
{
  "dashboard_style": {
    "background_color": "#FFFFFF",
    "border": {
      "enabled": true,
      "color": "#CCCCCC",
      "width": 1
    },
    "padding": 10,
    "shadow": false
  }
}
```

## 9. 대시보드 게시 및 공유

### Tableau Server/Online 게시
**단계별 절차**:
1. 서버 > "통합 문서 게시" 선택
2. 서버 로그인 (처음 한 번만)
3. 프로젝트 선택
4. 권한 설정:
   - 프로젝트의 권한 상속
   - 사용자 지정 권한
5. "게시" 클릭

### 공유 옵션
- **링크 공유**: 게시된 대시보드 URL 복사
- **이메일 구독**: 예약된 스냅샷 자동 발송
- **임베드 코드**: 웹사이트에 대시보드 삽입

## 10. 메타데이터 자동 생성 예시

자연어 요청: "매출과 이익을 나란히 보여주는 대시보드를 만들어줘"

**생성될 JSON**:
```json
{
  "dashboard": {
    "name": "Sales and Profit Dashboard",
    "size": {"type": "fixed", "width": 1200, "height": 600},
    "layout": {
      "type": "horizontal_container",
      "children": [
        {
          "type": "worksheet",
          "name": "Sales by Category",
          "visual_type": "bar",
          "width_percentage": 50
        },
        {
          "type": "worksheet",
          "name": "Profit Trend",
          "visual_type": "line",
          "width_percentage": 50
        }
      ]
    },
    "filters": [
      {
        "field": "Order Date",
        "type": "range",
        "apply_to": "all_worksheets"
      }
    ]
  }
}
```

## 11. 일반적인 대시보드 패턴

### KPI 대시보드
**구조**:
- 상단: 주요 지표 카드 (수평 배열)
- 중단: 트렌드 차트 (시간 흐름)
- 하단: 상세 테이블 또는 세부 분석

### 분석 대시보드
**구조**:
- 좌측: 필터 패널 (수직 컨테이너)
- 우측 상단: 주요 차트
- 우측 하단: 보조 차트 또는 상세 정보

### 모니터링 대시보드
**구조**:
- 전체 화면 격자 레이아웃
- 실시간 데이터 새로고침
- 색상 코딩된 경고 표시

**JSON 패턴 예시 (KPI 대시보드)**:
```json
{
  "dashboard_pattern": "kpi_dashboard",
  "layout": {
    "header": {
      "type": "horizontal_container",
      "items": ["Total Sales KPI", "Total Profit KPI", "Order Count KPI"]
    },
    "body": {
      "type": "vertical_container",
      "items": [
        {"name": "Monthly Trend", "height_percentage": 60},
        {"name": "Detail Table", "height_percentage": 40}
      ]
    }
  }
}
```
