"""Tests for DuckDBService.

Following TDD approach - these tests define the expected DuckDB behavior.
"""

import pytest
import pandas as pd
from typing import Dict


class TestDuckDBServiceInitialization:
    """Test suite for DuckDBService initialization."""

    def test_service_creates_in_memory_database(self):
        """Test that DuckDBService creates in-memory database."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        service = DuckDBService()

        assert service is not None
        assert service.connection is not None

    def test_service_can_be_used_as_context_manager(self):
        """Test that DuckDBService can be used as context manager."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        with DuckDBService() as service:
            assert service is not None
            assert service.connection is not None

    def test_context_manager_closes_connection(self):
        """Test that context manager properly closes connection."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        service = DuckDBService()
        connection = service.connection

        service.close()

        # Connection should be closed
        assert service.connection is None or service._closed


class TestDuckDBServiceTableRegistration:
    """Test suite for registering pandas DataFrames as tables."""

    def test_register_single_dataframe(self):
        """Test registering a single DataFrame as a table."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        df = pd.DataFrame({
            "account_code": ["1000", "1100", "2000"],
            "account_name": ["Cash", "Accounts Receivable", "Accounts Payable"],
            "balance": [50000.00, 75000.00, -30000.00],
        })

        service = DuckDBService()
        service.register_dataframe("trial_balance", df)

        # Verify table exists by querying it
        result = service.execute_query("SELECT COUNT(*) as count FROM trial_balance")

        assert result.row_count == 1
        assert result.rows[0][0] == 3

    def test_register_multiple_dataframes(self):
        """Test registering multiple DataFrames as different tables."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        df1 = pd.DataFrame({
            "code": ["1000", "1100"],
            "amount": [50000.00, 75000.00],
        })

        df2 = pd.DataFrame({
            "code": ["2000", "2100"],
            "amount": [30000.00, 45000.00],
        })

        service = DuckDBService()
        service.register_dataframe("assets", df1)
        service.register_dataframe("liabilities", df2)

        # Verify both tables exist
        result1 = service.execute_query("SELECT COUNT(*) FROM assets")
        result2 = service.execute_query("SELECT COUNT(*) FROM liabilities")

        assert result1.rows[0][0] == 2
        assert result2.rows[0][0] == 2

    def test_register_dataframe_from_dict(self):
        """Test registering DataFrames from dictionary of worksheets."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        worksheets = {
            "TB-01": pd.DataFrame({"col1": [1, 2, 3]}),
            "TB-02": pd.DataFrame({"col2": [4, 5, 6]}),
        }

        service = DuckDBService()
        service.register_dataframes(worksheets)

        # Verify tables were created with sanitized names
        result = service.execute_query("SELECT COUNT(*) FROM \"TB-01\"")
        assert result.rows[0][0] == 3

    def test_sanitize_table_names(self):
        """Test that table names are sanitized to prevent SQL injection."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        df = pd.DataFrame({"col": [1]})

        service = DuckDBService()

        # Should handle names with special characters
        service.register_dataframe("table-with-dashes", df)
        service.register_dataframe("table with spaces", df)
        service.register_dataframe("table_with_underscores", df)

        # All should work without errors
        result1 = service.execute_query("SELECT COUNT(*) FROM \"table-with-dashes\"")
        assert result1.rows[0][0] == 1

    def test_replace_existing_table(self):
        """Test that registering same table name replaces previous table."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        df1 = pd.DataFrame({"col": [1, 2, 3]})
        df2 = pd.DataFrame({"col": [4, 5]})

        service = DuckDBService()
        service.register_dataframe("test_table", df1)

        # Verify first table has 3 rows
        result1 = service.execute_query("SELECT COUNT(*) FROM test_table")
        assert result1.rows[0][0] == 3

        # Replace with second table
        service.register_dataframe("test_table", df2)

        # Verify table now has 2 rows
        result2 = service.execute_query("SELECT COUNT(*) FROM test_table")
        assert result2.rows[0][0] == 2


class TestDuckDBServiceQueryExecution:
    """Test suite for executing SQL queries."""

    def test_execute_simple_select_query(self):
        """Test executing a simple SELECT query."""
        from genreport.core.parsing.duckdb_service import DuckDBService
        from genreport.core.parsing.parsing_models import QueryResult

        df = pd.DataFrame({
            "account_code": ["1000", "1100"],
            "balance": [50000.00, 75000.00],
        })

        service = DuckDBService()
        service.register_dataframe("accounts", df)

        result = service.execute_query("SELECT * FROM accounts")

        assert isinstance(result, QueryResult)
        assert result.row_count == 2
        assert result.columns == ["account_code", "balance"]
        assert result.rows[0][0] == "1000"
        assert result.rows[0][1] == 50000.00

    def test_execute_query_with_where_clause(self):
        """Test executing query with WHERE clause."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        df = pd.DataFrame({
            "account_code": ["1000", "1100", "2000"],
            "balance": [50000.00, 75000.00, -30000.00],
        })

        service = DuckDBService()
        service.register_dataframe("accounts", df)

        result = service.execute_query(
            "SELECT * FROM accounts WHERE balance > 0"
        )

        assert result.row_count == 2
        assert all(row[1] > 0 for row in result.rows)

    def test_execute_aggregate_query(self):
        """Test executing aggregate query (SUM, COUNT, AVG)."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        df = pd.DataFrame({
            "category": ["Asset", "Asset", "Liability"],
            "balance": [50000.00, 75000.00, 30000.00],
        })

        service = DuckDBService()
        service.register_dataframe("accounts", df)

        result = service.execute_query(
            "SELECT category, SUM(balance) as total FROM accounts GROUP BY category"
        )

        assert result.row_count == 2
        assert result.columns == ["category", "total"]

    def test_execute_join_query(self):
        """Test executing JOIN query across multiple tables."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        df1 = pd.DataFrame({
            "code": ["1000", "1100"],
            "name": ["Cash", "AR"],
        })

        df2 = pd.DataFrame({
            "code": ["1000", "1100"],
            "balance": [50000.00, 75000.00],
        })

        service = DuckDBService()
        service.register_dataframe("account_names", df1)
        service.register_dataframe("account_balances", df2)

        result = service.execute_query("""
            SELECT n.name, b.balance
            FROM account_names n
            JOIN account_balances b ON n.code = b.code
        """)

        assert result.row_count == 2
        assert result.columns == ["name", "balance"]

    def test_query_returns_execution_time(self):
        """Test that query result includes execution time."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        df = pd.DataFrame({"col": [1, 2, 3]})

        service = DuckDBService()
        service.register_dataframe("test", df)

        result = service.execute_query("SELECT * FROM test")

        assert result.execution_time_ms is not None
        assert result.execution_time_ms >= 0

    def test_query_includes_query_text(self):
        """Test that query result includes the query text for debugging."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        df = pd.DataFrame({"col": [1]})

        service = DuckDBService()
        service.register_dataframe("test", df)

        query = "SELECT * FROM test"
        result = service.execute_query(query)

        assert result.query == query

    def test_query_empty_result_set(self):
        """Test query that returns no rows."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        df = pd.DataFrame({
            "amount": [100, 200, 300],
        })

        service = DuckDBService()
        service.register_dataframe("test", df)

        result = service.execute_query("SELECT * FROM test WHERE amount > 1000")

        assert result.row_count == 0
        assert result.rows == []


class TestDuckDBServiceSQLInjectionPrevention:
    """Test suite for SQL injection prevention."""

    def test_reject_drop_table_in_query(self):
        """Test that DROP TABLE statements are rejected."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        df = pd.DataFrame({"col": [1]})

        service = DuckDBService()
        service.register_dataframe("test", df)

        # Should raise error for DROP statement
        with pytest.raises(ValueError, match="(?i)not allowed|forbidden|drop"):
            service.execute_query("DROP TABLE test")

    def test_reject_delete_in_query(self):
        """Test that DELETE statements are rejected."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        df = pd.DataFrame({"col": [1]})

        service = DuckDBService()
        service.register_dataframe("test", df)

        with pytest.raises(ValueError, match="(?i)not allowed|forbidden|delete"):
            service.execute_query("DELETE FROM test")

    def test_reject_update_in_query(self):
        """Test that UPDATE statements are rejected."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        df = pd.DataFrame({"col": [1]})

        service = DuckDBService()
        service.register_dataframe("test", df)

        with pytest.raises(ValueError, match="(?i)not allowed|forbidden|update"):
            service.execute_query("UPDATE test SET col = 2")

    def test_reject_insert_in_query(self):
        """Test that INSERT statements are rejected."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        df = pd.DataFrame({"col": [1]})

        service = DuckDBService()
        service.register_dataframe("test", df)

        with pytest.raises(ValueError, match="(?i)not allowed|forbidden|insert"):
            service.execute_query("INSERT INTO test VALUES (2)")

    def test_allow_select_only(self):
        """Test that only SELECT statements are allowed."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        df = pd.DataFrame({"col": [1]})

        service = DuckDBService()
        service.register_dataframe("test", df)

        # These should all work
        service.execute_query("SELECT * FROM test")
        service.execute_query("  SELECT * FROM test  ")  # With whitespace
        service.execute_query("SELECT COUNT(*) FROM test")

    def test_sanitize_table_name_prevents_injection(self):
        """Test that table name sanitization prevents SQL injection."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        df = pd.DataFrame({"col": [1]})

        service = DuckDBService()

        # Should handle malicious table names safely
        # These should not execute SQL injection
        service.register_dataframe("test; DROP TABLE users--", df)
        service.register_dataframe("test' OR '1'='1", df)


class TestDuckDBServiceErrorHandling:
    """Test suite for error handling."""

    def test_invalid_sql_syntax_raises_error(self):
        """Test that invalid SQL syntax raises appropriate error."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        df = pd.DataFrame({"col": [1]})

        service = DuckDBService()
        service.register_dataframe("test", df)

        with pytest.raises(Exception):  # Should raise some SQL error
            service.execute_query("SELECT * FORM test")  # Typo: FORM instead of FROM

    def test_query_nonexistent_table_raises_error(self):
        """Test that querying non-existent table raises error."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        service = DuckDBService()

        with pytest.raises(Exception):
            service.execute_query("SELECT * FROM nonexistent_table")

    def test_register_empty_dataframe(self):
        """Test registering empty DataFrame with columns but no rows."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        # Create DataFrame with columns but no rows (realistic scenario)
        df = pd.DataFrame(columns=["account_code", "balance"])

        service = DuckDBService()
        service.register_dataframe("empty", df)

        # Should handle empty table gracefully
        result = service.execute_query("SELECT COUNT(*) FROM empty")
        assert result.rows[0][0] == 0


class TestDuckDBServiceIntegration:
    """Integration tests for DuckDBService with real-world scenarios."""

    def test_analyze_trial_balance(self):
        """Test analyzing trial balance data."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        # Realistic trial balance data
        tb_data = pd.DataFrame({
            "account_code": ["1000", "1100", "1500", "2000", "2100", "3000"],
            "account_name": ["Cash", "Accounts Receivable", "Inventory",
                           "Accounts Payable", "Notes Payable", "Revenue"],
            "debit": [50000.00, 75000.00, 30000.00, 0.00, 0.00, 0.00],
            "credit": [0.00, 0.00, 0.00, 30000.00, 45000.00, 150000.00],
        })

        service = DuckDBService()
        service.register_dataframe("trial_balance", tb_data)

        # Query 1: Calculate total debits
        result1 = service.execute_query(
            "SELECT SUM(debit) as total_debit FROM trial_balance"
        )
        assert result1.rows[0][0] == 155000.00

        # Query 2: Calculate total credits
        result2 = service.execute_query(
            "SELECT SUM(credit) as total_credit FROM trial_balance"
        )
        assert result2.rows[0][0] == 225000.00

        # Query 3: Find accounts with balances
        result3 = service.execute_query("""
            SELECT account_name, (debit - credit) as balance
            FROM trial_balance
            WHERE (debit - credit) != 0
            ORDER BY balance DESC
        """)
        assert result3.row_count == 6

    def test_join_multiple_worksheets(self):
        """Test joining data from multiple worksheets."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        # Summary sheet
        summary = pd.DataFrame({
            "account": ["1000", "2000"],
            "total": [125000.00, 75000.00],
        })

        # Detail sheet
        details = pd.DataFrame({
            "account": ["1000", "1000", "2000"],
            "transaction_id": ["T1", "T2", "T3"],
            "amount": [50000.00, 75000.00, 75000.00],
        })

        service = DuckDBService()
        service.register_dataframe("summary", summary)
        service.register_dataframe("details", details)

        # Reconcile summary with details
        result = service.execute_query("""
            SELECT
                s.account,
                s.total as summary_total,
                SUM(d.amount) as detail_total,
                (s.total - SUM(d.amount)) as difference
            FROM summary s
            LEFT JOIN details d ON s.account = d.account
            GROUP BY s.account, s.total
        """)

        assert result.row_count == 2
        # Should match perfectly (difference = 0)
        assert all(row[3] == 0 for row in result.rows)

    def test_context_manager_cleanup(self):
        """Test that context manager properly cleans up resources."""
        from genreport.core.parsing.duckdb_service import DuckDBService

        df = pd.DataFrame({"col": [1, 2, 3]})

        with DuckDBService() as service:
            service.register_dataframe("test", df)
            result = service.execute_query("SELECT * FROM test")
            assert result.row_count == 3

        # After context manager exits, connection should be closed
        # Creating new service should work fine
        with DuckDBService() as service2:
            service2.register_dataframe("test", df)
            result2 = service2.execute_query("SELECT * FROM test")
            assert result2.row_count == 3
