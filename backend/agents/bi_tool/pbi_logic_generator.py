from typing import Dict, Any

class PBILogicGenerator:
    """
    Power BI DAX 및 M 쿼리 생성 엔진
    """
    def __init__(self):
        self.dax_templates = {
            "yoy_growth": "YoY Growth = VAR PriorYear = CALCULATE([Total Sales], SAMEPERIODLASTYEAR('Date'[Date])) RETURN DIVIDE([Total Sales] - PriorYear, PriorYear)",
            "mtd_sales": "MTD Sales = TOTALMTD([Total Sales], 'Date'[Date])"
        }

    def generate_dax(self, measure_type: str, context: Dict[str, Any] = None) -> str:
        """
        사용자 의도에 맞는 DAX 수식을 생성합니다.
        """
        # 실제 환경에서는 LLM을 통해 동적 생성하지만, 여기서는 템플릿 기반으로 시작
        dax = self.dax_templates.get(measure_type, "Calculated Measure = [TargetField] * 1.0")
        
        if context:
            for key, value in context.items():
                dax = dax.replace(f"[{key}]", f"[{value}]")
        
        return dax

    def generate_m_query(self, source_type: str, table_path: str) -> str:
        """
        Power Query(M) 로직을 생성합니다.
        """
        if source_type == "csv":
            return f'let Source = Csv.Document(File.Contents("{table_path}"),[Delimiter=",", Columns=5, Encoding=65001, QuoteStyle=QuoteStyle.None]), #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]) in #"Promoted Headers"'
        return "let Source = Unknown in Source"
