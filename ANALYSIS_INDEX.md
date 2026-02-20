# BI-Agent TUI 성능 분석 - 완전 가이드

**작성일**: 2026-02-20
**분석 대상**: `/Users/zokr/python_workspace/BI-Agent`
**주제**: TUI 비동기 처리 및 성능 최적화

---

## 📚 문서 구조

### 1. **TUI_ASYNC_ANALYSIS.md** (829줄, 26KB)
   **가장 상세한 분석 문서**

   #### 포함 내용
   - profiler.py 전체 내용 및 성능 분석
   - async def가 있는 모든 주요 파일 목록 (17개 파일)
   - TUI 메인 진입점 (bi_agent_console.py, main.py)
   - Blocking call 분석 (데이터베이스 쿼리, 프로파일링)
   - 성능 최적화 권장사항 (우선순위별)
   - 성능 개선 예상치

   #### 주요 섹션
   ```
   1. profiler.py 전체 내용
      └─ 220줄 코드 + 상세 설명
      └─ 성능 특성표 (개요/컬럼분석/분포/전체)

   2. async def 주요 파일 목록
      └─ 데이터소스 에이전트 (7개 파일)
      └─ ReAct 루프 (agentic_orchestrator)
      └─ TUI 스크린 (database_explorer_screen)

   3. TUI 메인 진입점
      └─ BI_AgentConsole (Textual App)
      └─ main.py (구형 Entry Point)
      └─ 핵심 메서드 분석

   4. Blocking Call 분석
      └─ DatabaseExplorerScreen (올바른 사용)
      └─ AgenticOrchestrator (문제점)
      └─ MetadataScanner (깊은 스캔)

   5. 최적화 권장사항
      └─ 우선순위 1: MetadataScanner async 리팩토링
      └─ 우선순위 2: ConnectionManager 비동기 래핑
      └─ 우선순위 3: 캐싱 및 스트리밍
   ```

   #### 대상 독자
   - 아키텍처 설계자
   - 성능 최적화 담당자
   - 비동기 프로그래밍 배우는 개발자

---

### 2. **BLOCKING_CALLS_SUMMARY.md** (577줄, 19KB)
   **실행 가능한 코드 중심 분석**

   #### 포함 내용
   - 프로젝트 구조 (파일 위치 + 상태 표시)
   - 4가지 주요 Blocking Call 상세 분석
   - 각 파일별 문제 코드 + 설명
   - 전체 Blocking Call 요약표
   - 이미 올바르게 구현된 부분 (모범 사례)
   - 핵심 결론 및 우선순위

   #### 주요 섹션
   ```
   1. 프로젝트 구조
      └─ 파일 위치 + ⚠️/✅ 상태 표시

   2. 4가지 Blocking Call 상세 분석
      └─ profiler.py - DataProfiler
      └─ connection_manager.py - ConnectionManager
      └─ metadata_scanner.py - MetadataScanner
      └─ agentic_orchestrator.py - ToolRegistry

   3. 각 함수별 성능 분석
      └─ 코드 스니펫
      └─ 성능 계산식
      └─ 사용처 추적

   4. 요약표
      └─ 모든 Blocking Call 한눈에
      └─ 소요시간 + 해결책

   5. 모범 사례
      └─ DatabaseExplorerScreen (올바른 사용)
      └─ BI_AgentConsole (async 메서드)
   ```

   #### 대상 독자
   - 코드를 직접 수정하는 개발자
   - 성능 디버깅을 하는 엔지니어
   - 신입 개발자 (실제 코드 예제 학습)

---

## 🎯 핵심 발견사항

### 1️⃣ 가장 심각한 성능 문제

#### MetadataScanner.scan_source(deep_scan=True)
```
예상 소요 시간: 55초 이상
테이블 50개 × (100ms 쿼리 + 1.1초 프로파일링) = 55초

UI 상태: 🔴 완전 프리징
사용자는 아무것도 할 수 없음
```

#### AgenticOrchestrator.analyze_schema()
```
예상 소요 시간: 15-60초
5개 테이블 × (10ms + 2-10초 COUNT) = 15-60초

UI 상태: 🔴 완전 프리징
ReAct 루프 중단
```

#### ConnectionManager.run_query()
```
예상 소요 시간: 100ms-10초 (네트워크 대기)

UI 상태: 🔴 프리징
PostgreSQL/MySQL의 경우 3-5초 대기
```

### 2️⃣ DataProfiler는 동기이지만 구현이 좋음

```python
# 현재: 직접 호출하면 블로킹
profile_data = profiler.profile()  # 1-2초

# DatabaseExplorerScreen에서: run_in_executor로 해결
metadata = await loop.run_in_executor(None, _scan_metadata)  # ✅
```

### 3️⃣ 이미 올바르게 구현된 부분

- **DatabaseExplorerScreen**: ✅ `run_in_executor` 사용
- **bi_agent_console**: ✅ `async def` 및 `await` 사용
- **text2sql_generator**: ✅ `async def` 및 LLM I/O

---

## 📊 성능 개선 예상치

### Before (현재)

| 시나리오 | 소요 시간 | UI 상태 |
|---------|---------|--------|
| 50개 테이블 deep scan | 55초 | 🔴 완전 프리징 |
| 5개 테이블 스키마 분석 | 15-60초 | 🔴 완전 프리징 |
| 대용량 쿼리 (1M행) | 5-10초 | 🔴 프리징 |

### After (우선순위 1 적용)

| 시나리오 | 소요 시간 | UI 상태 |
|---------|---------|--------|
| 50개 테이블 deep scan (5병렬) | 11초 | 🟢 반응 가능 |
| 5개 테이블 스키마 분석 (병렬) | 3-12초 | 🟢 반응 가능 |
| 대용량 쿼리 (run_in_executor) | 5-10초 | 🟢 반응 가능 |

**개선 효과: 55초 → 11초 (5배 개선!)**

---

## 🚀 빠른 시작 - 개선 로드맵

### Phase 1: 긴급 (1-2일)
```python
# 1. MetadataScanner를 async로 변경
async def scan_source(self, conn_id: str, deep_scan: bool = False):
    tasks = [
        asyncio.create_task(self._scan_table_async(conn_id, table))
        for table in table_names[:10]  # 최대 10개 동시
    ]
    return await asyncio.gather(*tasks)

# 2. ToolRegistry 도구를 async로 변경
async def query_database_async(query_description: str = "") -> str:
    loop = asyncio.get_event_loop()
    def _execute():
        # ... SQLite 쿼리
    rows = await loop.run_in_executor(None, _execute)
    return format_result(rows)
```

### Phase 2: 중요 (3-5일)
```python
# 1. ConnectionManager 래퍼 추가
class AsyncConnectionManager:
    async def run_query_async(self, conn_id: str, query: str):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.sync_cm.run_query(conn_id, query)
        )

# 2. ProfileCache 추가
class ProfileCache:
    def get(self, conn_id: str, table_name: str) -> Optional[Dict]:
        # ... TTL 확인
    def set(self, conn_id: str, table_name: str, data: Dict):
        # ... 캐시 저장
```

### Phase 3: 최적화 (1주)
```python
# 1. 배치 쿼리 실행
async def run_queries_batch(self, conn_id: str, queries: List[str]):
    tasks = [
        loop.run_in_executor(None, lambda q=q: self.run_query(conn_id, q))
        for q in queries
    ]
    return await asyncio.gather(*tasks)

# 2. 스트리밍 결과
async def run_query_streaming(self, conn_id: str, query: str, batch_size=1000):
    for batch_df in pd.read_sql_query(query, ..., chunksize=batch_size):
        yield batch_df
        await asyncio.sleep(0)
```

---

## 📍 파일별 상태 표

| 파일 | 상태 | 조치 필요 |
|------|------|---------|
| profiler.py | ✅ 좋음 (executor로 감싸면 됨) | 우선순위 2 |
| connection_manager.py | ⚠️ run_query() 동기 | 우선순위 2 |
| metadata_scanner.py | 🔴 모든 메서드 동기 + 병렬화 필요 | **우선순위 1** |
| table_recommender.py | ✅ async def 있음 | 없음 |
| sql_generator.py | ✅ async def 있음 | 없음 |
| query_healer.py | ✅ async def 있음 | 없음 |
| pandas_generator.py | ✅ async def 있음 | 없음 |
| data_source_agent.py | ✅ async def 있음 | 없음 |
| mcp_client.py | ✅ async def 있음 | 없음 |
| bi_agent_console.py | ✅ async/await 좋음 | 없음 |
| database_explorer_screen.py | ✅ run_in_executor 사용 | 없음 |
| agentic_orchestrator.py | 🔴 ToolRegistry 도구 동기 | 우선순위 1 |

---

## 🔗 문서 네비게이션

### 깊이 있는 분석이 필요한 경우
👉 **TUI_ASYNC_ANALYSIS.md** 참고
- 각 메서드의 성능 특성
- 최적화 코드 예제
- 체크리스트

### 코드 수정이 필요한 경우
👉 **BLOCKING_CALLS_SUMMARY.md** 참고
- 정확한 코드 위치
- 문제 코드 스니펫
- 해결책 코드 스니펫

### 빠른 개요가 필요한 경우
👉 **이 문서 (ANALYSIS_INDEX.md)** 참고
- 핵심 발견사항
- 개선 로드맵
- 상태 표

---

## 💾 파일 위치 요약

```
/Users/zokr/python_workspace/BI-Agent/
├── TUI_ASYNC_ANALYSIS.md          ← 상세 분석 (829줄)
├── BLOCKING_CALLS_SUMMARY.md      ← 코드 중심 분석 (577줄)
├── ANALYSIS_INDEX.md              ← 이 문서 (네비게이션)
│
├── backend/
│   ├── agents/data_source/
│   │   ├── profiler.py            ✅ (220줄)
│   │   ├── connection_manager.py  ⚠️ (385줄)
│   │   ├── metadata_scanner.py    🔴 (118줄)
│   │   └── ... (13개 파일)
│   │
│   ├── orchestrator/
│   │   ├── bi_agent_console.py    ✅ (418줄)
│   │   ├── orchestrators/
│   │   │   └── agentic_orchestrator.py  🔴 (500+줄)
│   │   └── screens/
│   │       └── database_explorer_screen.py  ✅ (699줄)
│   │
│   └── main.py                    ✅ (172줄)
```

---

## ⏱️ 예상 작업 시간

| 작업 | 난이도 | 예상 시간 | 영향 |
|------|--------|---------|------|
| MetadataScanner async 리팩토링 | 중간 | 4-6시간 | 🔴 높음 |
| ToolRegistry 도구 async 변경 | 중간 | 3-4시간 | 🔴 높음 |
| ConnectionManager 래퍼 추가 | 낮음 | 1-2시간 | 🟡 중간 |
| ProfileCache 구현 | 낮음 | 2-3시간 | 🟡 중간 |
| 배치/스트리밍 쿼리 | 중간 | 4-6시간 | 🟢 낮음 |

**총 예상 시간: 14-21시간 (2-3일)**

---

## 🎓 학습 포인트

### 1. AsyncIO 패턴
```python
# run_in_executor: 동기 함수를 비동기로 래핑
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(None, sync_function)

# gather: 여러 코루틴 병렬 실행
results = await asyncio.gather(*tasks)

# wait_for: 타임아웃 지원
result = await asyncio.wait_for(coroutine, timeout=30.0)
```

### 2. Textual 프레임워크
```python
# 비동기 메서드
async def on_mount(self) -> None:
    asyncio.create_task(self._background_work())

# 스레드 풀 작업
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(None, blocking_function)
```

### 3. 성능 측정
```python
import time

start = time.time()
# ... 작업 ...
duration = time.time() - start
print(f"소요 시간: {duration:.2f}초")
```

---

## 🏁 결론

### 현재 상태
- ✅ TUI 프레임워크 (Textual) 올바르게 사용
- ✅ 일부 스크린 (DatabaseExplorer) 올바르게 구현
- 🔴 MetadataScanner 병렬화 필수
- 🔴 AgenticOrchestrator 도구 async 필요

### 권장 조치
1. **즉시**: MetadataScanner async 리팩토링 (55s → 11s 기대)
2. **이후**: ToolRegistry 도구 async 변경
3. **그다음**: 캐싱 및 최적화

### 예상 효과
- 50개 테이블 스캔: **5배 개선**
- UI 반응성: **즉각적**
- 사용자 경험: **우수**

---

**작성자**: Claude Code Explorer
**마지막 업데이트**: 2026-02-20
**다음 검토 예정**: 개선 작업 완료 후
