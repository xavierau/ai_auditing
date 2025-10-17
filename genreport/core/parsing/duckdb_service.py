"""DuckDB service for SQL querying over parsed Excel data.

This module provides the DuckDBService class for executing analytical SQL
queries on pandas DataFrames using DuckDB's in-memory database. It includes
SQL injection prevention and secure query execution.

Architecture:
- In-memory DuckDB database (no persistence)
- Zero-copy integration with pandas DataFrames
- Read-only queries (SELECT only)
- Table name sanitization to prevent SQL injection
- Context manager support for resource cleanup

Example:
    ```python
    from genreport.core.parsing.duckdb_service import DuckDBService
    import pandas as pd

    # Create service
    with DuckDBService() as service:
        # Register DataFrames
        df = pd.DataFrame({
            "account": ["1000", "1100"],
            "balance": [50000, 75000]
        })
        service.register_dataframe("trial_balance", df)

        # Execute query
        result = service.execute_query('''
            SELECT account, balance
            FROM trial_balance
            WHERE balance > 60000
        ''')

        print(f"Found {result.row_count} rows")
        for row in result.rows:
            print(row)
    ```
"""

import re
import time
from typing import Dict, Optional
import logging

import duckdb
import pandas as pd

from genreport.core.parsing.parsing_models import QueryResult

logger = logging.getLogger(__name__)


class DuckDBService:
    """Service for executing SQL queries on pandas DataFrames using DuckDB.

    This service provides a secure, read-only SQL interface for querying
    Excel data loaded into pandas DataFrames. It uses DuckDB's in-memory
    database for high-performance analytical queries.

    Security Features:
    - Read-only queries (only SELECT allowed)
    - SQL injection prevention via query validation
    - Table name sanitization
    - No data persistence (in-memory only)

    Attributes:
        connection: DuckDB database connection

    Example:
        ```python
        service = DuckDBService()
        service.register_dataframe("accounts", df)
        result = service.execute_query("SELECT * FROM accounts")
        service.close()
        ```
    """

    # Forbidden SQL keywords (mutations not allowed)
    FORBIDDEN_KEYWORDS = {
        "DROP", "DELETE", "UPDATE", "INSERT", "ALTER",
        "CREATE", "TRUNCATE", "REPLACE", "MERGE"
    }

    def __init__(self):
        """Initialize DuckDB service with in-memory database."""
        self.connection = duckdb.connect(":memory:")
        self._closed = False

        logger.info("DuckDBService initialized with in-memory database")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.close()
        return False

    def close(self):
        """Close database connection and cleanup resources."""
        if not self._closed and self.connection:
            self.connection.close()
            self._closed = True
            self.connection = None
            logger.info("DuckDBService connection closed")

    def _sanitize_table_name(self, table_name: str) -> str:
        """Sanitize table name to prevent SQL injection.

        This removes dangerous characters and returns a clean table name.
        For registration with DuckDB, the name should NOT have quotes.

        Args:
            table_name: Raw table name

        Returns:
            Sanitized table name (without quotes)

        Example:
            ```python
            name = service._sanitize_table_name("TB-01")
            # Returns: 'TB-01'
            ```
        """
        # Remove any existing quotes and dangerous characters
        clean_name = table_name.strip().replace('"', '').replace("'", '')

        # Remove SQL injection attempts
        clean_name = clean_name.replace(';', '').replace('--', '')

        return clean_name

    def _validate_query(self, query: str) -> None:
        """Validate query to prevent SQL injection and mutations.

        This checks that the query is a read-only SELECT statement
        and doesn't contain forbidden keywords.

        Args:
            query: SQL query to validate

        Raises:
            ValueError: If query contains forbidden operations

        Example:
            ```python
            service._validate_query("SELECT * FROM table")  # OK
            service._validate_query("DROP TABLE table")  # Raises ValueError
            ```
        """
        # Remove comments and normalize whitespace
        clean_query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
        clean_query = re.sub(r'/\*.*?\*/', '', clean_query, flags=re.DOTALL)
        clean_query = clean_query.strip().upper()

        # Must start with SELECT
        if not clean_query.startswith("SELECT"):
            raise ValueError(
                "Only SELECT queries are allowed. "
                "Mutations (INSERT, UPDATE, DELETE, DROP) are forbidden."
            )

        # Check for forbidden keywords
        for keyword in self.FORBIDDEN_KEYWORDS:
            # Use word boundaries to avoid false positives
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, clean_query):
                raise ValueError(
                    f"Query contains forbidden keyword '{keyword}'. "
                    f"Only read-only SELECT queries are allowed."
                )

    def register_dataframe(self, table_name: str, df: pd.DataFrame) -> None:
        """Register a pandas DataFrame as a DuckDB table.

        This creates or replaces a table in DuckDB using zero-copy
        integration with pandas. The DataFrame is not modified.

        Args:
            table_name: Name for the table in DuckDB
            df: pandas DataFrame to register

        Example:
            ```python
            df = pd.DataFrame({"col": [1, 2, 3]})
            service.register_dataframe("my_table", df)
            ```
        """
        if self._closed:
            raise RuntimeError("Cannot register dataframe on closed connection")

        # Sanitize table name
        safe_name = self._sanitize_table_name(table_name)

        # Register DataFrame with DuckDB (zero-copy view)
        self.connection.register(safe_name, df)

        logger.debug(
            f"Registered DataFrame as table {safe_name} "
            f"({len(df)} rows, {len(df.columns)} columns)"
        )

    def register_dataframes(self, dataframes: Dict[str, pd.DataFrame]) -> None:
        """Register multiple pandas DataFrames as tables.

        Convenience method to register multiple DataFrames at once,
        typically used with parsed Excel worksheets.

        Args:
            dataframes: Dictionary mapping table names to DataFrames

        Example:
            ```python
            worksheets = {
                "TB-01": df1,
                "TB-02": df2,
            }
            service.register_dataframes(worksheets)
            ```
        """
        for table_name, df in dataframes.items():
            self.register_dataframe(table_name, df)

        logger.info(f"Registered {len(dataframes)} DataFrames as tables")

    def execute_query(self, query: str) -> QueryResult:
        """Execute a SQL query and return results.

        This executes a read-only SELECT query on the registered tables
        and returns the results along with execution time.

        Args:
            query: SQL SELECT query to execute

        Returns:
            QueryResult with columns, rows, and execution time

        Raises:
            ValueError: If query contains forbidden operations
            RuntimeError: If connection is closed
            Exception: If query execution fails

        Example:
            ```python
            result = service.execute_query('''
                SELECT account, SUM(balance) as total
                FROM trial_balance
                GROUP BY account
            ''')

            for row in result.rows:
                print(f"{row[0]}: {row[1]}")
            ```
        """
        if self._closed:
            raise RuntimeError("Cannot execute query on closed connection")

        # Validate query for security
        self._validate_query(query)

        # Execute query and measure time
        start_time = time.time()

        try:
            # Execute query
            cursor = self.connection.execute(query)

            # Fetch results
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000

            logger.debug(
                f"Query executed successfully: {len(rows)} rows in {execution_time_ms:.2f}ms"
            )

            return QueryResult(
                columns=columns,
                rows=rows,
                row_count=len(rows),
                query=query,
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.debug(f"Failed query: {query}")
            raise
