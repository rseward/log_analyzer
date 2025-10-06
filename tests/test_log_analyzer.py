#!/usr/bin/env python3
"""
Unit tests for log_analyzer.py
"""

import pytest
import sqlite3
import tempfile
import os
import shutil
from datetime import datetime, date

# Import the module under test
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import log_analyzer


class TestExtractComponentName:
    """Test cases for extract_component_name function"""
    
    def test_extract_with_prefix(self):
        """Test extracting component name with number prefix"""
        assert log_analyzer.extract_component_name("01 - reaper.log") == "reaper"
        assert log_analyzer.extract_component_name("02 - alchemist.log") == "alchemist"
        assert log_analyzer.extract_component_name("10 - service_name.log") == "service_name"
    
    def test_extract_without_prefix(self):
        """Test extracting component name without prefix"""
        assert log_analyzer.extract_component_name("simple_service.log") == "simple_service"
        assert log_analyzer.extract_component_name("component.log") == "component"
    
    def test_extract_with_spaces_in_prefix(self):
        """Test extracting with various spacing in prefix"""
        assert log_analyzer.extract_component_name("1 - service.log") == "service"
        assert log_analyzer.extract_component_name("01-service.log") == "service"
        assert log_analyzer.extract_component_name("1  -  service.log") == "service"
    
    def test_extract_with_path(self):
        """Test extracting component name from full path"""
        assert log_analyzer.extract_component_name("/path/to/01 - reaper.log") == "reaper"
        assert log_analyzer.extract_component_name("./tests/fixtures/02 - service.log") == "service"


class TestParseTimeToUnixTimestamp:
    """Test cases for parse_time_to_unix_timestamp function"""
    
    def test_parse_basic_timestamp(self):
        """Test parsing basic timestamp format"""
        test_date = date(2023, 10, 15)
        result = log_analyzer.parse_time_to_unix_timestamp("14:45:36.507", test_date)
        
        # Verify the result is a valid unix timestamp
        assert isinstance(result, int)
        assert result > 0
        
        # Convert back to verify (note: microseconds are lost when converting to int timestamp)
        dt = datetime.fromtimestamp(result)
        assert dt.hour == 14
        assert dt.minute == 45
        assert dt.second == 36
        # Note: microseconds are lost when converting to integer timestamp
    
    def test_parse_midnight(self):
        """Test parsing midnight timestamp"""
        test_date = date(2023, 10, 15)
        result = log_analyzer.parse_time_to_unix_timestamp("00:00:00.000", test_date)
        
        dt = datetime.fromtimestamp(result)
        assert dt.hour == 0
        assert dt.minute == 0
        assert dt.second == 0
        assert dt.microsecond == 0
    
    def test_parse_end_of_day(self):
        """Test parsing end of day timestamp"""
        test_date = date(2023, 10, 15)
        result = log_analyzer.parse_time_to_unix_timestamp("23:59:59.999", test_date)
        
        dt = datetime.fromtimestamp(result)
        assert dt.hour == 23
        assert dt.minute == 59
        assert dt.second == 59
        # Note: microseconds are lost when converting to integer timestamp


class TestSetupDatabase:
    """Test cases for setup_database function"""
    
    def test_setup_database_creates_file(self):
        """Test that database file is created"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            
            conn = log_analyzer.setup_database(db_path)
            
            assert os.path.exists(db_path)
            assert isinstance(conn, sqlite3.Connection)
            conn.close()
    
    def test_setup_database_creates_table(self):
        """Test that logs table is created with correct schema"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            
            conn = log_analyzer.setup_database(db_path)
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='logs'")
            result = cursor.fetchone()
            assert result is not None
            
            # Check table schema
            cursor.execute("PRAGMA table_info(logs)")
            columns = cursor.fetchall()
            
            column_names = [col[1] for col in columns]
            assert "id" in column_names
            assert "ts" in column_names
            assert "timestamp" in column_names
            assert "component" in column_names
            assert "message" in column_names
            
            conn.close()
    
    def test_setup_database_creates_indexes(self):
        """Test that indexes are created"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            
            conn = log_analyzer.setup_database(db_path)
            cursor = conn.cursor()
            
            # Check if indexes exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [row[0] for row in cursor.fetchall()]
            
            # SQLite creates automatic indexes, but we should have our custom ones
            index_names = [idx for idx in indexes if idx.startswith('idx_logs_')]
            assert len(index_names) >= 3  # ts, timestamp, and component indexes
            
            conn.close()
    
    def test_setup_database_migration(self):
        """Test that database migration works for existing databases without timestamp column"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "migration_test.db")
            
            # Create old schema database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create old table without timestamp column
            cursor.execute('''
                CREATE TABLE logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts INTEGER NOT NULL,
                    component VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL
                )
            ''')
            
            # Insert test data with old schema
            cursor.execute('INSERT INTO logs (ts, component, message) VALUES (?, ?, ?)',
                          (1697395536, 'old_component', 'Old test message'))
            conn.commit()
            conn.close()
            
            # Verify old schema
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(logs)")
            old_columns = [col[1] for col in cursor.fetchall()]
            assert 'timestamp' not in old_columns
            conn.close()
            
            # Run migration via setup_database
            conn = log_analyzer.setup_database(db_path)
            cursor = conn.cursor()
            
            # Verify new schema has timestamp column
            cursor.execute("PRAGMA table_info(logs)")
            new_columns = [col[1] for col in cursor.fetchall()]
            assert 'timestamp' in new_columns
            
            # Verify old data was migrated with timestamp populated in ISO format
            cursor.execute('SELECT ts, timestamp, component, message FROM logs')
            result = cursor.fetchone()
            assert result[0] == 1697395536  # ts
            # Verify timestamp is in ISO format
            expected_iso = datetime.fromtimestamp(1697395536).isoformat() + 'Z'
            assert result[1] == expected_iso  # timestamp should be ISO format
            assert result[2] == 'old_component'
            assert result[3] == 'Old test message'
            
            conn.close()


class TestDiscoverLogFiles:
    """Test cases for discover_log_files function"""
    
    def test_discover_log_files(self):
        """Test discovering log files in fixtures directory"""
        fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
        log_files = log_analyzer.discover_log_files(fixtures_dir)
        
        assert len(log_files) >= 2  # We created at least 2 test files
        
        # Check that all returned files end with .log
        for log_file in log_files:
            assert log_file.endswith(".log")
            assert os.path.exists(log_file)
    
    def test_discover_no_log_files(self):
        """Test behavior when no log files are found"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_files = log_analyzer.discover_log_files(temp_dir)
            assert log_files == []


class TestProcessLogFile:
    """Test cases for process_log_file function"""
    
    def setUp_database(self):
        """Helper method to set up test database"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.conn = log_analyzer.setup_database(self.db_path)
        self.cursor = self.conn.cursor()
    
    def tearDown_database(self):
        """Helper method to clean up test database"""
        if hasattr(self, 'conn'):
            self.conn.close()
        if hasattr(self, 'temp_dir'):
            shutil.rmtree(self.temp_dir)
    
    def test_process_simple_log_file(self):
        """Test processing a simple log file"""
        self.setUp_database()
        
        try:
            fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
            log_file = os.path.join(fixtures_dir, "simple_service.log")
            
            test_date = date(2023, 10, 15)
            entries_count = log_analyzer.process_log_file(
                log_file, "simple_service", test_date, self.cursor
            )
            
            assert entries_count > 0
            
            # Check database entries
            self.cursor.execute("SELECT COUNT(*) FROM logs WHERE component = ?", ("simple_service",))
            db_count = self.cursor.fetchone()[0]
            assert db_count == entries_count
            
            # Check that timestamps and messages are properly stored
            self.cursor.execute("SELECT ts, timestamp, message FROM logs WHERE component = ? ORDER BY ts", 
                               ("simple_service",))
            results = self.cursor.fetchall()
            assert len(results) > 0
            
            # Verify timestamp is valid unix timestamp and string timestamp is ISO format
            for ts, timestamp_str, message in results:
                assert isinstance(ts, int)
                assert ts > 0
                # Verify timestamp_str is in ISO format
                expected_iso = datetime.fromtimestamp(ts).isoformat() + 'Z'
                assert timestamp_str == expected_iso
                assert len(message) > 0
        
        finally:
            self.tearDown_database()
    
    def test_process_multiline_log_entries(self):
        """Test processing log file with multi-line entries"""
        self.setUp_database()
        
        try:
            fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
            log_file = os.path.join(fixtures_dir, "01 - test_component.log")
            
            test_date = date(2023, 10, 15)
            entries_count = log_analyzer.process_log_file(
                log_file, "test_component", test_date, self.cursor
            )
            
            assert entries_count > 0
            
            # Check that continuation lines are properly handled
            # Count entries that are continuation lines (don't start with log level)
            self.cursor.execute("""
                SELECT message FROM logs 
                WHERE component = ? AND message NOT LIKE '[%]%'
                ORDER BY ts
            """, ("test_component",))
            
            continuation_lines = self.cursor.fetchall()
            # Should have at least 3 continuation lines based on our fixture
            assert len(continuation_lines) >= 3
            
        finally:
            self.tearDown_database()


class TestTimestampPattern:
    """Test cases for the timestamp regex pattern"""
    
    def test_timestamp_pattern_matches(self):
        """Test that the timestamp pattern matches valid timestamps"""
        pattern = log_analyzer.TIMESTAMP_PATTERN
        
        # Valid timestamps
        valid_cases = [
            "14:45:36.507 [info] Message",
            "00:00:00.000 [debug] Start",
            "23:59:59.999 [error] End",
            "09:30:15.123 Service message"
        ]
        
        for case in valid_cases:
            match = pattern.match(case)
            assert match is not None, f"Should match: {case}"
            assert len(match.groups()) == 2  # time and message groups
    
    def test_timestamp_pattern_no_match(self):
        """Test that the pattern doesn't match invalid formats"""
        pattern = log_analyzer.TIMESTAMP_PATTERN
        
        # Invalid timestamps
        invalid_cases = [
            "Not a timestamp line",
            "14:45:36 [info] No milliseconds",
            "25:00:00.000 [error] Invalid hour",  # Invalid hour > 23
            "14:60:00.000 [error] Invalid minute",  # Invalid minute > 59
            "14:45:60.000 [error] Invalid second",  # Invalid second > 59
            "",
            " 14:45:36.507 [info] Leading space"
        ]
        
        for case in invalid_cases:
            match = pattern.match(case)
            assert match is None, f"Should not match: {case}"


class TestIntegration:
    """Integration tests for the complete workflow"""
    
    def test_end_to_end_processing(self):
        """Test the complete log processing workflow"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up test environment
            db_path = os.path.join(temp_dir, "test.db")
            fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
            
            # Setup database
            conn = log_analyzer.setup_database(db_path)
            cursor = conn.cursor()
            
            # Discover and process log files
            log_files = log_analyzer.discover_log_files(fixtures_dir)
            assert len(log_files) > 0
            
            test_date = date(2023, 10, 15)
            total_entries = 0
            
            for log_file in log_files:
                component = log_analyzer.extract_component_name(log_file)
                entries = log_analyzer.process_log_file(log_file, component, test_date, cursor)
                total_entries += entries
            
            conn.commit()
            
            # Verify results
            assert total_entries > 0
            
            # Check database integrity
            cursor.execute("SELECT COUNT(*) FROM logs")
            db_total = cursor.fetchone()[0]
            assert db_total == total_entries
            
            # Check that all components are represented
            cursor.execute("SELECT DISTINCT component FROM logs")
            components = [row[0] for row in cursor.fetchall()]
            assert len(components) >= 2  # We have at least 2 different log files
            
            # Check timestamp ordering
            cursor.execute("SELECT ts FROM logs ORDER BY ts")
            timestamps = [row[0] for row in cursor.fetchall()]
            assert timestamps == sorted(timestamps)  # Should be in ascending order
            
            conn.close()


class TestErrorHandling:
    """Test error handling scenarios"""
    
    def test_missing_log_file(self):
        """Test handling of missing log files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            conn = log_analyzer.setup_database(db_path)
            cursor = conn.cursor()
            
            # Try to process non-existent file
            with pytest.raises(FileNotFoundError):
                log_analyzer.process_log_file(
                    "nonexistent.log", "test", date(2023, 10, 15), cursor
                )
            
            conn.close()
    
    def test_invalid_database_path(self):
        """Test handling of invalid database paths"""
        # Try to create database in non-existent directory
        with pytest.raises(sqlite3.OperationalError):
            log_analyzer.setup_database("/nonexistent/path/test.db")
    
    def test_corrupted_log_file(self):
        """Test handling of files with encoding issues"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file with invalid UTF-8
            bad_file = os.path.join(temp_dir, "bad.log")
            with open(bad_file, 'wb') as f:
                f.write(b'12:00:00.000 [info] Valid line\n')
                f.write(b'12:00:01.000 [error] Invalid \xff\xfe chars\n')
                f.write(b'12:00:02.000 [info] Another valid line\n')
            
            db_path = os.path.join(temp_dir, "test.db")
            conn = log_analyzer.setup_database(db_path)
            cursor = conn.cursor()
            
            # Should handle the file gracefully (using errors='replace')
            entries = log_analyzer.process_log_file(
                bad_file, "bad_component", date(2023, 10, 15), cursor
            )
            
            assert entries > 0  # Should process some entries despite encoding issues
            conn.close()


if __name__ == '__main__':
    pytest.main([__file__])