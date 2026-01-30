"""
Metadata Scanner Module
Discovers tables, schemas, and profiles data sources for analytical context.
"""
from typing import Dict, Any, List
import pandas as pd
from backend.agents.data_source.connection_manager import ConnectionManager
from backend.agents.data_source.profiler import DataProfiler

class MetadataScanner:
    """
    Scans a data source to extract table lists, schemas, and detailed profiles.
    """

    def __init__(self, connection_manager: ConnectionManager):
        self.conn_mgr = connection_manager

    def scan_source(self, conn_id: str) -> Dict[str, Any]:
        """Scans the entire source and returns a metadata tree."""
        conn_info = self._get_conn_info(conn_id)
        conn_type = conn_info["type"]
        
        metadata = {
            "conn_id": conn_id,
            "type": conn_type,
            "tables": []
        }
        
        table_names = self._list_tables(conn_id, conn_type)
        
        for table in table_names:
            table_meta = self.scan_table(conn_id, table)
            metadata["tables"].append(table_meta)
            
        return metadata

    def scan_table(self, conn_id: str, table_name: str) -> Dict[str, Any]:
        """Performs detailed profiling of a single table."""
        # 1. Fetch Sample Data
        query = f'SELECT * FROM "{table_name}" LIMIT 100'
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

    def _get_conn_info(self, conn_id: str) -> Dict[str, Any]:
        with open(self.conn_mgr.registry_path, 'r', encoding='utf-8') as f:
            registry = json.load(f)
        return registry[conn_id]

    def _list_tables(self, conn_id: str, conn_type: str) -> List[str]:
        """Lists table names based on connection type."""
        if conn_type == "sqlite":
            query = "SELECT name FROM sqlite_master WHERE type='table'"
            df = self.conn_mgr.run_query(conn_id, query)
            return df["name"].tolist()
        elif conn_type == "postgres":
            query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            df = self.conn_mgr.run_query(conn_id, query)
            return df["table_name"].tolist()
        elif conn_type == "duckdb":
            query = "SHOW TABLES"
            df = self.conn_mgr.run_query(conn_id, query)
            # SHOW TABLES returns a column 'name' or just one column
            return df.iloc[:, 0].tolist()
        elif conn_type == "excel":
            # For Excel, we assume the session (path) refers to a file with sheets
            # In a real impl, we'd list sheet names.
            return ["Sheet1"] 
        else:
            return []

import json # Required for Registry read in helper
if __name__ == "__main__":
    # Test with SQLite
    mgr = ConnectionManager("/tmp/test_connections.json")
    mgr.register_connection("test_db", "sqlite", {"path": ":memory:"})
    conn = mgr.get_connection("test_db")
    
    conn.execute("CREATE TABLE sales (id INT, product TEXT, amount REAL)")
    conn.execute("INSERT INTO sales VALUES (1, 'Apple', 10.5), (2, 'Banana', 5.0)")
    conn.commit()
    
    scanner = MetadataScanner(mgr)
    full_meta = scanner.scan_source("test_db")
    
    import pprint
    pprint.pprint(full_meta)
    
    os.remove("/tmp/test_connections.json")
