#!/usr/bin/env python3
"""
Kubernetes log analyzer for micro service architecture application.

This script processes *.log files in the current directory, parses timestamps,
and stores log entries in a SQLite database for analysis.
"""

import sqlite3
import re
import os
import glob
from datetime import datetime, date, time
from pathlib import Path

import click
from tqdm import tqdm


# Regex pattern to match timestamp format like "14:45:36.507"
# More restrictive: hours 00-23, minutes 00-59, seconds 00-59
TIMESTAMP_PATTERN = re.compile(r'^((?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d\.\d{3})\s+(.*)$')


def setup_database(db_path="logs.db"):
    """
    Create SQLite database and logs table with proper indexes.
    Handles migration of existing databases that don't have the timestamp column.
    
    Args:
        db_path (str): Path to the SQLite database file
        
    Returns:
        sqlite3.Connection: Database connection object
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            timestamp VARCHAR(50) NOT NULL,
            component VARCHAR(255) NOT NULL,
            message TEXT NOT NULL
        )
    ''')
    
    # Check if timestamp column exists (for migration)
    cursor.execute("PRAGMA table_info(logs)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'timestamp' not in columns:
        # Add timestamp column and populate it with ISO format datetime strings
        cursor.execute('ALTER TABLE logs ADD COLUMN timestamp VARCHAR(50)')
        # Convert existing UNIX timestamps to ISO format
        cursor.execute('SELECT id, ts FROM logs WHERE timestamp IS NULL')
        rows = cursor.fetchall()
        for row_id, ts in rows:
            iso_timestamp = datetime.fromtimestamp(ts).isoformat() + 'Z'
            cursor.execute('UPDATE logs SET timestamp = ? WHERE id = ?', (iso_timestamp, row_id))
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)')
    
    # Create indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_ts ON logs(ts)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_component ON logs(component)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_ts_component ON logs(ts, component)')
    
    conn.commit()
    return conn


def extract_component_name(filename):
    """
    Extract component name from log filename by removing prefix and extension.
    
    Examples:
        "01 - reaper.log" -> "reaper"
        "02 - alchemist.log" -> "alchemist"
    
    Args:
        filename (str): Original log filename
        
    Returns:
        str: Extracted component name
    """
    basename = Path(filename).stem
    
    # Remove number prefix pattern like "01 - ", "02 - ", etc.
    if re.match(r'^\d+\s*-\s*', basename):
        basename = re.sub(r'^\d+\s*-\s*', '', basename)
    
    return basename


def parse_time_to_unix_timestamp(time_str, reference_date):
    """
    Parse time string like "14:45:36.507" and convert to UNIX timestamp.
    
    Args:
        time_str (str): Time string in format "HH:MM:SS.mmm"
        reference_date (date): Date to use for timestamp conversion
        
    Returns:
        int: UNIX timestamp
    """
    # Parse the time components
    time_parts = time_str.split(':')
    hours = int(time_parts[0])
    minutes = int(time_parts[1])
    seconds_parts = time_parts[2].split('.')
    seconds = int(seconds_parts[0])
    milliseconds = int(seconds_parts[1])
    microseconds = milliseconds * 1000  # Convert milliseconds to microseconds
    
    # Create datetime object
    dt = datetime.combine(reference_date, time(hours, minutes, seconds, microseconds))
    
    # Convert to UNIX timestamp
    return int(dt.timestamp())


def discover_log_files(directory="."):
    """
    Find all *.log files in the specified directory.
    
    Args:
        directory (str): Directory to search for log files
        
    Returns:
        list: List of log file paths
    """
    pattern = os.path.join(directory, "*.log")
    return glob.glob(pattern)


def process_log_file(filepath, component, reference_date, cursor):
    """
    Process a single log file and insert entries into the database.
    
    Args:
        filepath (str): Path to the log file
        component (str): Component name extracted from filename
        reference_date (date): Date to use for timestamp conversion
        cursor: Database cursor for insertions
        
    Returns:
        int: Number of log entries processed
    """
    entries_processed = 0
    current_timestamp = None
    
    with open(filepath, 'r', encoding='utf-8', errors='replace') as file:
        lines = file.readlines()
        
        for line in tqdm(lines, desc=f"Processing {component}", leave=False):
            line = line.rstrip('\n\r')
            
            if not line:  # Skip empty lines
                continue
            
            # Check if line starts with a timestamp
            match = TIMESTAMP_PATTERN.match(line)
            
            if match:
                # New timestamp found
                time_str = match.group(1)
                message = match.group(2)
                current_timestamp = parse_time_to_unix_timestamp(time_str, reference_date)
            else:
                # Line continues from previous timestamp
                message = line
            
            # Insert into database if we have a current timestamp
            if current_timestamp is not None:
                # Convert timestamp to ISO format datetime string
                timestamp_str = datetime.fromtimestamp(current_timestamp).isoformat() + 'Z'
                cursor.execute(
                    'INSERT INTO logs (ts, timestamp, component, message) VALUES (?, ?, ?, ?)',
                    (current_timestamp, timestamp_str, component, message)
                )
                entries_processed += 1
    
    return entries_processed


@click.command()
@click.option('--date', '-d', 
              help='Date to use for timestamp conversion (YYYY-MM-DD). Defaults to today.',
              default=None)
@click.option('--database', '--db',
              help='SQLite database file path',
              default='logs.db')
@click.option('--directory', '--dir',
              help='Directory to search for *.log files',
              default='.')
def main(date, database, directory):
    """
    Kubernetes log analyzer for micro service architecture application.
    
    Processes all *.log files in the specified directory, parses timestamps,
    and stores log entries in a SQLite database for analysis.
    """
    # Parse reference date
    if date:
        try:
            reference_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            click.echo(f"Error: Invalid date format '{date}'. Use YYYY-MM-DD format.")
            return
    else:
        reference_date = datetime.now().date()
    
    click.echo(f"Using reference date: {reference_date}")
    click.echo(f"Database: {database}")
    click.echo(f"Search directory: {directory}")
    
    # Setup database
    click.echo("Setting up database...")
    conn = setup_database(database)
    cursor = conn.cursor()
    
    # Discover log files
    log_files = discover_log_files(directory)
    
    if not log_files:
        click.echo("No *.log files found in the specified directory.")
        conn.close()
        return
    
    click.echo(f"Found {len(log_files)} log files:")
    for log_file in log_files:
        component = extract_component_name(log_file)
        click.echo(f"  {log_file} -> component: {component}")
    
    # Process each log file
    total_entries = 0
    
    for log_file in tqdm(log_files, desc="Processing log files"):
        component = extract_component_name(log_file)
        
        try:
            entries = process_log_file(log_file, component, reference_date, cursor)
            total_entries += entries
            tqdm.write(f"Processed {entries} entries from {component}")
        except Exception as e:
            tqdm.write(f"Error processing {log_file}: {str(e)}")
            continue
    
    # Commit changes and close database
    conn.commit()
    conn.close()
    
    click.echo(f"\nCompleted! Processed {total_entries} total log entries.")
    click.echo(f"Database saved to: {database}")


if __name__ == '__main__':
    main()