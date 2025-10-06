#!/usr/bin/env python3
"""
Unit tests for log_query.py
"""

import pytest
import sqlite3
import tempfile
import os
import sys
from datetime import datetime
from click.testing import CliRunner

# Import the module under test
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import log_query


class TestTimestampParsing:
    """Test cases for parse_timestamp function"""
    
    def test_parse_unix_timestamp(self):
        """Test parsing UNIX timestamp as string"""
        result = log_query.parse_timestamp("1697395536")
        assert result == 1697395536
    
    def test_parse_unix_timestamp_integer(self):
        """Test parsing UNIX timestamp as integer string"""
        result = log_query.parse_timestamp("1697395536")
        assert isinstance(result, int)
        assert result > 0
    
    def test_parse_iso_format_basic(self):
        """Test parsing ISO format timestamp"""
        result = log_query.parse_timestamp("2023-10-15T14:45:36")
        expected = int(datetime(2023, 10, 15, 14, 45, 36).timestamp())
        assert result == expected
    
    def test_parse_iso_format_with_z(self):
        """Test parsing ISO format with Z suffix"""
        result = log_query.parse_timestamp("2023-10-15T14:45:36Z")
        expected = int(datetime(2023, 10, 15, 14, 45, 36).timestamp())
        assert result == expected
    
    def test_parse_iso_format_space_separated(self):
        """Test parsing ISO format with space instead of T"""
        result = log_query.parse_timestamp("2023-10-15 14:45:36")
        expected = int(datetime(2023, 10, 15, 14, 45, 36).timestamp())
        assert result == expected
    
    def test_parse_invalid_format(self):
        """Test parsing invalid timestamp format"""
        with pytest.raises(ValueError, match="Unable to parse timestamp"):
            log_query.parse_timestamp("invalid-timestamp")
    
    def test_parse_empty_string(self):
        """Test parsing empty string"""
        with pytest.raises(ValueError):
            log_query.parse_timestamp("")


class TestFilterExpressionParsing:
    """Test cases for parse_filter_expression function"""
    
    def test_parse_empty_filter(self):
        """Test parsing empty filter"""
        result = log_query.parse_filter_expression("")
        assert result == {"conditions": []}
    
    def test_parse_simple_string_filter(self):
        """Test parsing simple string filter"""
        result = log_query.parse_filter_expression("error")
        expected = {
            "conditions": [
                {"type": "general", "value": "error", "negated": False, "operator": None}
            ]
        }
        assert result == expected
    
    def test_parse_field_specific_filter(self):
        """Test parsing field-specific filter"""
        result = log_query.parse_filter_expression("component:reaper")
        expected = {
            "conditions": [
                {"type": "field", "field": "component", "value": "reaper", "negated": False, "operator": None}
            ]
        }
        assert result == expected
    
    def test_parse_and_filter(self):
        """Test parsing AND filter"""
        result = log_query.parse_filter_expression("error AND component:reaper")
        assert len(result["conditions"]) == 2
        assert result["conditions"][0]["value"] == "error"
        assert result["conditions"][0]["operator"] == "AND"
        assert result["conditions"][1]["field"] == "component"
        assert result["conditions"][1]["value"] == "reaper"
    
    def test_parse_or_filter(self):
        """Test parsing OR filter"""
        result = log_query.parse_filter_expression("error OR warning")
        assert len(result["conditions"]) == 2
        assert result["conditions"][0]["value"] == "error"
        assert result["conditions"][0]["operator"] == "OR"
        assert result["conditions"][1]["value"] == "warning"
    
    def test_parse_or_with_field_specific(self):
        """Test parsing OR filter with field-specific conditions"""
        result = log_query.parse_filter_expression("component:alchemist OR component:forklift")
        assert len(result["conditions"]) == 2
        assert result["conditions"][0]["type"] == "field"
        assert result["conditions"][0]["field"] == "component"
        assert result["conditions"][0]["value"] == "alchemist"
        assert result["conditions"][0]["operator"] == "OR"
        assert result["conditions"][1]["type"] == "field"
        assert result["conditions"][1]["field"] == "component"
        assert result["conditions"][1]["value"] == "forklift"
    
    def test_parse_mixed_or_conditions(self):
        """Test parsing OR filter with mixed field-specific and general conditions"""
        result = log_query.parse_filter_expression("component:alchemist OR error")
        assert len(result["conditions"]) == 2
        assert result["conditions"][0]["type"] == "field"
        assert result["conditions"][0]["field"] == "component"
        assert result["conditions"][0]["value"] == "alchemist"
        assert result["conditions"][0]["operator"] == "OR"
        assert result["conditions"][1]["type"] == "general"
        assert result["conditions"][1]["value"] == "error"
    
    def test_parse_or_with_pipes(self):
        """Test parsing OR filter using || operator"""
        result = log_query.parse_filter_expression("error || warning")
        assert len(result["conditions"]) == 2
        assert result["conditions"][0]["value"] == "error"
        assert result["conditions"][0]["operator"] == "OR"
        assert result["conditions"][1]["value"] == "warning"
    
    def test_parse_complex_and_or(self):
        """Test parsing complex filter with both AND and OR"""
        result = log_query.parse_filter_expression("error AND component:alchemist OR warning")
        assert len(result["conditions"]) == 3
        assert result["conditions"][0]["value"] == "error"
        assert result["conditions"][0]["operator"] == "AND"
        assert result["conditions"][1]["field"] == "component"
        assert result["conditions"][1]["value"] == "alchemist"
        assert result["conditions"][1]["operator"] == "OR"
        assert result["conditions"][2]["value"] == "warning"


class TestNotFunctionality:
    """Test cases for NOT functionality in filters"""
    
    def test_parse_not_function_pattern(self):
        """Test parsing not(value) pattern"""
        result = log_query.parse_filter_expression("not(error)")
        assert len(result["conditions"]) == 1
        assert result["conditions"][0]["value"] == "error"
        assert result["conditions"][0]["negated"] is True
        assert result["conditions"][0]["type"] == "general"
    
    def test_parse_not_keyword_pattern(self):
        """Test parsing NOT value pattern"""
        result = log_query.parse_filter_expression("NOT warning")
        assert len(result["conditions"]) == 1
        assert result["conditions"][0]["value"] == "warning"
        assert result["conditions"][0]["negated"] is True
        assert result["conditions"][0]["type"] == "general"
    
    def test_parse_exclamation_pattern(self):
        """Test parsing !value pattern"""
        result = log_query.parse_filter_expression("!debug")
        assert len(result["conditions"]) == 1
        assert result["conditions"][0]["value"] == "debug"
        assert result["conditions"][0]["negated"]  is True
        assert result["conditions"][0]["type"] == "general"
    
    def test_parse_not_field_specific(self):
        """Test parsing NOT with field-specific filter"""
        result = log_query.parse_filter_expression("NOT component:reaper")
        assert len(result["conditions"]) == 1
        assert result["conditions"][0]["type"] == "field"
        assert result["conditions"][0]["field"] == "component"
        assert result["conditions"][0]["value"] == "reaper"
        assert result["conditions"][0]["negated"]  is True
    
    def test_parse_not_function_field_specific(self):
        """Test parsing not() with field-specific filter"""
        result = log_query.parse_filter_expression("not(component:database)")
        assert len(result["conditions"]) == 1
        assert result["conditions"][0]["type"] == "field"
        assert result["conditions"][0]["field"] == "component"
        assert result["conditions"][0]["value"] == "database"
        assert result["conditions"][0]["negated"]  is True
    
    def test_parse_regular_condition_not_negated(self):
        """Test that regular conditions are not negated"""
        result = log_query.parse_filter_expression("error")
        assert len(result["conditions"]) == 1
        assert result["conditions"][0]["value"] == "error"
        assert result["conditions"][0]["negated"]  is False
    
    def test_parse_combined_not_and_regular(self):
        """Test combinations of NOT with regular conditions"""
        result = log_query.parse_filter_expression("error AND not(debug)")
        assert len(result["conditions"]) == 2
        assert result["conditions"][0]["value"] == "error"
        assert result["conditions"][0]["negated"]  is False
        assert result["conditions"][1]["value"] == "debug"
        assert result["conditions"][1]["negated"]  is True
    
    def test_parse_combined_not_or_regular(self):
        """Test NOT with OR operations"""
        result = log_query.parse_filter_expression("NOT warning OR error")
        assert len(result["conditions"]) == 2
        assert result["conditions"][0]["value"] == "warning"
        assert result["conditions"][0]["negated"]  is True
        assert result["conditions"][1]["value"] == "error"
        assert result["conditions"][1]["negated"]  is False
    
    def test_sql_generation_not_general(self):
        """Test SQL generation for general NOT conditions"""
        filters = {"conditions": [{"type": "general", "value": "error", "negated": True, "operator": None}]}
        query, params = log_query.build_sql_query(1000, 2000, filters, ["message"], None)
        
        assert "message NOT LIKE ?" in query
        assert "%error%" in params
    
    def test_sql_generation_not_field_specific(self):
        """Test SQL generation for field-specific NOT conditions"""
        filters = {"conditions": [{"type": "field", "field": "component", "value": "reaper", "negated": True, "operator": None}]}
        query, params = log_query.build_sql_query(1000, 2000, filters, ["message"], None)
        
        assert "component NOT LIKE ?" in query
        assert "%reaper%" in params
    
    def test_sql_generation_regular_vs_not(self):
        """Test SQL generation difference between regular and NOT conditions"""
        # Regular condition
        filters_regular = {"conditions": [{"type": "general", "value": "warning", "negated": False, "operator": None}]}
        query_regular, params_regular = log_query.build_sql_query(1000, 2000, filters_regular, ["message"], None)
        
        # NOT condition
        filters_not = {"conditions": [{"type": "general", "value": "warning", "negated": True, "operator": None}]}
        query_not, params_not = log_query.build_sql_query(1000, 2000, filters_not, ["message"], None)
        
        assert "message LIKE ?" in query_regular
        assert "NOT LIKE" not in query_regular
        assert "message NOT LIKE ?" in query_not
        assert "%warning%" in params_regular
        assert "%warning%" in params_not
    
    def test_sql_generation_not_timestamp_field(self):
        """Test SQL generation for NOT with timestamp field (should use != instead of NOT LIKE)"""
        filters = {"conditions": [{"type": "field", "field": "ts", "value": "1500", "negated": True, "operator": None}]}
        query, params = log_query.build_sql_query(1000, 2000, filters, ["message"], None)
        
        assert "ts != ?" in query
        assert 1500 in params
    
    def test_sql_generation_regular_timestamp_field(self):
        """Test SQL generation for regular timestamp field (should use = not !=)"""
        filters = {"conditions": [{"type": "field", "field": "ts", "value": "1500", "negated": False, "operator": None}]}
        query, params = log_query.build_sql_query(1000, 2000, filters, ["message"], None)
        
        assert "ts = ?" in query
        assert "!=" not in query
        assert 1500 in params


class TestSQLQueryBuilding:
    """Test cases for build_sql_query function"""
    
    def test_build_basic_query(self):
        """Test building basic SQL query"""
        query, params = log_query.build_sql_query(
            1000, 2000, {"conditions": []}, ["timestamp", "component", "message"]
        )
        
        assert "SELECT timestamp, component, message" in query
        assert "FROM logs" in query
        assert "WHERE ts BETWEEN ? AND ?" in query
        assert "ORDER BY ts ASC" in query
        assert params == [1000, 2000]
    
    def test_build_query_with_filters(self):
        """Test building query with filters"""
        filters = {
            "conditions": [
                {"type": "general", "value": "error", "negated": False, "operator": None}
            ]
        }
        query, params = log_query.build_sql_query(
            1000, 2000, filters, ["timestamp", "message"]
        )
        
        assert "message LIKE ?" in query
        assert params == [1000, 2000, "%error%"]
    
    def test_build_query_with_field_filter(self):
        """Test building query with field-specific filter"""
        filters = {
            "conditions": [
                {"type": "field", "field": "component", "value": "reaper", "negated": False, "operator": None}
            ]
        }
        query, params = log_query.build_sql_query(
            1000, 2000, filters, ["timestamp", "component"]
        )
        
        assert "component LIKE ?" in query
        assert params == [1000, 2000, "%reaper%"]
    
    def test_build_query_with_limit(self):
        """Test building query with limit"""
        query, params = log_query.build_sql_query(
            1000, 2000, {"conditions": []}, ["timestamp"], limit=10
        )
        
        assert "LIMIT 10" in query
    
    def test_build_query_with_or_conditions(self):
        """Test building SQL query with OR conditions"""
        filters = {
            "conditions": [
                {"type": "general", "value": "error", "negated": False, "operator": "OR"},
                {"type": "general", "value": "warning", "negated": False, "operator": None}
            ]
        }
        query, params = log_query.build_sql_query(
            1000, 2000, filters, ["timestamp", "message"]
        )
        
        assert "message LIKE ? OR message LIKE ?" in query
        assert params == [1000, 2000, "%error%", "%warning%"]
    
    def test_build_query_with_or_field_conditions(self):
        """Test building SQL query with OR field-specific conditions"""
        filters = {
            "conditions": [
                {"type": "field", "field": "component", "value": "alchemist", "negated": False, "operator": "OR"},
                {"type": "field", "field": "component", "value": "forklift", "negated": False, "operator": None}
            ]
        }
        query, params = log_query.build_sql_query(
            1000, 2000, filters, ["timestamp", "component", "message"]
        )
        
        assert "component LIKE ? OR component LIKE ?" in query
        assert params == [1000, 2000, "%alchemist%", "%forklift%"]
    
    def test_build_query_with_mixed_or_conditions(self):
        """Test building SQL query with mixed OR conditions (field + general)"""
        filters = {
            "conditions": [
                {"type": "field", "field": "component", "value": "alchemist", "negated": False, "operator": "OR"},
                {"type": "general", "value": "error", "negated": False, "operator": None}
            ]
        }
        query, params = log_query.build_sql_query(
            1000, 2000, filters, ["timestamp", "component", "message"]
        )
        
        assert "component LIKE ? OR message LIKE ?" in query
        assert params == [1000, 2000, "%alchemist%", "%error%"]
    
    def test_build_query_with_complex_and_or(self):
        """Test building SQL query with complex AND/OR conditions"""
        filters = {
            "conditions": [
                {"type": "general", "value": "error", "negated": False, "operator": "AND"},
                {"type": "field", "field": "component", "value": "alchemist", "negated": False, "operator": "OR"},
                {"type": "general", "value": "warning", "negated": False, "operator": None}
            ]
        }
        query, params = log_query.build_sql_query(
            1000, 2000, filters, ["timestamp", "component", "message"]
        )
        
        assert "message LIKE ? AND component LIKE ? OR message LIKE ?" in query
        assert params == [1000, 2000, "%error%", "%alchemist%", "%warning%"]


class TestOutputFormatting:
    """Test cases for format_output_line function"""
    
    def test_format_basic_output(self):
        """Test formatting basic output line"""
        row = {"timestamp": "2023-10-15T14:45:36Z", "component": "test", "message": "Test message"}
        fields = ["timestamp", "component", "message"]
        
        result = log_query.format_output_line(row, fields)
        assert result == "2023-10-15T14:45:36Z | test | Test message"
    
    def test_format_with_unix_timestamp(self):
        """Test formatting output with UNIX timestamp"""
        row = {"ts": 1697395536, "component": "test", "message": "Test message"}
        fields = ["ts", "component", "message"]
        
        result = log_query.format_output_line(row, fields)
        assert "1697395536" in result  # Should show raw integer timestamp
        assert "test" in result
        assert "Test message" in result
    
    def test_format_custom_fields(self):
        """Test formatting with custom field order"""
        row = {"timestamp": "2023-10-15T14:45:36Z", "component": "test", "message": "Test"}
        fields = ["component", "message"]
        
        result = log_query.format_output_line(row, fields)
        assert result == "test | Test"


class TestDatabaseOperations:
    """Test cases for database operations"""
    
    def test_get_available_fields_with_valid_db(self):
        """Test getting available fields from valid database"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            
            # Create test database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE logs (
                    id INTEGER PRIMARY KEY,
                    ts INTEGER,
                    timestamp VARCHAR(50),
                    component VARCHAR(255),
                    message TEXT
                )
            """)
            conn.commit()
            conn.close()
            
            fields = log_query.get_available_fields(db_path)
            assert "id" in fields
            assert "ts" in fields
            assert "timestamp" in fields
            assert "component" in fields
            assert "message" in fields
    
    def test_get_available_fields_invalid_db(self):
        """Test getting available fields from invalid database"""
        fields = log_query.get_available_fields("nonexistent.db")
        # Should return default fields when database doesn't exist
        assert "id" in fields
        assert "ts" in fields
        assert "timestamp" in fields
        assert "component" in fields
        assert "message" in fields


class TestCLIIntegration:
    """Test cases for CLI integration"""
    
    def setUp_test_database(self):
        """Helper method to set up test database"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create table
        cursor.execute("""
            CREATE TABLE logs (
                id INTEGER PRIMARY KEY,
                ts INTEGER NOT NULL,
                timestamp VARCHAR(50) NOT NULL,
                component VARCHAR(255) NOT NULL,
                message TEXT NOT NULL
            )
        """)
        
        # Insert test data
        test_data = [
            (1697395536, "2023-10-15T14:45:36Z", "test_component", "[info] Test message 1"),
            (1697395537, "2023-10-15T14:45:37Z", "test_component", "[error] Test error message"),
            (1697395538, "2023-10-15T14:45:38Z", "other_component", "[info] Other message"),
            (1697395539, "2023-10-15T14:45:39Z", "alchemist", "[warn] Connection warning"),
            (1697395540, "2023-10-15T14:45:40Z", "forklift", "[info] Processing data"),
            (1697395541, "2023-10-15T14:45:41Z", "test_component", "[warn] Warning message"),
        ]
        
        cursor.executemany(
            "INSERT INTO logs (ts, timestamp, component, message) VALUES (?, ?, ?, ?)",
            test_data
        )
        
        conn.commit()
        conn.close()
        
        return self.db_path
    
    def tearDown_test_database(self):
        """Helper method to clean up test database"""
        if hasattr(self, 'temp_dir'):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def test_cli_help(self):
        """Test CLI help output"""
        runner = CliRunner()
        result = runner.invoke(log_query.main, ['--help'])
        
        assert result.exit_code == 0
        assert "Query log entries from a logs.db database" in result.output
        assert "--database" in result.output
        assert "--range" in result.output
        assert "--filter" in result.output
    
    def test_cli_show_fields(self):
        """Test --show-fields option"""
        db_path = self.setUp_test_database()
        
        try:
            runner = CliRunner()
            result = runner.invoke(log_query.main, ['--database', db_path, '--show-fields'])
            
            assert result.exit_code == 0
            assert "Available fields:" in result.output
            assert "id" in result.output
            assert "timestamp" in result.output
        finally:
            self.tearDown_test_database()
    
    def test_cli_basic_query(self):
        """Test basic CLI query"""
        db_path = self.setUp_test_database()
        
        try:
            runner = CliRunner()
            result = runner.invoke(log_query.main, [
                '--database', db_path,
                '1697395537',  # UNIX timestamp
                '--range', '5'
            ])
            
            assert result.exit_code == 0
            assert "Found" in result.output
            assert "matching entries" in result.output
            assert "Test error message" in result.output
        finally:
            self.tearDown_test_database()
    
    def test_cli_with_filters(self):
        """Test CLI with filters"""
        db_path = self.setUp_test_database()
        
        try:
            runner = CliRunner()
            result = runner.invoke(log_query.main, [
                '--database', db_path,
                '1697395537',
                '--range', '5',
                '--filter', 'error'
            ])
            
            assert result.exit_code == 0
            assert "Test error message" in result.output
            # Should not contain info messages
            assert "Test message 1" not in result.output
        finally:
            self.tearDown_test_database()
    
    def test_cli_with_component_filter(self):
        """Test CLI with component filter"""
        db_path = self.setUp_test_database()
        
        try:
            runner = CliRunner()
            result = runner.invoke(log_query.main, [
                '--database', db_path,
                '1697395537',
                '--range', '5',
                '--filter', 'component:other_component'
            ])
            
            assert result.exit_code == 0
            assert "Other message" in result.output
            # Should not contain test_component messages
            assert "Test message 1" not in result.output
        finally:
            self.tearDown_test_database()
    
    def test_cli_with_custom_fields(self):
        """Test CLI with custom field selection"""
        db_path = self.setUp_test_database()
        
        try:
            runner = CliRunner()
            result = runner.invoke(log_query.main, [
                '--database', db_path,
                '1697395537',
                '--range', '5',
                '--fields', 'component,message'
            ])
            
            assert result.exit_code == 0
            assert "COMPONENT | MESSAGE" in result.output
            assert "test_component | [info] Test message 1" in result.output
        finally:
            self.tearDown_test_database()
    
    def test_cli_withtime_option(self):
        """Test CLI with --withtime option"""
        db_path = self.setUp_test_database()
        
        try:
            runner = CliRunner()
            result = runner.invoke(log_query.main, [
                '--database', db_path,
                '1697395537',
                '--range', '5',
                '--withtime'
            ])
            
            assert result.exit_code == 0
            assert "UNIX_TS" in result.output
            assert "1697395" in result.output  # Should show integer timestamp
        finally:
            self.tearDown_test_database()
    
    def test_cli_nonexistent_database(self):
        """Test CLI with nonexistent database"""
        runner = CliRunner()
        result = runner.invoke(log_query.main, [
            '--database', 'nonexistent.db',
            '1697395537'
        ])
        
        assert result.exit_code == 1
        assert "Database file 'nonexistent.db' not found" in result.output
    
    def test_cli_invalid_timestamp(self):
        """Test CLI with invalid timestamp"""
        db_path = self.setUp_test_database()
        
        try:
            runner = CliRunner()
            result = runner.invoke(log_query.main, [
                '--database', db_path,
                'invalid-timestamp'
            ])
            
            assert result.exit_code == 1
            assert "Unable to parse timestamp" in result.output
        finally:
            self.tearDown_test_database()
    
    def test_cli_no_timestamp(self):
        """Test CLI without timestamp argument"""
        runner = CliRunner()
        result = runner.invoke(log_query.main, ['--database', 'test.db'])
        
        assert result.exit_code == 1
        assert "TIMESTAMP argument is required" in result.output
    
    def test_cli_with_or_filters(self):
        """Test CLI with OR filter conditions"""
        db_path = self.setUp_test_database()
        
        try:
            runner = CliRunner()
            result = runner.invoke(log_query.main, [
                '--database', db_path,
                '1697395539',  # Center timestamp to catch both error and warn
                '--range', '10',
                '--filter', 'error OR warn'
            ])
            
            assert result.exit_code == 0
            # Should contain both error and warning messages
            assert "Test error message" in result.output
            assert "Connection warning" in result.output
            assert "Warning message" in result.output
            # Should not contain info messages without error/warn
            assert "Other message" not in result.output
        finally:
            self.tearDown_test_database()
    
    def test_cli_with_or_component_filters(self):
        """Test CLI with OR component filter conditions"""
        db_path = self.setUp_test_database()
        
        try:
            runner = CliRunner()
            result = runner.invoke(log_query.main, [
                '--database', db_path,
                '1697395540',  # Center around alchemist and forklift entries
                '--range', '10',
                '--filter', 'component:alchemist OR component:forklift'
            ])
            
            assert result.exit_code == 0
            # Should contain messages from both components
            assert "Connection warning" in result.output  # alchemist
            assert "Processing data" in result.output     # forklift
            # Should not contain test_component or other_component messages
            assert "Test error message" not in result.output
            assert "Other message" not in result.output
        finally:
            self.tearDown_test_database()
    
    def test_cli_with_mixed_or_filters(self):
        """Test CLI with mixed OR filter conditions (component + general)"""
        db_path = self.setUp_test_database()
        
        try:
            runner = CliRunner()
            result = runner.invoke(log_query.main, [
                '--database', db_path,
                '1697395539',
                '--range', '10',
                '--filter', 'component:forklift OR error'
            ])
            
            assert result.exit_code == 0
            # Should contain forklift messages AND any error messages
            assert "Processing data" in result.output     # forklift component
            assert "Test error message" in result.output  # error message
            # Should not contain other component info messages
            assert "Other message" not in result.output
        finally:
            self.tearDown_test_database()
    
    def test_cli_or_vs_and_comparison(self):
        """Test CLI comparing OR vs AND behavior"""
        db_path = self.setUp_test_database()
        
        try:
            runner = CliRunner()
            
            # Test AND - should be restrictive (component must be test_component AND message must contain error)
            and_result = runner.invoke(log_query.main, [
                '--database', db_path,
                '1697395537',
                '--range', '10',
                '--filter', 'component:test_component AND error'
            ])
            
            # Test OR - should be inclusive (either test_component OR any error message)
            or_result = runner.invoke(log_query.main, [
                '--database', db_path,
                '1697395537',
                '--range', '10',
                '--filter', 'component:test_component OR error'
            ])
            
            assert and_result.exit_code == 0
            assert or_result.exit_code == 0
            
            # AND should only contain test_component entries that ALSO have error
            assert "Test error message" in and_result.output  # test_component AND error
            assert "Test message 1" not in and_result.output  # test_component but no error
            assert "Warning message" not in and_result.output # test_component but no error
            
            # OR should contain ALL test_component entries OR any error entries
            assert "Test error message" in or_result.output   # matches both conditions
            assert "Test message 1" in or_result.output       # test_component
            assert "Warning message" in or_result.output      # test_component
        finally:
            self.tearDown_test_database()
    
    def test_cli_with_not_function_filter(self):
        """Test CLI with not() function filter"""
        db_path = self.setUp_test_database()
        
        try:
            runner = CliRunner()
            result = runner.invoke(log_query.main, [
                '--database', db_path,
                '1697395537',
                '--range', '5',
                '--filter', 'not(error)'
            ])
            
            assert result.exit_code == 0
            # Should NOT contain error messages
            assert "Test error message" not in result.output
            # Should contain other messages
            assert "Test message 1" in result.output
            assert "Other message" in result.output
        finally:
            self.tearDown_test_database()
    
    def test_cli_with_not_keyword_filter(self):
        """Test CLI with NOT keyword filter"""
        db_path = self.setUp_test_database()
        
        try:
            runner = CliRunner()
            result = runner.invoke(log_query.main, [
                '--database', db_path,
                '1697395537',
                '--range', '5',
                '--filter', 'NOT info'
            ])
            
            assert result.exit_code == 0
            # Should NOT contain info messages
            assert "Test message 1" not in result.output
            assert "Other message" not in result.output
            assert "Processing data" not in result.output
            # Should contain error and warning messages
            assert "Test error message" in result.output
            assert "Warning message" in result.output
        finally:
            self.tearDown_test_database()
    
    def test_cli_with_exclamation_filter(self):
        """Test CLI with ! filter"""
        db_path = self.setUp_test_database()
        
        try:
            runner = CliRunner()
            result = runner.invoke(log_query.main, [
                '--database', db_path,
                '1697395537',
                '--range', '5',
                '--filter', '!warn'
            ])
            
            assert result.exit_code == 0
            # Should NOT contain warning messages
            assert "Connection warning" not in result.output
            assert "Warning message" not in result.output
            # Should contain other messages
            assert "Test error message" in result.output
            assert "Test message 1" in result.output
        finally:
            self.tearDown_test_database()
    
    def test_cli_with_not_component_filter(self):
        """Test CLI with NOT component filter"""
        db_path = self.setUp_test_database()
        
        try:
            runner = CliRunner()
            result = runner.invoke(log_query.main, [
                '--database', db_path,
                '1697395537',
                '--range', '5',
                '--filter', 'NOT component:test_component'
            ])
            
            assert result.exit_code == 0
            # Should NOT contain test_component messages
            assert "Test message 1" not in result.output
            assert "Test error message" not in result.output
            assert "Warning message" not in result.output
            # Should contain other component messages
            assert "Other message" in result.output
        finally:
            self.tearDown_test_database()
    
    def test_cli_with_mixed_not_and_regular_filters(self):
        """Test CLI with mixed NOT and regular filters"""
        db_path = self.setUp_test_database()
        
        try:
            runner = CliRunner()
            result = runner.invoke(log_query.main, [
                '--database', db_path,
                '1697395537',
                '--range', '5',
                '--filter', 'component:test_component AND not(error)'
            ])
            
            assert result.exit_code == 0
            # Should contain test_component messages but NOT error messages
            assert "Test message 1" in result.output       # test_component, no error
            assert "Warning message" in result.output      # test_component, no error
            assert "Test error message" not in result.output  # test_component but has error
            # Should not contain non-test_component messages
            assert "Other message" not in result.output
        finally:
            self.tearDown_test_database()


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_empty_database_results(self):
        """Test query with no matching results"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "empty.db")
            
            # Create empty database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE logs (
                    id INTEGER PRIMARY KEY,
                    ts INTEGER,
                    timestamp VARCHAR(50),
                    component VARCHAR(255),
                    message TEXT
                )
            """)
            conn.commit()
            conn.close()
            
            runner = CliRunner()
            result = runner.invoke(log_query.main, [
                '--database', db_path,
                '1697395537',
                '--range', '5'
            ])
            
            assert result.exit_code == 0
            assert "No matching log entries found" in result.output


if __name__ == '__main__':
    pytest.main([__file__])