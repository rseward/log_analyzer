#!/usr/bin/env python3
"""
Log query tool for querying logs.db databases created by log_analyzer.

This tool allows users to query log entries by timestamp, with time ranges,
and apply filters to find specific log messages.
"""

import sqlite3
import re
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

import click
from tqdm import tqdm


def parse_timestamp(timestamp_str: str) -> int:
    """
    Parse timestamp from either UNIX timestamp integer or ISO format string.
    
    Args:
        timestamp_str (str): Timestamp as string (either "1697395536" or "2023-10-15T14:45:36")
        
    Returns:
        int: UNIX timestamp
        
    Raises:
        ValueError: If timestamp format is not recognized
    """
    timestamp_str = timestamp_str.strip()
    
    # Try parsing as integer (UNIX timestamp)
    try:
        return int(timestamp_str)
    except ValueError:
        pass
    
    # Try parsing as ISO format (with or without 'Z' suffix)
    iso_formats = [
        "%Y-%m-%dT%H:%M:%S",      # 2023-10-15T14:45:36
        "%Y-%m-%dT%H:%M:%SZ",     # 2023-10-15T14:45:36Z
        "%Y-%m-%d %H:%M:%S",      # 2023-10-15 14:45:36
    ]
    
    for fmt in iso_formats:
        try:
            dt = datetime.strptime(timestamp_str, fmt)
            return int(dt.timestamp())
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse timestamp: {timestamp_str}. "
                     f"Expected UNIX timestamp or ISO format (YYYY-MM-DDTHH:MM:SS)")


def parse_filter_expression(filter_expr: str) -> Dict[str, Any]:
    """
    Parse filter expression similar to UNIX find command.
    
    Supports:
    - Simple string matching: "error"
    - Field-specific matching: "component:reaper"
    - AND/OR operations: "error AND component:reaper"
    - NOT operations: "not(error)", "NOT error", "!error"
    - Parentheses for grouping: "(error OR warning) AND component:reaper"
    
    Args:
        filter_expr (str): Filter expression string
        
    Returns:
        Dict with parsed filter conditions
    """
    if not filter_expr:
        return {"conditions": []}
    
    # For now, implement basic string matching and field-specific matching
    # This can be extended later for more complex expressions
    conditions = []
    
    # Split by AND/OR while preserving the operators
    parts = re.split(r'\s+(AND|OR|\&\&|\|\|)\s+', filter_expr, flags=re.IGNORECASE)
    
    i = 0
    while i < len(parts):
        condition = parts[i].strip()
        operator = "AND"  # Default operator
        
        if i + 1 < len(parts) and parts[i + 1].upper() in ["AND", "OR", "&&", "||"]:
            operator = parts[i + 1].upper()
            if operator in ["&&", "||"]:
                operator = "AND" if operator == "&&" else "OR"
        
        # Parse individual condition
        negated = False
        
        # Check for NOT patterns
        condition_clean = condition.strip()
        
        # Handle not(value) pattern
        not_func_match = re.match(r'^not\s*\((.+)\)$', condition_clean, re.IGNORECASE)
        if not_func_match:
            negated = True
            condition_clean = not_func_match.group(1).strip()
        # Handle NOT value or !value patterns
        elif re.match(r'^(NOT|!)\s*', condition_clean, re.IGNORECASE):
            negated = True
            condition_clean = re.sub(r'^(NOT|!)\s*', '', condition_clean, flags=re.IGNORECASE).strip()
        
        if ":" in condition_clean:
            # Field-specific condition like "component:reaper"
            field, value = condition_clean.split(":", 1)
            conditions.append({
                "type": "field",
                "field": field.strip(),
                "value": value.strip(),
                "negated": negated,
                "operator": operator if i + 2 < len(parts) else None
            })
        else:
            # General string matching
            conditions.append({
                "type": "general",
                "value": condition_clean,
                "negated": negated,
                "operator": operator if i + 2 < len(parts) else None
            })
        
        i += 2  # Skip the operator
    
    return {"conditions": conditions}


def build_sql_query(
    start_ts: int,
    end_ts: int,
    filters: Dict[str, Any],
    fields: List[str],
    limit: Optional[int] = None
) -> Tuple[str, List[Any]]:
    """
    Build SQL query based on parameters.
    
    Args:
        start_ts: Start timestamp
        end_ts: End timestamp  
        filters: Parsed filter conditions
        fields: List of fields to select
        limit: Optional limit on results
        
    Returns:
        Tuple of (sql_query, parameters)
    """
    # Build SELECT clause
    select_fields = ", ".join(fields)
    
    # Build WHERE clause
    where_conditions = ["ts BETWEEN ? AND ?"]
    params = [start_ts, end_ts]
    
    # Add filter conditions with proper OR/AND logic
    if filters["conditions"]:
        filter_parts = []
        current_filter_sql = []
        
        for i, condition in enumerate(filters["conditions"]):
            # Build the SQL condition for this filter
            negated = condition.get("negated", False)
            not_operator = "NOT " if negated else ""
            
            if condition["type"] == "field":
                field = condition["field"]
                value = condition["value"]
                
                if field in ["component", "message", "timestamp"]:
                    current_filter_sql.append(f"{field} {not_operator}LIKE ?")
                    params.append(f"%{value}%")
                elif field == "ts":
                    try:
                        ts_value = int(value)
                        equality_op = "!=" if negated else "="
                        current_filter_sql.append(f"ts {equality_op} ?")
                        params.append(ts_value)
                    except ValueError:
                        # Skip invalid ts values
                        continue
                else:
                    # Unknown field, search in message
                    current_filter_sql.append(f"message {not_operator}LIKE ?")
                    params.append(f"%{value}%")
            else:
                # General search in message
                current_filter_sql.append(f"message {not_operator}LIKE ?")
                params.append(f"%{condition['value']}%")
            
            # Check if there's a next condition and what operator to use
            if current_filter_sql:
                if condition.get("operator") == "OR":
                    # Add OR to the current filter part
                    filter_parts.append(current_filter_sql[-1])
                    if i < len(filters["conditions"]) - 1:  # Not the last condition
                        filter_parts.append("OR")
                else:
                    # Default AND logic or no operator (last condition)
                    filter_parts.append(current_filter_sql[-1])
                    if condition.get("operator") == "AND" and i < len(filters["conditions"]) - 1:
                        filter_parts.append("AND")
                
                current_filter_sql = []  # Reset for next iteration
        
        if filter_parts:
            # Join filter parts with spaces (they already include AND/OR operators)
            filter_clause = " ".join(filter_parts)
            where_conditions.append(f"({filter_clause})")
    
    # Build complete query
    query = f"""
        SELECT {select_fields}
        FROM logs
        WHERE {' AND '.join(where_conditions)}
        ORDER BY ts ASC
    """
    
    if limit:
        query += f" LIMIT {limit}"
    
    return query.strip(), params


def format_output_line(row: Dict[str, Any], fields: List[str]) -> str:
    """
    Format output line based on selected fields.
    
    Args:
        row: Database row as dictionary
        fields: List of fields to include
        
    Returns:
        Formatted output string
    """
    parts = []
    for field in fields:
        value = row.get(field, "")
        if field == "ts":
            # Show UNIX timestamp as integer
            parts.append(str(value))
        else:
            parts.append(str(value))
    
    return " | ".join(parts)


def get_available_fields(db_path: str) -> List[str]:
    """
    Get available fields from the logs table.
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        List of available field names
    """
    if not os.path.exists(db_path):
        return ["id", "ts", "timestamp", "component", "message"]
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(logs)")
        fields = [row[1] for row in cursor.fetchall()]
        conn.close()
        return fields
    except sqlite3.Error:
        return ["id", "ts", "timestamp", "component", "message"]


@click.command()
@click.argument("timestamp", required=False)
@click.option(
    "--database", "--db",
    default="logs.db",
    help="Path to the SQLite database file (default: logs.db)"
)
@click.option(
    "--range", "-r",
    default=120,
    type=int,
    help="Time range in seconds before and after timestamp (default: 120)"
)
@click.option(
    "--filter", "-f", "filters",
    multiple=True,
    help="Filter expressions (can be used multiple times). "
         "Examples: 'error', 'component:reaper', 'error AND component:reaper', 'error OR warning', "
         "'not(error)', 'NOT warning', '!debug'"
)
@click.option(
    "--withtime",
    is_flag=True,
    help="Include ts (UNIX timestamp) column in output"
)
@click.option(
    "--fields",
    help="Specify fields to return and their order (comma-separated). "
         "Example: 'timestamp,component,message' or 'component,message,ts'"
)
@click.option(
    "--limit", "-l",
    type=int,
    help="Limit number of results returned"
)
@click.option(
    "--show-fields",
    is_flag=True,
    help="Show available fields and exit"
)
def main(timestamp, database, range, filters, withtime, fields, limit, show_fields):
    """
    Query log entries from a logs.db database.
    
    TIMESTAMP can be either:
    - UNIX timestamp: 1697395536
    - ISO format: 2023-10-15T14:45:36 (without timezone)
    - ISO format: 2023-10-15 14:45:36
    
    Examples:
    \b
      # Query logs around specific time
      log_query.py 1697395536
      
      # Query with custom time range (300 seconds = 5 minutes)
      log_query.py "2023-10-15T14:45:36" --range 300
      
      # Query with filters
      log_query.py 1697395536 --filter "error" --filter "component:reaper"
      
      # Query with NOT filters (exclude messages containing 'debug')
      log_query.py 1697395536 --filter "not(debug)" --filter "error"
      
      # Query excluding specific component
      log_query.py 1697395536 --filter "NOT component:reaper"
      
      # Custom output fields
      log_query.py 1697395536 --fields "component,message"
      
      # Include UNIX timestamp in output
      log_query.py 1697395536 --withtime
    """
    # Show available fields if requested
    if show_fields:
        fields_list = get_available_fields(database)
        click.echo("Available fields:")
        for field in fields_list:
            click.echo(f"  {field}")
        sys.exit(0)
    
    # Check if timestamp is provided when not showing fields
    if not timestamp:
        click.echo("Error: TIMESTAMP argument is required.", err=True)
        click.echo("Use --show-fields to see available fields without specifying timestamp.")
        sys.exit(1)
    
    # Check if database exists
    if not os.path.exists(database):
        click.echo(f"Error: Database file '{database}' not found", err=True)
        sys.exit(1)
    
    try:
        # Parse target timestamp
        target_ts = parse_timestamp(timestamp)
        
        # Calculate time range
        start_ts = target_ts - range
        end_ts = target_ts + range
        
        # Parse filters
        combined_filters = {"conditions": []}
        for filter_expr in filters:
            parsed = parse_filter_expression(filter_expr)
            combined_filters["conditions"].extend(parsed["conditions"])
        
        # Determine output fields
        if fields:
            field_list = [f.strip() for f in fields.split(",")]
        elif withtime:
            field_list = ["timestamp", "ts", "component", "message"]
        else:
            field_list = ["timestamp", "component", "message"]
        
        # Validate fields exist
        available_fields = get_available_fields(database)
        invalid_fields = [f for f in field_list if f not in available_fields]
        if invalid_fields:
            click.echo(f"Error: Invalid fields: {', '.join(invalid_fields)}", err=True)
            click.echo(f"Available fields: {', '.join(available_fields)}")
            sys.exit(1)
        
        # Build and execute query
        query, params = build_sql_query(start_ts, end_ts, combined_filters, field_list, limit)
        
        # Connect to database and execute query
        conn = sqlite3.connect(database)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        cursor = conn.cursor()
        
        click.echo(f"Querying logs from {datetime.fromtimestamp(start_ts)} to {datetime.fromtimestamp(end_ts)}")
        if filters:
            click.echo(f"Filters: {', '.join(filters)}")
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        if not rows:
            click.echo("No matching log entries found.")
            conn.close()
            sys.exit(0)
        
        # Display results with progress bar if many results
        click.echo(f"\nFound {len(rows)} matching entries:")
        click.echo("-" * 80)
        
        # Show header
        header_parts = []
        for field in field_list:
            if field == "ts":
                header_parts.append("UNIX_TS")
            else:
                header_parts.append(field.upper())
        click.echo(" | ".join(header_parts))
        click.echo("-" * 80)
        
        # Show results
        if len(rows) > 100:
            # Use progress bar for large result sets
            with tqdm(rows, desc="Displaying results") as pbar:
                for row in pbar:
                    row_dict = dict(row)
                    click.echo(format_output_line(row_dict, field_list))
        else:
            for row in rows:
                row_dict = dict(row)
                click.echo(format_output_line(row_dict, field_list))
        
        conn.close()
        
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except sqlite3.Error as e:
        click.echo(f"Database error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()