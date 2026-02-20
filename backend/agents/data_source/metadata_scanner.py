"""
Metadata Scanner Module
Discovers tables, schemas, and profiles data sources for analytical context.
"""
import asyncio
import json
import logging
from typing import Dict, Any, List
import pandas as pd
from backend.agents.data_source.connection_manager import ConnectionManager
from backend.agents.data_source.profiler import DataProfiler

logger = logging.getLogger("tui")

class MetadataScanner:
    """
    Scans a data source to extract table lists, schemas, and detailed profiles.
    """

    def __init__(self, connection_manager: ConnectionManager):
        self.conn_mgr = connection_manager

    def scan_source(self, conn_id: str, deep_scan: bool = False) -> Dict[str, Any]:
        """
        Scans the source. Returns table list by default (shallow).
        If deep_scan=True, performs detailed profiling for all tables.
        """
        conn_info = self._get_conn_info(conn_id)
        conn_type = conn_info["type"]
        
        metadata = {
            "conn_id": conn_id,
            "type": conn_type,
            "tables": []
        }
        
        table_names = self._list_tables(conn_id, conn_type)
        
        for table in table_names:
            if deep_scan:
                table_meta = self.scan_table(conn_id, table)
            else:
                table_meta = {"table_name": table, "is_lazy": True}
            metadata["tables"].append(table_meta)
            
        return metadata

    def scan_table(self, conn_id: str, table_name: str) -> Dict[str, Any]:
        """Performs detailed profiling of a single table."""
        # 1. Fetch Sample Data - Sanitize table name by escaping existing double quotes
        safe_table_name = table_name.replace('"', '""')
        query = f'SELECT * FROM "{safe_table_name}" LIMIT 100'  # nosec B608
        df = self.conn_mgr.run_query(conn_id, query)
        
        # 2. Use DataProfiler for statistical summary
        profiler = DataProfiler(df)
        profile_data = profiler.profile()
        
        return {
            "table_name": table_name,
            "row_count_estimate": profile_data["overview"]["rows"],
            "columns": profile_data["columns"],
            "sample": profile_data["sample"]
        }

    async def async_scan_source(
        self,
        conn_id: str,
        deep_scan: bool = False,
        max_concurrent: int = 5,
    ) -> Dict[str, Any]:
        """scan_source의 비동기 버전. deep_scan=True 시 최대 max_concurrent개 테이블을 병렬 스캔.

        참고: 읽기 전용 SELECT 쿼리만 실행한다고 가정함. Semaphore로 동시 실행 수를 제한하여
        스레드 안전성을 확보하며, SQLite(WAL모드), PostgreSQL, MySQL, DuckDB 읽기에 적합함.
        """
        conn_info = self._get_conn_info(conn_id)
        conn_type = conn_info["type"]
        metadata: Dict[str, Any] = {"conn_id": conn_id, "type": conn_type, "tables": []}
        table_names = self._list_tables(conn_id, conn_type)

        if not deep_scan:
            metadata["tables"] = [{"table_name": t, "is_lazy": True} for t in table_names]
            return metadata

        loop = asyncio.get_running_loop()
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _scan_one(table: str) -> Dict[str, Any]:
            async with semaphore:
                return await loop.run_in_executor(None, self.scan_table, conn_id, table)

        tasks = [asyncio.create_task(_scan_one(t)) for t in table_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for table_name, result in zip(table_names, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to scan table '{table_name}': {result}")
                metadata["tables"].append({"table_name": table_name, "error": str(result)})
            else:
                metadata["tables"].append(result)

        return metadata

    async def async_scan_table(self, conn_id: str, table_name: str) -> Dict[str, Any]:
        """scan_table의 비동기 래퍼. run_in_executor로 blocking I/O를 비동기로 처리."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.scan_table, conn_id, table_name)

    def _get_conn_info(self, conn_id: str) -> Dict[str, Any]:
        with open(self.conn_mgr.registry_path, 'r', encoding='utf-8') as f:
            registry = json.load(f)
        return registry[conn_id]

    def _list_tables(self, conn_id: str, conn_type: str) -> List[str]:
        """Lists table names based on connection type."""
        logger.info(f"Listing tables for connection '{conn_id}' (type: {conn_type})")
        try:
            if conn_type == "sqlite":
                query = "SELECT name FROM sqlite_master WHERE type='table'"
                df = self.conn_mgr.run_query(conn_id, query)
                tables = df["name"].tolist()
            elif conn_type == "postgres":
                query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                df = self.conn_mgr.run_query(conn_id, query)
                tables = df["table_name"].tolist()
            elif conn_type == "duckdb":
                query = "SHOW TABLES"
                df = self.conn_mgr.run_query(conn_id, query)
                tables = df.iloc[:, 0].tolist()
            elif conn_type == "excel":
                return ["Sheet1"]
            else:
                logger.warning(f"Unsupported connection type for table listing: {conn_type}")
                return []

            logger.info(f"Found {len(tables)} tables for '{conn_id}': {tables[:10]}")
            return tables
        except Exception as e:
            logger.error(f"Failed to list tables for '{conn_id}' ({conn_type}): {e}", exc_info=True)
            raise


if __name__ == "__main__":
    import tempfile
    import os
    temp_json = os.path.join(tempfile.gettempdir(), "test_connections.json")
    mgr = ConnectionManager(temp_json)
    mgr.register_connection("test_db", "sqlite", {"path": ":memory:"})
    conn = mgr.get_connection("test_db")
    
    conn.execute("CREATE TABLE sales (id INT, product TEXT, amount REAL)")
    conn.execute("INSERT INTO sales VALUES (1, 'Apple', 10.5), (2, 'Banana', 5.0)")
    conn.commit()
    
    scanner = MetadataScanner(mgr)
    full_meta = scanner.scan_source("test_db")
    
    import pprint
    pprint.pprint(full_meta)
    
    os.remove(temp_json)
