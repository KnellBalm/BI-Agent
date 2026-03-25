"""bi_agent_mcp.tools.files 단위 테스트."""
import sys
import pytest
import pandas as pd
import os
from pathlib import Path
from unittest.mock import patch, MagicMock


def _clear_files():
    from bi_agent_mcp.tools import files
    files._files.clear()


class TestConnectFile:
    def setup_method(self):
        _clear_files()

    def teardown_method(self):
        _clear_files()

    def test_connect_file_csv(self, tmp_path):
        csv_file = tmp_path / "sales.csv"
        csv_file.write_text("id,name,amount\n1,Alice,100\n2,Bob,200\n")

        from bi_agent_mcp.tools.files import connect_file
        result = connect_file(str(csv_file))

        assert "[ERROR]" not in result
        assert "file_" in result
        assert "sales.csv" in result
        assert "2" in result  # 행수

    def test_connect_file_unsupported_extension(self, tmp_path):
        txt_file = tmp_path / "data.txt"
        txt_file.write_text("hello")

        from bi_agent_mcp.tools.files import connect_file
        result = connect_file(str(txt_file))

        assert "[ERROR]" in result
        assert ".txt" in result

    def test_connect_file_not_found(self):
        from bi_agent_mcp.tools.files import connect_file
        result = connect_file("/nonexistent/path/data.csv")

        assert "[ERROR]" in result
        assert "찾을 수 없습니다" in result

    def test_connect_file_returns_file_id(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("col1,col2\n1,a\n2,b\n")

        from bi_agent_mcp.tools.files import connect_file
        result = connect_file(str(csv_file))

        assert "file_" in result

    def test_connect_file_shows_columns(self, tmp_path):
        csv_file = tmp_path / "wide.csv"
        cols = ",".join([f"col{i}" for i in range(15)])
        csv_file.write_text(cols + "\n" + ",".join(["1"] * 15) + "\n")

        from bi_agent_mcp.tools.files import connect_file
        result = connect_file(str(csv_file))

        assert "[ERROR]" not in result
        assert "15" in result


class TestListFiles:
    def setup_method(self):
        _clear_files()

    def teardown_method(self):
        _clear_files()

    def test_list_files_empty(self):
        from bi_agent_mcp.tools.files import list_files
        result = list_files()
        assert "없습니다" in result

    def test_list_files_with_loaded_file(self, tmp_path):
        csv_file = tmp_path / "report.csv"
        csv_file.write_text("a,b\n1,2\n3,4\n5,6\n")

        from bi_agent_mcp.tools.files import connect_file, list_files
        connect_file(str(csv_file))
        result = list_files()

        assert "report.csv" in result
        assert "|" in result
        assert "file_" in result


class TestQueryFile:
    def setup_method(self):
        _clear_files()

    def teardown_method(self):
        _clear_files()

    def _load_csv(self, tmp_path, filename="data.csv", content="id,value\n1,10\n2,20\n3,30\n"):
        csv_file = tmp_path / filename
        csv_file.write_text(content)
        from bi_agent_mcp.tools.files import connect_file
        result = connect_file(str(csv_file))
        # file_id 추출
        for token in result.split():
            if token.startswith("file_"):
                return token
        # 개행 포함된 경우 처리
        for line in result.splitlines():
            line = line.strip()
            if line.startswith("file_"):
                return line
        raise ValueError(f"file_id를 찾을 수 없음. connect_file 결과: {result!r}")

    def test_unknown_file_id_returns_error(self):
        from bi_agent_mcp.tools.files import query_file
        result = query_file("file_nonexistent", "SELECT * FROM df")
        assert "[ERROR]" in result

    def test_query_file_basic_select(self, tmp_path):
        pytest.importorskip("duckdb")
        file_id = self._load_csv(tmp_path)

        from bi_agent_mcp.tools.files import query_file
        result = query_file(file_id, "SELECT * FROM df")

        assert "[ERROR]" not in result
        assert "|" in result

    def test_query_file_rejects_insert(self, tmp_path):
        file_id = self._load_csv(tmp_path)

        from bi_agent_mcp.tools.files import query_file
        result = query_file(file_id, "INSERT INTO df VALUES (4, 40)")

        assert "[ERROR]" in result

    def test_query_file_rejects_drop(self, tmp_path):
        file_id = self._load_csv(tmp_path)

        from bi_agent_mcp.tools.files import query_file
        result = query_file(file_id, "DROP TABLE df")

        assert "[ERROR]" in result

    def test_query_file_with_where_clause(self, tmp_path):
        pytest.importorskip("duckdb")
        file_id = self._load_csv(tmp_path)

        from bi_agent_mcp.tools.files import query_file
        result = query_file(file_id, "SELECT * FROM df WHERE id = 1")

        assert "[ERROR]" not in result


class TestGetFileSchema:
    def setup_method(self):
        _clear_files()

    def teardown_method(self):
        _clear_files()

    def test_unknown_file_id_returns_error(self):
        from bi_agent_mcp.tools.files import get_file_schema
        result = get_file_schema("file_nonexistent")
        assert "[ERROR]" in result

    def test_get_file_schema_returns_columns(self, tmp_path):
        csv_file = tmp_path / "schema_test.csv"
        csv_file.write_text("name,age,score\nAlice,30,95.5\nBob,25,87.0\n")

        from bi_agent_mcp.tools.files import connect_file, get_file_schema
        result_conn = connect_file(str(csv_file))

        file_id = None
        for token in result_conn.split():
            if token.startswith("file_"):
                file_id = token
                break
        if file_id is None:
            for line in result_conn.splitlines():
                line = line.strip()
                if line.startswith("file_"):
                    file_id = line
                    break

        assert file_id is not None, f"file_id를 찾을 수 없음: {result_conn!r}"

        result = get_file_schema(file_id)

        assert "[ERROR]" not in result
        assert "name" in result
        assert "age" in result
        assert "score" in result
        assert "|" in result

    def test_schema_long_sample_truncated(self, tmp_path):
        """컬럼 샘플값이 50자 초과 시 '...'으로 잘린다 (line 156)."""
        csv_file = tmp_path / "longval.csv"
        long_val = "x" * 60
        csv_file.write_text(f"col\n{long_val}\n")

        from bi_agent_mcp.tools.files import connect_file, get_file_schema
        result_conn = connect_file(str(csv_file))
        file_id = None
        for token in result_conn.split():
            if token.startswith("file_"):
                file_id = token
                break
        if file_id is None:
            for line in result_conn.splitlines():
                line = line.strip()
                if line.startswith("file_"):
                    file_id = line
                    break
        assert file_id is not None
        result = get_file_schema(file_id)
        assert "..." in result


class TestConnectFileExtra:
    """connect_file Excel 경로 및 로드 실패 커버리지 보완."""

    def setup_method(self):
        from bi_agent_mcp.tools import files
        files._files.clear()

    def teardown_method(self):
        from bi_agent_mcp.tools import files
        files._files.clear()

    def test_excel_load_mocked(self, tmp_path):
        """Excel(xlsx) 로드 성공 — pandas.read_excel mock (lines 43-45)."""
        xlsx_file = tmp_path / "data.xlsx"
        xlsx_file.write_bytes(b"fake")

        mock_df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        with patch("pandas.read_excel", return_value=mock_df):
            from bi_agent_mcp.tools.files import connect_file
            result = connect_file(str(xlsx_file))

        assert "[ERROR]" not in result
        assert "data.xlsx" in result

    def test_excel_load_with_sheet_name(self, tmp_path):
        """sheet 파라미터가 있을 때 sheet_name으로 전달된다."""
        xlsx_file = tmp_path / "data.xlsx"
        xlsx_file.write_bytes(b"fake")

        mock_df = pd.DataFrame({"a": [1]})
        with patch("pandas.read_excel", return_value=mock_df) as mock_read:
            from bi_agent_mcp.tools.files import connect_file
            connect_file(str(xlsx_file), sheet="Sheet1")

        mock_read.assert_called_once_with(str(xlsx_file), sheet_name="Sheet1")

    def test_csv_load_failure_returns_error(self, tmp_path):
        """CSV 로드 시 예외 발생 → [ERROR] 반환 (lines 44-45)."""
        csv_file = tmp_path / "bad.csv"
        csv_file.write_text("a,b\n1,2")

        with patch("pandas.read_csv", side_effect=Exception("parse error")):
            from bi_agent_mcp.tools.files import connect_file
            result = connect_file(str(csv_file))

        assert result.startswith("[ERROR]")
        assert "파일 로드 실패" in result


class TestQueryFileExtra:
    """query_file 누락 브랜치 커버리지 보완 (lines 86-87, 93-128)."""

    def setup_method(self):
        from bi_agent_mcp.tools import files
        files._files.clear()

    def teardown_method(self):
        from bi_agent_mcp.tools import files
        files._files.clear()

    def _insert(self, file_id="file_t1"):
        import bi_agent_mcp.tools.files as m
        df = pd.DataFrame({"name": ["Alice", "Bob"], "val": [10, 20]})
        m._files[file_id] = {"path": "/tmp/d.csv", "df": df, "name": "d_csv"}
        return file_id

    def test_backtick_stripping(self):
        """SQL에 백틱 코드블록이 있으면 제거 후 실행 (lines 86-87)."""
        fid = self._insert()
        sql_with_backticks = "```sql\nSELECT * FROM df\n```"

        with patch("bi_agent_mcp.tools.files._validate_select", return_value=None):
            with patch("duckdb.connect") as mock_conn:
                mock_con = MagicMock()
                mock_conn.return_value = mock_con
                mock_con.execute.return_value.fetchdf.return_value = pd.DataFrame(
                    {"name": ["Alice"], "val": [10]}
                )
                from bi_agent_mcp.tools.files import query_file
                query_file(fid, sql_with_backticks)

        called_sql = mock_con.execute.call_args[0][0]
        assert "```" not in called_sql

    def test_duckdb_empty_result(self):
        """DuckDB 쿼리 결과가 비어있으면 '결과 없음' 반환 (line 116)."""
        fid = self._insert()

        with patch("bi_agent_mcp.tools.files._validate_select", return_value=None):
            with patch("duckdb.connect") as mock_conn:
                mock_con = MagicMock()
                mock_conn.return_value = mock_con
                mock_con.execute.return_value.fetchdf.return_value = pd.DataFrame()
                from bi_agent_mcp.tools.files import query_file
                result = query_file(fid, "SELECT * FROM df WHERE 1=0")

        assert "결과 없음" in result

    def test_duckdb_success_markdown(self):
        """DuckDB 쿼리 성공 시 마크다운 테이블 반환 (lines 119-131)."""
        fid = self._insert()

        with patch("bi_agent_mcp.tools.files._validate_select", return_value=None):
            with patch("duckdb.connect") as mock_conn:
                mock_con = MagicMock()
                mock_conn.return_value = mock_con
                mock_con.execute.return_value.fetchdf.return_value = pd.DataFrame(
                    {"name": ["Alice", "Bob"], "val": [10, 20]}
                )
                from bi_agent_mcp.tools.files import query_file
                result = query_file(fid, "SELECT * FROM df")

        assert "건 반환" in result
        assert "|" in result

    def test_duckdb_exception_returns_error(self):
        """DuckDB 실행 중 예외 → [ERROR] 반환 (lines 112-113)."""
        fid = self._insert()

        with patch("bi_agent_mcp.tools.files._validate_select", return_value=None):
            with patch("duckdb.connect", side_effect=RuntimeError("crash")):
                from bi_agent_mcp.tools.files import query_file
                result = query_file(fid, "SELECT * FROM df")

        assert result.startswith("[ERROR]")
        assert "쿼리 실행 실패" in result

    def test_duckdb_import_error_pandasql_fallback(self):
        """duckdb ImportError → pandasql 폴백 (lines 105-109)."""
        fid = self._insert()
        import bi_agent_mcp.tools.files as m
        df = m._files[fid]["df"]

        mock_ps = MagicMock()
        mock_ps.sqldf.return_value = pd.DataFrame({"name": ["Alice"], "val": [10]})

        saved = sys.modules.get("duckdb")
        sys.modules["duckdb"] = None
        try:
            with patch("bi_agent_mcp.tools.files._validate_select", return_value=None):
                with patch.dict(sys.modules, {"pandasql": mock_ps}):
                    from bi_agent_mcp.tools.files import query_file
                    result = query_file(fid, "SELECT * FROM df")
        finally:
            if saved is None:
                sys.modules.pop("duckdb", None)
            else:
                sys.modules["duckdb"] = saved

        assert "[ERROR]" not in result

    def test_duckdb_and_pandasql_both_missing(self):
        """duckdb, pandasql 모두 없으면 [ERROR] 반환 (lines 110-111)."""
        fid = self._insert()

        saved_duckdb = sys.modules.get("duckdb")
        saved_ps = sys.modules.get("pandasql")
        sys.modules["duckdb"] = None
        sys.modules["pandasql"] = None
        try:
            with patch("bi_agent_mcp.tools.files._validate_select", return_value=None):
                from bi_agent_mcp.tools.files import query_file
                result = query_file(fid, "SELECT * FROM df")
        finally:
            if saved_duckdb is None:
                sys.modules.pop("duckdb", None)
            else:
                sys.modules["duckdb"] = saved_duckdb
            if saved_ps is None:
                sys.modules.pop("pandasql", None)
            else:
                sys.modules["pandasql"] = saved_ps

        assert result.startswith("[ERROR]")

    def test_long_sql_preview_truncated(self):
        """SQL이 80자 초과 시 '...' 붙는다 (line 127)."""
        fid = self._insert()
        long_sql = "SELECT " + ", ".join([f"col{i}" for i in range(30)]) + " FROM df"

        with patch("bi_agent_mcp.tools.files._validate_select", return_value=None):
            with patch("duckdb.connect") as mock_conn:
                mock_con = MagicMock()
                mock_conn.return_value = mock_con
                mock_con.execute.return_value.fetchdf.return_value = pd.DataFrame(
                    {"name": ["Alice"]}
                )
                from bi_agent_mcp.tools.files import query_file
                result = query_file(fid, long_sql)

        assert "..." in result
