# Tableau Chart JSON Mapping Guide

Tableau 시각화를 구조화된 JSON으로 변환하거나 생성할 때의 표준 매핑 규칙입니다.

## 1. 막대 차트 (Bar Chart)
- **정의**: 범주별 정량적 비교를 위해 사용.
- **필수 요소**:
    - `marks_type`: "bar"
    - `encodings`:
        - `columns`: Dimension (e.g., [Category])
        - `rows`: Measure (e.g., SUM([Sales]))
- **JSON 구조 예시**:
```json
{
  "chart_type": "bar",
  "dimensions": [{"field": "Category", "role": "columns"}],
  "measures": [{"field": "Sales", "aggregation": "SUM", "role": "rows"}]
}
```

## 2. 라인 차트 (Line Chart)
- **정의**: 시간 흐름에 따른 추세 분석.
- **필수 요소**:
    - `marks_type`: "line"
    - `encodings`:
        - `columns`: Date Dimension (e.g., YEAR([Order Date]))
        - `rows`: Measure
- **JSON 구조 예시**:
```json
{
  "chart_type": "line",
  "dimensions": [{"field": "Order Date", "role": "columns", "granularity": "YEAR"}],
  "measures": [{"field": "Profit", "aggregation": "SUM", "role": "rows"}]
}
```

## 3. 공통 마크 속성
- `color`: 특정 필드에 따른 색상 구분 (encodings.color)
- `size`: 마크 크기 조절 (encodings.size)
- `label`: 텍스트 레이블 표시 (encodings.text)
