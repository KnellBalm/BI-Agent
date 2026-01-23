# Tableau Filter JSON Mapping Guide

Tableau 필터링 로직을 JSON으로 표현하기 위한 가이드입니다.

## 1. 일반 필터 (General Filter)
- **대상**: Dimension 또는 Measure
- **속성**:
    - `field`: 필터 대상 필드명
    - `type`: "categorical" (항목 선택) | "range" (범위 선택)
    - `values`: 선택된 값 리스트 또는 [min, max]
- **JSON 구조 예시**:
```json
{
  "filter_type": "categorical",
  "field": "Region",
  "selection": ["Central", "East"]
}
```

## 2. 와일드카드 필터 (Wildcard Filter)
- **속성**:
    - `condition`: "contains" | "starts_with" | "ends_with" | "exact"
- **JSON 구조 예시**:
```json
{
  "filter_type": "wildcard",
  "field": "Product Name",
  "condition": "contains",
  "value": "Smart"
}
```

## 3. 컨텍스트 필터 (Context Filter)
- **정의**: 다른 필터보다 먼저 실행되어 데이터 집합을 미리 제한.
- **속성**: `is_context`: true
