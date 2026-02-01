from setuptools import setup, find_packages

setup(
    name="bi-agent",
    version="0.1.0",
    author="BI-Agent Team",
    author_email="info@bi-agent.ai",
    description="Autonomous Business Intelligence Agent with Proactive Insights",
    packages=find_packages(),
    install_requires=[
        "textual>=0.47.1",
        "google-genai",
        "pandas",
        "duckdb",
        "plotly",
        "httpx",
        "rich",
        "python-dotenv",
        "google-auth",
        "google-auth-oauthlib",
        "anthropic",
        "openai",
        "mcp",
    ],
    entry_points={
        "console_scripts": [
            "bi-agent=backend.orchestrator.bi_agent_console:run_app",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.js", "*.json", "*.css", "*.md"],
    },
)
