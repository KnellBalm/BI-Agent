# Testing Guidelines (테스트 가이드라인)

이 문서는 BI-Agent 프로젝트의 안정성을 유지하고, 개발 환경 오염을 방지하기 위한 테스트 작성 규칙을 정의합니다.

## 1. 파일 시스템 부작용 방지 (No File System Side-Effects)

테스트 코드는 실행 중인 호의 파일 시스템에 영구적인 흔적을 남겨서는 안 됩니다. 특히 사용자의 `~/Downloads`, `~/Documents` 등 실제 경로를 건드리는 행위는 엄격히 금지됩니다.

### 규칙:
- **`tmp_path` 픽스처 사용**: pytest에서 제공하는 `tmp_path`를 사용하여 임시 디렉토리 내에서만 파일 작업을 수행하십시오.
- **경로 모킹 (Path Mocking)**: `Path.home()`, `Path.expanduser()` 등을 모킹하여 테스트 환경이 실제 사용자 디렉토리를 가리키지 않도록 하십시오.
- **절대 경로 사용 금지**: 테스트 코드 내에 하드코딩된 절대 경로를 사용하지 마십시오.

### 예시 (Correct):
```python
def test_save_function(tmp_path):
    fake_home = tmp_path
    with patch.object(Path, "home", return_value=fake_home):
        # 테스트 수행...
```

## 2. 외부 서비스 의존성 제거

실제 데이터베이스나 외부 API(GA4, Amplitude 등)에 연결하는 테스트는 단위 테스트(Unit Test)에서 제외해야 합니다.

### 규칙:
- **Mock 사용**: 모든 외부 호출은 `unittest.mock`을 사용하여 결과값을 시뮬레이션하십시오.
- **통합 테스트 분리**: 실제 연결이 필요한 테스트는 `tests/integration/` 폴더에 별도로 관리하고, CI 환경에서 선택적으로 실행되도록 설정하십시오.

## 3. 빈 데이터 및 예외 상황 테스트

도구(Tool)가 비정상적인 입력(빈 문자열, 유효하지 않은 JSON 등)을 받았을 때 파일 시스템에 불완전한 파일을 생성하지 않는지 항상 확인하십시오.

### 체크리스트:
- [ ] 테스트 실행 후 `~/Downloads`에 새로운 `dashboard_*.html` 파일이 생성되었는가? (생성되면 안 됨)
- [ ] 임시 디렉토리는 테스트 종료 후 정리되는가?
- [ ] 로깅이 너무 과도하게 발생하지 않는가?
