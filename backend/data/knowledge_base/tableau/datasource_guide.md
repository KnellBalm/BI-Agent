# Tableau 데이터 소스 연결 가이드

Tableau에서 데이터 소스를 연결하고 설정하는 방법에 대한 가이드입니다.

## 1. 데이터베이스 연결 (Database Connection)

### PostgreSQL 연결
**단계별 절차**:
1. Tableau 시작 화면에서 "연결" 섹션의 "서버로" 클릭
2. "PostgreSQL" 선택
3. 연결 정보 입력:
   - 서버: localhost 또는 호스트명
   - 포트: 5432 (기본값) 또는 사용자 지정 포트
   - 데이터베이스: 데이터베이스 이름
   - 인증: 사용자 이름 및 암호
4. "로그인" 클릭

**JSON 구조 예시**:
```json
{
  "connection_type": "postgresql",
  "server": "localhost",
  "port": 5432,
  "database": "sales_db",
  "authentication": "username-password",
  "username": "bi_user"
}
```

### MySQL 연결
**단계별 절차**:
1. "연결" > "서버로" > "MySQL" 선택
2. 연결 정보 입력:
   - 서버: 호스트명
   - 포트: 3306 (기본값)
   - 데이터베이스: 선택적 (나중에 선택 가능)
3. "로그인" 클릭
4. 연결된 후 왼쪽 패널에서 테이블 선택

**JSON 구조 예시**:
```json
{
  "connection_type": "mysql",
  "server": "localhost",
  "port": 3306,
  "database": "analytics",
  "ssl_mode": "preferred"
}
```

## 2. 파일 기반 데이터 소스

### Excel 파일
**단계별 절차**:
1. "연결" > "파일로" > "Microsoft Excel" 선택
2. .xlsx 또는 .xls 파일 선택
3. 워크시트 또는 명명된 범위 선택
4. 데이터 미리보기에서 첫 행을 열 이름으로 사용할지 선택

**공통 설정**:
- `첫 행을 헤더로 사용`: 체크 시 첫 번째 행이 필드 이름이 됨
- `데이터 해석기`: 자동으로 하위 테이블 감지

### CSV 파일
**단계별 절차**:
1. "연결" > "파일로" > "텍스트 파일" 선택
2. .csv 파일 선택
3. 필드 구분자 및 인코딩 확인
4. 데이터 타입 자동 감지 확인

## 3. 클라우드 데이터 소스

### Snowflake
**단계별 절차**:
1. "연결" > "서버로" > "Snowflake" 선택
2. 연결 정보 입력:
   - 서버: account_name.snowflakecomputing.com
   - 웨어하우스: 사용할 웨어하우스 이름
   - 데이터베이스 및 스키마 선택
3. 인증 방법 선택 (사용자 이름/암호 또는 OAuth)

**JSON 구조 예시**:
```json
{
  "connection_type": "snowflake",
  "account": "mycompany",
  "warehouse": "COMPUTE_WH",
  "database": "SALES_DB",
  "schema": "PUBLIC",
  "authentication": "oauth"
}
```

### BigQuery
**단계별 절차**:
1. "연결" > "서버로" > "Google BigQuery" 선택
2. OAuth를 통한 Google 계정 인증
3. 프로젝트 및 데이터세트 선택
4. 청구 프로젝트 ID 확인

## 4. 데이터 조인 및 관계 설정

### 물리적 테이블 조인
**단계별 절차**:
1. 데이터 소스 페이지에서 첫 번째 테이블을 캔버스에 드래그
2. 추가 테이블을 첫 번째 테이블 옆에 드래그
3. 조인 아이콘 클릭하여 조인 유형 선택:
   - Inner Join (내부 조인)
   - Left Join (왼쪽 조인)
   - Right Join (오른쪽 조인)
   - Full Outer Join (전체 외부 조인)
4. 조인 키 필드 설정

**JSON 구조 예시**:
```json
{
  "join_type": "inner",
  "left_table": "orders",
  "right_table": "customers",
  "conditions": [
    {
      "left_field": "customer_id",
      "operator": "=",
      "right_field": "id"
    }
  ]
}
```

### 논리적 테이블 관계
**단계별 절차**:
1. 논리적 레이어에서 테이블을 나란히 배치
2. Tableau가 자동으로 관계 감지 (동일한 필드 이름 기반)
3. 관계 편집 아이콘 클릭하여 관계 필드 수정
4. 관계 유형 선택 (다대다, 일대다 등)

## 5. 데이터 추출 (Extract)

### 추출 생성
**단계별 절차**:
1. 데이터 소스 페이지 상단의 "추출" 라디오 버튼 선택
2. "추출 편집" 클릭하여 설정:
   - 필터 추가 (필요 시)
   - 집계 수준 설정
   - 행 수 제한
3. "확인" 후 "시트로 이동"
4. 통합 문서 저장 시 .hyper 파일 생성

**추출의 장점**:
- 빠른 쿼리 성능
- 오프라인 작업 가능
- 대용량 데이터 처리 최적화

**JSON 구조 예시**:
```json
{
  "extract_settings": {
    "enabled": true,
    "filters": [
      {
        "field": "Order Date",
        "type": "range",
        "values": ["2023-01-01", "2023-12-31"]
      }
    ],
    "aggregation": "visible_dimensions",
    "row_limit": 1000000
  }
}
```

## 6. 라이브 연결 vs. 추출

### 라이브 연결 (Live Connection)
- **장점**: 항상 최신 데이터 반영
- **단점**: 네트워크 및 데이터베이스 성능에 의존
- **사용 시나리오**: 실시간 대시보드, 소규모 데이터셋

### 추출 (Extract)
- **장점**: 빠른 성능, 오프라인 작업
- **단점**: 주기적 갱신 필요
- **사용 시나리오**: 대용량 데이터, 복잡한 계산, 게시된 대시보드

## 7. 공통 연결 문제 해결

### 연결 오류
- **증상**: "데이터베이스에 연결할 수 없습니다"
- **해결 방법**:
  1. 네트워크 연결 확인
  2. 방화벽 설정 확인
  3. 자격 증명 재확인
  4. 데이터베이스 서비스 실행 상태 확인

### 성능 문제
- **증상**: 느린 쿼리, 타임아웃
- **해결 방법**:
  1. 추출 사용 고려
  2. 데이터 소스 필터 적용
  3. 인덱스 확인 (데이터베이스 측)
  4. 컨텍스트 필터 사용

## 8. 메타데이터 자동 생성 예시

자연어 요청: "PostgreSQL의 sales 테이블에 연결해줘"

**생성될 JSON**:
```json
{
  "datasource": {
    "name": "Sales Connection",
    "connection": {
      "type": "postgresql",
      "server": "localhost",
      "port": 5432,
      "database": "analytics",
      "schema": "public"
    },
    "tables": ["sales"],
    "connection_mode": "live"
  }
}
```
