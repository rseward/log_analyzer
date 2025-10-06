#!/usr/bin/env python3
"""
Integration tests for log_analyzer.py

These tests verify the complete end-to-end workflow including CLI integration.
"""

import pytest
import tempfile
import os
import sqlite3
import subprocess
import sys
from datetime import date, datetime
from click.testing import CliRunner

# Import the module under test
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import log_analyzer


class TestCLIIntegration:
    """Test CLI integration using Click's test runner"""
    
    def test_cli_help(self):
        """Test that CLI help works"""
        runner = CliRunner()
        result = runner.invoke(log_analyzer.main, ['--help'])
        
        assert result.exit_code == 0
        assert 'Kubernetes log analyzer' in result.output
        assert '--date' in result.output
        assert '--database' in result.output
        assert '--directory' in result.output
    
    def test_cli_with_fixtures(self):
        """Test CLI execution with test fixtures"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Copy fixtures to temp directory for isolation
            fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
            test_fixtures = os.path.join(temp_dir, "test_logs")
            os.makedirs(test_fixtures)
            
            # Copy fixture files
            for fixture_file in os.listdir(fixtures_dir):
                if fixture_file.endswith('.log'):
                    src = os.path.join(fixtures_dir, fixture_file)
                    dst = os.path.join(test_fixtures, fixture_file)
                    with open(src, 'r') as f_src, open(dst, 'w') as f_dst:
                        f_dst.write(f_src.read())
            
            # Set up database path
            db_path = os.path.join(temp_dir, "test_cli.db")
            
            # Run CLI
            runner = CliRunner()
            result = runner.invoke(log_analyzer.main, [
                '--database', db_path,
                '--directory', test_fixtures,
                '--date', '2023-10-15'
            ])
            
            # Check that CLI executed successfully
            assert result.exit_code == 0
            assert 'Completed!' in result.output
            assert os.path.exists(db_path)
            
            # Verify database content
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM logs")
            total_count = cursor.fetchone()[0]
            assert total_count > 0
            
            cursor.execute("SELECT DISTINCT component FROM logs")
            components = [row[0] for row in cursor.fetchall()]
            assert len(components) >= 2
            
            conn.close()
    
    def test_cli_invalid_date(self):
        """Test CLI with invalid date format"""
        runner = CliRunner()
        result = runner.invoke(log_analyzer.main, [
            '--date', 'invalid-date'
        ])
        
        assert result.exit_code == 0  # Script handles error gracefully
        assert 'Invalid date format' in result.output
    
    def test_cli_no_log_files(self):
        """Test CLI when no log files are found"""
        with tempfile.TemporaryDirectory() as temp_dir:
            runner = CliRunner()
            result = runner.invoke(log_analyzer.main, [
                '--directory', temp_dir
            ])
            
            assert result.exit_code == 0
            assert 'No *.log files found' in result.output


class TestRealWorldScenarios:
    """Test real-world usage scenarios"""
    
    def test_large_log_processing(self):
        """Test processing larger log files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a larger test log file
            large_log = os.path.join(temp_dir, "large_service.log")
            with open(large_log, 'w') as f:
                base_time = "10:00:00"
                for i in range(1000):  # 1000 log entries
                    minutes = i // 60
                    seconds = i % 60
                    timestamp = f"10:{minutes:02d}:{seconds:02d}.{i % 1000:03d}"
                    f.write(f"{timestamp} [info] Log entry number {i}\n")
                    
                    # Add some multi-line entries
                    if i % 100 == 0:
                        f.write(f"Additional details for entry {i}\n")
                        f.write(f"More context information\n")
            
            # Process the large file
            db_path = os.path.join(temp_dir, "large_test.db")
            conn = log_analyzer.setup_database(db_path)
            cursor = conn.cursor()
            
            test_date = date(2023, 10, 15)
            entries_processed = log_analyzer.process_log_file(
                large_log, "large_service", test_date, cursor
            )
            
            conn.commit()
            
            # Verify all entries were processed
            assert entries_processed > 1000  # Should be more due to continuation lines
            
            # Verify database integrity
            cursor.execute("SELECT COUNT(*) FROM logs WHERE component = ?", ("large_service",))
            db_count = cursor.fetchone()[0]
            assert db_count == entries_processed
            
            # Verify timestamp ordering
            cursor.execute("SELECT ts FROM logs WHERE component = ? ORDER BY ts", ("large_service",))
            timestamps = [row[0] for row in cursor.fetchall()]
            assert timestamps == sorted(timestamps)
            
            conn.close()
    
    def test_multiple_components_same_time(self):
        """Test processing multiple components with overlapping timestamps"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple log files with same timestamps
            log_files = []
            components = ["service_a", "service_b", "service_c"]
            
            for i, component in enumerate(components):
                log_file = os.path.join(temp_dir, f"{i:02d} - {component}.log")
                log_files.append((log_file, component))
                
                with open(log_file, 'w') as f:
                    f.write(f"12:00:00.000 [{component}] Service {component} starting\n")
                    f.write(f"12:00:01.000 [{component}] Processing request\n")
                    f.write(f"12:00:02.000 [{component}] Operation completed\n")
            
            # Process all files
            db_path = os.path.join(temp_dir, "multi_component.db")
            conn = log_analyzer.setup_database(db_path)
            cursor = conn.cursor()
            
            test_date = date(2023, 10, 15)
            total_entries = 0
            
            for log_file, component in log_files:
                entries = log_analyzer.process_log_file(log_file, component, test_date, cursor)
                total_entries += entries
            
            conn.commit()
            
            # Verify all components are present
            cursor.execute("SELECT DISTINCT component FROM logs")
            db_components = sorted([row[0] for row in cursor.fetchall()])
            assert db_components == sorted(components)
            
            # Verify each component has correct number of entries
            for component in components:
                cursor.execute("SELECT COUNT(*) FROM logs WHERE component = ?", (component,))
                count = cursor.fetchone()[0]
                assert count == 3  # Each component should have 3 entries
            
            # Verify we can query by timestamp and component
            test_timestamp = log_analyzer.parse_time_to_unix_timestamp("12:00:01.000", test_date)
            cursor.execute("SELECT component FROM logs WHERE ts = ? ORDER BY component", (test_timestamp,))
            results = [row[0] for row in cursor.fetchall()]
            assert results == sorted(components)
            
            conn.close()
    
    def test_edge_case_log_formats(self):
        """Test handling of edge case log formats"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create log file with various edge cases
            edge_log = os.path.join(temp_dir, "edge_cases.log")
            with open(edge_log, 'w') as f:
                f.write("10:00:00.000 [info] Normal message\n")
                f.write("Line without timestamp\n")
                f.write("\n")  # Empty line
                f.write("10:00:01.001 [error] Message with unicode: café 🚀\n")
                f.write("Continuation with unicode: naïve résumé\n")
                f.write("10:00:02.002 [warn] Very long message " + "x" * 1000 + "\n")
                f.write("10:00:03.003 [debug] Message with special chars: !@#$%^&*(){}[]|\\:;\"'<>?,./\n")
                f.write("10:00:04.004 [trace] Message\nwith\nnewlines\nin\ncontinuation\n")
                f.write("10:00:05.005 [info] Final message\n")
            
            # Process the edge case file
            db_path = os.path.join(temp_dir, "edge_test.db")
            conn = log_analyzer.setup_database(db_path)
            cursor = conn.cursor()
            
            test_date = date(2023, 10, 15)
            entries_processed = log_analyzer.process_log_file(
                edge_log, "edge_service", test_date, cursor
            )
            
            conn.commit()
            
            # Verify processing completed without errors
            assert entries_processed > 0
            
            # Verify unicode handling
            cursor.execute("SELECT message FROM logs WHERE message LIKE '%café%'")
            unicode_result = cursor.fetchone()
            assert unicode_result is not None
            assert "café" in unicode_result[0]
            
            # Verify long message handling
            cursor.execute("SELECT message FROM logs WHERE LENGTH(message) > 500")
            long_message = cursor.fetchone()
            assert long_message is not None
            
            conn.close()


class TestConcurrencyAndPerformance:
    """Test performance and concurrency aspects"""
    
    def test_database_concurrent_access(self):
        """Test that database can handle multiple cursors with proper transaction handling"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "concurrent_test.db")
            
            # Create database
            conn1 = log_analyzer.setup_database(db_path)
            cursor1 = conn1.cursor()
            
            # Insert data from first connection and commit
            iso_ts1 = datetime.fromtimestamp(1697356800).isoformat() + 'Z'
            cursor1.execute("INSERT INTO logs (ts, timestamp, component, message) VALUES (?, ?, ?, ?)",
                           (1697356800, iso_ts1, "test1", "Message from cursor 1"))
            conn1.commit()
            
            # Open second connection after first commit
            conn2 = sqlite3.connect(db_path)
            cursor2 = conn2.cursor()
            
            # Insert data from second cursor
            iso_ts2 = datetime.fromtimestamp(1697356801).isoformat() + 'Z'
            cursor2.execute("INSERT INTO logs (ts, timestamp, component, message) VALUES (?, ?, ?, ?)",
                           (1697356801, iso_ts2, "test2", "Message from cursor 2"))
            conn2.commit()
            
            # Verify both inserts worked
            cursor1.execute("SELECT COUNT(*) FROM logs")
            count = cursor1.fetchone()[0]
            assert count == 2
            
            # Verify we can read from both connections
            cursor2.execute("SELECT COUNT(*) FROM logs")
            count2 = cursor2.fetchone()[0]
            assert count2 == 2
            
            conn1.close()
            conn2.close()


class TestCommandLineIntegration:
    """Test actual command line execution"""
    
    def test_script_execution(self):
        """Test running the script as a subprocess"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Copy a fixture file
            fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
            fixture_file = None
            for f in os.listdir(fixtures_dir):
                if f.endswith('.log'):
                    fixture_file = f
                    break
            
            if fixture_file:
                src = os.path.join(fixtures_dir, fixture_file)
                dst = os.path.join(temp_dir, fixture_file)
                with open(src, 'r') as f_src, open(dst, 'w') as f_dst:
                    f_dst.write(f_src.read())
                
                # Get path to log_analyzer.py
                script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "log_analyzer.py")
                db_path = os.path.join(temp_dir, "subprocess_test.db")
                
                # Run script as subprocess
                result = subprocess.run([
                    sys.executable, script_path,
                    "--database", db_path,
                    "--directory", temp_dir,
                    "--date", "2023-10-15"
                ], capture_output=True, text=True)
                
                # Check execution was successful
                assert result.returncode == 0
                assert "Completed!" in result.stdout
                assert os.path.exists(db_path)
                
                # Verify database was created and populated
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM logs")
                count = cursor.fetchone()[0]
                assert count > 0
                conn.close()


if __name__ == '__main__':
    pytest.main([__file__])