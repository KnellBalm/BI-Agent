import asyncio
import json
from backend.agents.data_source.data_source_agent import DataSourceAgent
from backend.agents.data_source.sql_generator import SQLGenerator

async def test_saas_scaffolding():
    print("=== SaaS Scaffolding Test ===")
    
    # 설정 로드 및 Failover LLM 구성
    from backend.orchestrator.llm_provider import GeminiProvider, OllamaProvider, FailoverLLMProvider
    gemini = GeminiProvider()
    ollama = OllamaProvider()
    llm = FailoverLLMProvider(providers=[gemini, ollama])
    
    generator = SQLGenerator(llm=llm)
    agent = DataSourceAgent(sql_generator=generator)
    
    # Showcase SQL generation for BigQuery
    bq_schema = "Table: `my-project.my_dataset.sales`, Columns: id (INT), total (FLOAT)"
    bq_query = "최근 1주일간 총 매출액을 구해줘"
    sql = await agent.sql_generator.generate_sql(bq_query, "BigQuery", bq_schema)
    print(f"\n[BigQuery SQL Generation]\n{sql}")
    
    # Showcase SQL generation for Snowflake
    sf_schema = "Table: SALES_DATA, Columns: ID, AMOUNT, SALE_DATE"
    sf_query = "가장 많이 팔린 품목 3가지"
    sql = await agent.sql_generator.generate_sql(sf_query, "Snowflake", sf_schema)
    print(f"\n[Snowflake SQL Generation]\n{sql}")

    # Note: We don't execute the full MCP call here as it requires real credentials
    print("\n[Note] MCP Servers are implemented with Node.js SDKs and are ready for real credentials.")

if __name__ == "__main__":
    asyncio.run(test_saas_scaffolding())
