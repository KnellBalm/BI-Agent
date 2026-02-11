"""
Text2SQL 서비스 팩토리
"""
from typing import Optional
from backend.orchestrator.services.text2sql.base import BaseText2SQLService
from backend.orchestrator.services.text2sql.local_service import LocalText2SQLService
from backend.orchestrator.services.text2sql.api_service import APIText2SQLService
from backend.utils.logger_setup import setup_logger

logger = setup_logger("text2sql_factory", "text2sql_factory.log")


class Text2SQLServiceFactory:
    """
    Text2SQL 서비스 생성 팩토리

    사용 예시:
        # Local 모드 (Ollama)
        service = Text2SQLServiceFactory.create("local")

        # API 모드 (Gemini)
        service = Text2SQLServiceFactory.create("api", provider="gemini")

        # API 모드 (Claude)
        service = Text2SQLServiceFactory.create("api", provider="claude")
    """

    @staticmethod
    def create(
        mode: str,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs
    ) -> BaseText2SQLService:
        """
        Text2SQL 서비스 생성

        Args:
            mode: "local" 또는 "api"
            provider: API 모드일 때 제공자 ("gemini", "claude", "openai")
            model_name: 사용할 모델명 (선택사항)
            **kwargs: 추가 설정

        Returns:
            BaseText2SQLService 구현체

        Raises:
            ValueError: 지원하지 않는 모드 또는 제공자
        """
        mode = mode.lower()

        if mode == "local":
            logger.info("Creating LocalText2SQLService")
            return LocalText2SQLService(
                model_name=model_name or kwargs.get("ollama_model", "qwen2.5-coder:7b"),
                base_url=kwargs.get("ollama_url", "http://localhost:11434")
            )

        elif mode == "api":
            if not provider:
                provider = "gemini"  # 기본값

            provider = provider.lower()

            if provider not in ["gemini", "claude", "openai"]:
                raise ValueError(
                    f"Unsupported API provider: {provider}. "
                    f"Choose from: gemini, claude, openai"
                )

            logger.info(f"Creating APIText2SQLService with provider: {provider}")
            return APIText2SQLService(
                provider=provider,
                model_name=model_name
            )

        else:
            raise ValueError(
                f"Unsupported mode: {mode}. Choose 'local' or 'api'"
            )

    @staticmethod
    def create_from_config(config: dict) -> BaseText2SQLService:
        """
        설정 딕셔너리로부터 서비스 생성

        Args:
            config: {
                "mode": "local" | "api",
                "provider": "gemini" | "claude" | "openai",  # API 모드일 때만
                "model_name": "...",  # 선택사항
                "ollama_url": "...",  # Local 모드일 때만
            }

        Returns:
            BaseText2SQLService 구현체
        """
        mode = config.get("mode", "local")
        provider = config.get("provider")
        model_name = config.get("model_name")

        logger.info(f"Creating service from config: mode={mode}, provider={provider}")

        return Text2SQLServiceFactory.create(
            mode=mode,
            provider=provider,
            model_name=model_name,
            ollama_url=config.get("ollama_url", "http://localhost:11434"),
            ollama_model=config.get("ollama_model", "qwen2.5-coder:7b")
        )
