# /bi-connect — 데이터 소스 연결 및 컨텍스트 로드

데이터 소스에 연결하고 비즈니스 도메인 컨텍스트를 로드합니다.

## 실행 절차

1. `context/02_data_sources.md` 파일을 읽어 사용 가능한 데이터 소스 파악
2. `check_setup_status` MCP 도구로 현재 설정/연결 상태 확인
3. $ARGUMENTS가 있으면 해당 소스 연결, 없으면 미연결 소스 목록 표시 및 연결 안내
4. `connect_db` 또는 `connect_file`로 데이터 소스 연결
5. 연결 성공 후 `get_schema`로 주요 테이블 요약 출력
6. `context/01_business_context.md`를 읽어 "현재 컨텍스트: [비즈니스명]" 표시
7. 연결된 소스 요약 및 다음 단계 안내 (`/bi-explore` 또는 `/bi-analyze` 사용 제안)

## 사용법

```
/bi-connect                    # 전체 연결 상태 확인 및 안내
/bi-connect postgresql         # PostgreSQL 연결
/bi-connect file orders.csv    # CSV 파일 연결
```

## 참조 파일
- `context/01_business_context.md` — 비즈니스 컨텍스트
- `context/02_data_sources.md` — 데이터 소스 설정

## 사용 MCP 도구
- `check_setup_status` — 설정 상태 확인
- `list_connections` — 현재 연결 목록
- `connect_db(db_type, host, port, database, user, password)` — DB 연결
- `connect_file(path)` — CSV/Excel 파일 연결
- `get_schema(conn_id)` — 스키마 조회
