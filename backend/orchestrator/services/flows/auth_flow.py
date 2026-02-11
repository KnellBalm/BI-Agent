"""Auth flow for API key setup."""
from typing import Any

from backend.orchestrator.services.question_flow import (
    FlowDefinition,
    FlowResult,
    Question,
)


PROVIDER_INFO = {
    "gemini": {
        "env_var": "GEMINI_API_KEY",
        "url": "https://aistudio.google.com/app/apikey",
        "format": '{"gemini": "your-api-key-here"}',
    },
    "claude": {
        "env_var": "ANTHROPIC_API_KEY",
        "url": "https://console.anthropic.com/settings/keys",
        "format": '{"anthropic": "your-api-key-here"}',
    },
    "openai": {
        "env_var": "OPENAI_API_KEY",
        "url": "https://platform.openai.com/api-keys",
        "format": '{"openai": "your-api-key-here"}',
    },
}


def build_auth_flow(auth_manager: Any, context_manager: Any) -> FlowDefinition:
    """Build the auth flow for API key setup.

    Args:
        auth_manager: Manager for API credentials
        context_manager: Manager for user journey context

    Returns:
        FlowDefinition: Complete auth flow configuration
    """

    def validate_api_key(value: str) -> str | None:
        """Validate API key input. Returns error message or None."""
        stripped = value.strip()
        if not stripped:
            return "API key cannot be empty"
        return None

    async def on_complete(answers: dict) -> FlowResult:
        """Handle flow completion - verify and save API key."""
        provider = answers["provider"]
        api_key = answers["api_key"]

        # Verify key
        is_valid = auth_manager.verify_key(provider, api_key)

        if not is_valid:
            return FlowResult(
                success=False,
                message="API key verification failed. Please check your key.",
                retry_from_question="api_key",
            )

        # Save credentials
        auth_manager.set_provider_key(provider, api_key)
        auth_manager.load_credentials()  # Reload

        # Update journey progress
        context_manager.update_journey_step(1)

        return FlowResult(
            success=True,
            message=f"✓ {provider.title()} API key verified and saved!",
        )

    def get_setup_info_message(answers: dict) -> str:
        """Generate provider-specific setup instructions."""
        provider = answers.get("provider", "")
        info = PROVIDER_INFO.get(provider, {})

        return f"""[bold cyan]Setup Instructions for {provider.title()}[/bold cyan]

1. Get your API key from: [link={info.get('url', '')}]{info.get('url', '')}[/link]
2. Environment variable: [yellow]{info.get('env_var', '')}[/yellow]
3. Expected format: [dim]{info.get('format', '')}[/dim]

Enter API key now?"""

    # Question 1: Provider selection
    q1_provider = Question(
        id="provider",
        prompt="Which LLM provider would you like to configure?",
        input_type="choice",
        choices=[
            ("gemini", "Gemini"),
            ("claude", "Claude"),
            ("openai", "OpenAI"),
        ],
        default="gemini",
        next_question="setup_info",
    )

    # Question 2: Setup info and confirmation
    q2_setup_info = Question(
        id="setup_info",
        prompt=get_setup_info_message,
        input_type="confirm",
        default="y",
        next_question=lambda answers: "api_key" if answers.get("setup_info") == "y" else None,
    )

    # Question 3: API key input
    q3_api_key = Question(
        id="api_key",
        prompt="Enter your API key:",
        input_type="password",
        validator=validate_api_key,
    )

    return FlowDefinition(
        flow_id="auth_setup",
        title="API Key Setup",
        questions={
            "provider": q1_provider,
            "setup_info": q2_setup_info,
            "api_key": q3_api_key,
        },
        first_question="provider",
        on_complete=on_complete,
    )
