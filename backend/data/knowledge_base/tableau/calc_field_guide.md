# Tableau Calculated Field & LOD Mapping Guide

복잡한 계산 로직 및 LOD(Level of Detail) 표현식을 JSON으로 매칭하는 가이드입니다.

## 1. 산술 계산 (Basic Calculation)
- **수식 예시**: `[Sales] - [Cost]`
- **JSON 구조**:
```json
{
  "calc_name": "Profit Margin",
  "formula": "([Sales] - [Cost]) / [Sales]",
  "output_type": "float"
}
```

## 2. LOD 표현식 (FIXED)
- **정의**: 지정된 차원을 기준으로 집계.
- **수식 예시**: `{ FIXED [Region] : SUM([Sales]) }`
- **JSON 구조**:
```json
{
  "calc_type": "LOD",
  "keyword": "FIXED",
  "dimensions": ["Region"],
  "aggregation": "SUM",
  "field": "Sales"
}
```

## 3. 조건문 (IF-THEN)
- **수식 예시**: `IF [Sales] > 1000 THEN "High" ELSE "Low" END`
- **JSON 구조**:
```json
{
  "calc_type": "conditional",
  "conditions": [
    {"if": "[Sales] > 1000", "then": "High"},
    {"else": "Low"}
  ]
}
```
