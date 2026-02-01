"""
Hypothesis Templates Engine for BI-Agent

Industry-specific hypothesis template system for guided data analysis.
Provides context-aware template suggestions based on available data columns.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class Industry(Enum):
    """Industry categories for hypothesis templates."""
    RETAIL = "retail"
    FINANCE = "finance"
    MANUFACTURING = "manufacturing"
    HEALTHCARE = "healthcare"
    GENERAL = "general"


@dataclass
class HypothesisTemplate:
    """
    Represents a hypothesis template with placeholders for industry-specific analysis.

    Attributes:
        template_id: Unique identifier for the template
        industry: Industry category this template belongs to
        template_text: Template string with {{placeholder}} syntax
        placeholders: List of placeholder names in the template
        description: Korean description of what this hypothesis tests
        required_columns: Column types required (e.g., ["numerical", "categorical"])
    """
    template_id: str
    industry: Industry
    template_text: str
    placeholders: List[str]
    description: str
    required_columns: List[str]

    def render(self, substitutions: Dict[str, str]) -> str:
        """
        Render template with actual values substituting placeholders.

        Args:
            substitutions: Dictionary mapping placeholder names to values

        Returns:
            Rendered hypothesis text

        Raises:
            ValueError: If not all placeholders are provided
        """
        if not self.validate_substitutions(substitutions):
            missing = set(self.placeholders) - set(substitutions.keys())
            raise ValueError(
                f"Missing required placeholders: {missing}. "
                f"Required: {self.placeholders}, Provided: {list(substitutions.keys())}"
            )

        rendered = self.template_text
        for placeholder, value in substitutions.items():
            rendered = rendered.replace(f"{{{{{placeholder}}}}}", value)

        return rendered

    def validate_substitutions(self, substitutions: Dict[str, str]) -> bool:
        """
        Validate that all required placeholders are provided.

        Args:
            substitutions: Dictionary of placeholder values

        Returns:
            True if all placeholders are present, False otherwise
        """
        return all(placeholder in substitutions for placeholder in self.placeholders)


def extract_placeholders(template_text: str) -> List[str]:
    """
    Extract all {{placeholder}} names from template text.

    Args:
        template_text: Template string with {{placeholder}} syntax

    Returns:
        List of placeholder names
    """
    pattern = r'\{\{([^}]+)\}\}'
    return re.findall(pattern, template_text)


# Industry-specific template definitions

RETAIL_TEMPLATES = [
    HypothesisTemplate(
        template_id="retail_traffic_sales",
        industry=Industry.RETAIL,
        template_text="{{매출}} 증가는 {{요일}} 트래픽과 비례한다",
        placeholders=["매출", "요일"],
        description="요일별 매출과 방문객 트래픽 간의 상관관계",
        required_columns=["numerical", "categorical"]
    ),
    HypothesisTemplate(
        template_id="retail_return_rate",
        industry=Industry.RETAIL,
        template_text="{{카테고리}}별 {{반품률}}은 계절에 따라 변동한다",
        placeholders=["카테고리", "반품률"],
        description="카테고리별 계절적 반품 패턴",
        required_columns=["categorical", "numerical"]
    ),
    HypothesisTemplate(
        template_id="retail_customer_acquisition",
        industry=Industry.RETAIL,
        template_text="{{신규고객}} 유입은 {{마케팅채널}} 효과에 의존한다",
        placeholders=["신규고객", "마케팅채널"],
        description="마케팅 채널별 신규 고객 유입 효과",
        required_columns=["numerical", "categorical"]
    ),
    HypothesisTemplate(
        template_id="retail_seasonal_sales",
        industry=Industry.RETAIL,
        template_text="{{제품군}} 매출은 {{시즌}}에 따라 증가한다",
        placeholders=["제품군", "시즌"],
        description="계절별 제품 카테고리 매출 패턴",
        required_columns=["categorical", "datetime"]
    ),
    HypothesisTemplate(
        template_id="retail_price_elasticity",
        industry=Industry.RETAIL,
        template_text="{{제품}} 수요는 {{가격}} 변동에 민감하다",
        placeholders=["제품", "가격"],
        description="가격 변동에 따른 수요 탄력성",
        required_columns=["categorical", "numerical"]
    )
]

FINANCE_TEMPLATES = [
    HypothesisTemplate(
        template_id="finance_portfolio_risk",
        industry=Industry.FINANCE,
        template_text="{{포트폴리오}} 수익률은 {{리스크지표}}와 반비례한다",
        placeholders=["포트폴리오", "리스크지표"],
        description="포트폴리오 위험도와 수익률의 관계",
        required_columns=["numerical", "numerical"]
    ),
    HypothesisTemplate(
        template_id="finance_loan_default",
        industry=Industry.FINANCE,
        template_text="{{대출}} 연체율은 {{신용등급}}에 따라 차이가 있다",
        placeholders=["대출", "신용등급"],
        description="신용등급별 대출 연체 패턴",
        required_columns=["numerical", "categorical"]
    ),
    HypothesisTemplate(
        template_id="finance_transaction_volume",
        industry=Industry.FINANCE,
        template_text="{{거래량}}은 {{시간대}}에 따라 변동한다",
        placeholders=["거래량", "시간대"],
        description="시간대별 거래 패턴 분석",
        required_columns=["numerical", "datetime"]
    ),
    HypothesisTemplate(
        template_id="finance_fraud_detection",
        industry=Industry.FINANCE,
        template_text="{{거래}} 사기 발생률은 {{거래유형}}과 {{금액}}에 영향을 받는다",
        placeholders=["거래", "거래유형", "금액"],
        description="거래 유형과 금액에 따른 사기 패턴",
        required_columns=["categorical", "categorical", "numerical"]
    ),
    HypothesisTemplate(
        template_id="finance_customer_churn",
        industry=Industry.FINANCE,
        template_text="{{고객}} 이탈률은 {{계좌활동}}과 상관관계가 있다",
        placeholders=["고객", "계좌활동"],
        description="계좌 활동 수준과 고객 이탈 관계",
        required_columns=["categorical", "numerical"]
    )
]

MANUFACTURING_TEMPLATES = [
    HypothesisTemplate(
        template_id="mfg_defect_rate",
        industry=Industry.MANUFACTURING,
        template_text="{{불량률}}은 {{생산라인}}에 따라 차이가 있다",
        placeholders=["불량률", "생산라인"],
        description="생산라인별 품질 차이 분석",
        required_columns=["numerical", "categorical"]
    ),
    HypothesisTemplate(
        template_id="mfg_downtime",
        industry=Industry.MANUFACTURING,
        template_text="{{가동중단시간}}은 {{설비연식}}과 비례한다",
        placeholders=["가동중단시간", "설비연식"],
        description="설비 노후화와 다운타임 상관관계",
        required_columns=["numerical", "numerical"]
    ),
    HypothesisTemplate(
        template_id="mfg_throughput",
        industry=Industry.MANUFACTURING,
        template_text="{{생산량}}은 {{교대근무}}와 {{설비효율}}에 영향을 받는다",
        placeholders=["생산량", "교대근무", "설비효율"],
        description="교대 근무와 설비 효율이 생산량에 미치는 영향",
        required_columns=["numerical", "categorical", "numerical"]
    ),
    HypothesisTemplate(
        template_id="mfg_quality_control",
        industry=Industry.MANUFACTURING,
        template_text="{{품질지표}}는 {{원자재공급업체}}에 따라 차이가 있다",
        placeholders=["품질지표", "원자재공급업체"],
        description="공급업체별 품질 차이 분석",
        required_columns=["numerical", "categorical"]
    ),
    HypothesisTemplate(
        template_id="mfg_maintenance",
        industry=Industry.MANUFACTURING,
        template_text="{{정비주기}}는 {{고장빈도}} 감소와 비례한다",
        placeholders=["정비주기", "고장빈도"],
        description="예방 정비 주기와 고장률의 관계",
        required_columns=["numerical", "numerical"]
    )
]

HEALTHCARE_TEMPLATES = [
    HypothesisTemplate(
        template_id="health_readmission",
        industry=Industry.HEALTHCARE,
        template_text="{{재입원율}}은 {{진료과}}에 따라 차이가 있다",
        placeholders=["재입원율", "진료과"],
        description="진료과별 재입원 패턴",
        required_columns=["numerical", "categorical"]
    ),
    HypothesisTemplate(
        template_id="health_wait_time",
        industry=Industry.HEALTHCARE,
        template_text="{{대기시간}}은 {{요일}}과 {{시간대}}에 영향을 받는다",
        placeholders=["대기시간", "요일", "시간대"],
        description="요일/시간대별 환자 대기시간 패턴",
        required_columns=["numerical", "categorical", "datetime"]
    ),
    HypothesisTemplate(
        template_id="health_treatment_outcome",
        industry=Industry.HEALTHCARE,
        template_text="{{치료성과}}는 {{환자연령}}과 {{기저질환}}에 영향을 받는다",
        placeholders=["치료성과", "환자연령", "기저질환"],
        description="환자 특성이 치료 결과에 미치는 영향",
        required_columns=["numerical", "numerical", "categorical"]
    ),
    HypothesisTemplate(
        template_id="health_resource_utilization",
        industry=Industry.HEALTHCARE,
        template_text="{{병상가동률}}은 {{계절}}에 따라 변동한다",
        placeholders=["병상가동률", "계절"],
        description="계절별 의료 자원 활용 패턴",
        required_columns=["numerical", "datetime"]
    ),
    HypothesisTemplate(
        template_id="health_medication_adherence",
        industry=Industry.HEALTHCARE,
        template_text="{{복약순응도}}는 {{처방복잡도}}와 반비례한다",
        placeholders=["복약순응도", "처방복잡도"],
        description="처방 복잡도가 복약 순응도에 미치는 영향",
        required_columns=["numerical", "numerical"]
    )
]

GENERAL_TEMPLATES = [
    HypothesisTemplate(
        template_id="general_correlation",
        industry=Industry.GENERAL,
        template_text="{{변수A}}와 {{변수B}}는 상관관계가 있다",
        placeholders=["변수A", "변수B"],
        description="두 변수 간의 일반적 상관관계 분석",
        required_columns=["numerical", "numerical"]
    ),
    HypothesisTemplate(
        template_id="general_group_difference",
        industry=Industry.GENERAL,
        template_text="{{그룹}}별 {{측정값}}에 차이가 있다",
        placeholders=["그룹", "측정값"],
        description="그룹 간 측정값 비교",
        required_columns=["categorical", "numerical"]
    ),
    HypothesisTemplate(
        template_id="general_trend",
        industry=Industry.GENERAL,
        template_text="{{지표}}는 {{시간}}에 따라 변화한다",
        placeholders=["지표", "시간"],
        description="시계열 트렌드 분석",
        required_columns=["numerical", "datetime"]
    ),
    HypothesisTemplate(
        template_id="general_proportion",
        industry=Industry.GENERAL,
        template_text="{{카테고리}}별 {{비율}}에 차이가 있다",
        placeholders=["카테고리", "비율"],
        description="카테고리별 비율 분석",
        required_columns=["categorical", "numerical"]
    )
]


class HypothesisTemplateEngine:
    """
    Hypothesis template engine for context-aware template suggestion and rendering.

    Manages industry-specific hypothesis templates and provides intelligent
    template matching based on available data columns.
    """

    def __init__(self, llm: Optional[Any] = None):
        """
        Initialize the hypothesis template engine.

        Args:
            llm: Optional LLM provider for enhanced template suggestions
        """
        self.llm = llm
        self.templates = self._load_all_templates()

    def _load_all_templates(self) -> Dict[Industry, List[HypothesisTemplate]]:
        """
        Load all predefined templates organized by industry.

        Returns:
            Dictionary mapping industries to their template lists
        """
        return {
            Industry.RETAIL: RETAIL_TEMPLATES,
            Industry.FINANCE: FINANCE_TEMPLATES,
            Industry.MANUFACTURING: MANUFACTURING_TEMPLATES,
            Industry.HEALTHCARE: HEALTHCARE_TEMPLATES,
            Industry.GENERAL: GENERAL_TEMPLATES
        }

    def suggest_templates(
        self,
        industry: Industry,
        available_columns: List[Dict[str, Any]]
    ) -> List[HypothesisTemplate]:
        """
        Context-aware template selection based on available data columns.

        Matches template requirements with actual column types in the dataset
        to suggest relevant hypothesis templates.

        Args:
            industry: Target industry for template selection
            available_columns: List of column metadata dictionaries with keys:
                - name: Column name
                - type: Column type (numerical, categorical, datetime, etc.)

        Returns:
            List of matching hypothesis templates sorted by relevance

        Example:
            >>> columns = [
            ...     {"name": "sales", "type": "numerical"},
            ...     {"name": "day_of_week", "type": "categorical"}
            ... ]
            >>> engine = HypothesisTemplateEngine()
            >>> templates = engine.suggest_templates(Industry.RETAIL, columns)
        """
        # Extract available column types
        available_types = [col.get("type", "").lower() for col in available_columns]
        type_counts = {
            "numerical": available_types.count("numerical"),
            "categorical": available_types.count("categorical"),
            "datetime": available_types.count("datetime")
        }

        # Get templates for industry (fallback to GENERAL if industry not found)
        industry_templates = self.templates.get(industry, [])
        general_templates = self.templates.get(Industry.GENERAL, [])
        all_templates = industry_templates + general_templates

        # Filter and score templates based on column availability
        matching_templates = []
        for template in all_templates:
            score = self._calculate_template_match_score(template, type_counts)
            if score > 0:
                matching_templates.append((template, score))

        # Sort by score (descending) and return templates only
        matching_templates.sort(key=lambda x: x[1], reverse=True)
        return [template for template, score in matching_templates]

    def _calculate_template_match_score(
        self,
        template: HypothesisTemplate,
        type_counts: Dict[str, int]
    ) -> float:
        """
        Calculate how well a template matches available column types.

        Args:
            template: Hypothesis template to score
            type_counts: Dictionary of available column type counts

        Returns:
            Match score (0 = no match, higher = better match)
        """
        required_types = template.required_columns

        # Check if all required types are available
        for required_type in required_types:
            if type_counts.get(required_type, 0) == 0:
                return 0.0  # Cannot use this template

        # Calculate score based on how many required columns we can fill
        # and how many extra columns we have
        base_score = 1.0

        # Bonus for having exactly the right types
        exact_match_bonus = 0.5 if len(required_types) == len([t for t in required_types if type_counts.get(t, 0) > 0]) else 0.0

        # Bonus for having multiple options for each type
        abundance_bonus = sum(min(type_counts.get(t, 0) - 1, 2) * 0.1 for t in required_types)

        return base_score + exact_match_bonus + abundance_bonus

    def render_template(
        self,
        template: HypothesisTemplate,
        substitutions: Dict[str, str]
    ) -> str:
        """
        Render a template with provided substitutions.

        Args:
            template: Hypothesis template to render
            substitutions: Dictionary mapping placeholder names to values

        Returns:
            Rendered hypothesis text

        Raises:
            ValueError: If substitutions are incomplete

        Example:
            >>> template = engine.get_template_by_id("retail_traffic_sales")
            >>> hypothesis = engine.render_template(
            ...     template,
            ...     {"매출": "주간매출", "요일": "주말"}
            ... )
        """
        return template.render(substitutions)

    def create_custom_template(
        self,
        template_text: str,
        industry: Industry,
        description: str,
        required_columns: Optional[List[str]] = None
    ) -> HypothesisTemplate:
        """
        Create a custom hypothesis template from user-defined text.

        Automatically extracts placeholders and generates a unique ID.

        Args:
            template_text: Template string with {{placeholder}} syntax
            industry: Industry category
            description: Korean description of the hypothesis
            required_columns: Optional list of required column types

        Returns:
            New HypothesisTemplate instance

        Example:
            >>> custom = engine.create_custom_template(
            ...     "{{수익}}은 {{비용}} 증가와 반비례한다",
            ...     Industry.GENERAL,
            ...     "수익과 비용의 관계"
            ... )
        """
        placeholders = extract_placeholders(template_text)

        # Generate unique ID from industry and first placeholder
        template_id = f"{industry.value}_custom_{placeholders[0] if placeholders else 'unknown'}"
        template_id = re.sub(r'[^a-z0-9_]', '_', template_id.lower())

        # Infer required columns if not provided
        if required_columns is None:
            # Default: assume first placeholder is numerical, rest categorical
            required_columns = ["numerical"] + ["categorical"] * (len(placeholders) - 1) if placeholders else []

        return HypothesisTemplate(
            template_id=template_id,
            industry=industry,
            template_text=template_text,
            placeholders=placeholders,
            description=description,
            required_columns=required_columns
        )

    def get_template_by_id(self, template_id: str) -> Optional[HypothesisTemplate]:
        """
        Find a template by its unique ID across all industries.

        Args:
            template_id: Template identifier

        Returns:
            HypothesisTemplate if found, None otherwise
        """
        for templates_list in self.templates.values():
            for template in templates_list:
                if template.template_id == template_id:
                    return template
        return None

    def get_templates_by_industry(self, industry: Industry) -> List[HypothesisTemplate]:
        """
        Get all templates for a specific industry.

        Args:
            industry: Industry category

        Returns:
            List of templates for the industry
        """
        return self.templates.get(industry, [])

    def get_all_templates(self) -> List[HypothesisTemplate]:
        """
        Get all available templates across all industries.

        Returns:
            Flat list of all templates
        """
        all_templates = []
        for templates_list in self.templates.values():
            all_templates.extend(templates_list)
        return all_templates

    def get_template_summary(self, template: HypothesisTemplate) -> Dict[str, Any]:
        """
        Get a summary dictionary for a template (useful for UI display).

        Args:
            template: Hypothesis template

        Returns:
            Dictionary with template metadata
        """
        return {
            "template_id": template.template_id,
            "industry": template.industry.value,
            "template_text": template.template_text,
            "placeholders": template.placeholders,
            "description": template.description,
            "required_columns": template.required_columns
        }
