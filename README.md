# Kubernetes Log Analyzer

A powerful Python tool for parsing and analyzing Kubernetes microservice logs. This tool processes log files from multiple components, extracts timestamps, and stores structured log data in a SQLite database for efficient querying and analysis.

## Features

- 🔍 **Smart Log Parsing**: Automatically parses timestamp formats like `14:45:36.507`
- 📊 **Multi-Component Support**: Processes logs from multiple microservices simultaneously
- 🗃️ **SQLite Storage**: Efficient database storage with proper indexing
- 📈 **Progress Tracking**: Real-time progress indicators using tqdm
- 🎯 **CLI Interface**: Easy-to-use command-line interface with Click
- 📝 **Multi-line Log Support**: Handles continuation lines and stack traces
- 🔧 **Configurable**: Flexible date handling and directory selection
- 🔎 **Advanced Querying**: Powerful log query tool with filtering and time range support
- ✅ **Well-Tested**: Comprehensive test suite with 96% code coverage

## Installation

### Prerequisites

- Python 3.8+
- `uv` package manager (recommended) or `pip`

### Setup

1. **Clone or download the project files**

2. **Create and activate a virtual environment:**
   ```bash
   uv venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   uv pip install -r requirements.txt
   ```

4. **For development (includes testing dependencies):**
   ```bash
   uv pip install -r requirements-test.txt
   ```

## Usage

### Basic Usage

Process all `*.log` files in the current directory:

```bash
python log_analyzer.py
```

### Advanced Usage

```bash
# Specify custom database and date
python log_analyzer.py --database my_logs.db --date 2023-10-15

# Process logs from a specific directory
python log_analyzer.py --directory /path/to/logs --date 2023-10-15

# Get help
python log_analyzer.py --help
```

### Command Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--database` | `--db` | SQLite database file path | `logs.db` |
| `--directory` | `--dir` | Directory to search for *.log files | `.` (current directory) |
| `--date` | `-d` | Date for timestamp conversion (YYYY-MM-DD) | Today's date |
| `--help` | | Show help message | |

## Querying Logs

Once you've processed logs with `log_analyzer.py`, you can use the powerful `log_query.py` tool to search and filter your log data.

### Basic Querying

```bash
# Query logs around a specific UNIX timestamp (±2 minutes by default)
python log_query.py 1759400000

# Query using ISO format timestamp
python log_query.py "2025-10-02T06:11:20"

# Show available database fields
python log_query.py --show-fields
```

### Advanced Query Options

```bash
# Custom time range (5 minutes = 300 seconds before/after)
python log_query.py 1759400000 --range 300

# Filter by message content
python log_query.py 1759400000 --filter "error"

# Filter by component
python log_query.py 1759400000 --filter "component:alchemist"

# NOT conditions (exclude messages) - three syntaxes available:
python log_query.py 1759400000 --filter "not(error)"           # function syntax
python log_query.py 1759400000 --filter "NOT warning"          # keyword syntax
python log_query.py 1759400000 --filter "!debug"               # exclamation syntax

# NOT with field-specific filters
python log_query.py 1759400000 --filter "NOT component:reaper"  # exclude component
python log_query.py 1759400000 --filter "not(component:debug_service)"  # function syntax

# AND conditions (restrictive - must match ALL conditions)
python log_query.py 1759400000 --filter "component:alchemist AND error"
python log_query.py 1759400000 --filter "error AND warn"  # messages with both terms

# OR conditions (inclusive - matches ANY condition)
python log_query.py 1759400000 --filter "error OR warning"
python log_query.py 1759400000 --filter "component:alchemist OR component:forklift"
python log_query.py 1759400000 --filter "component:forklift OR error"  # mixed conditions

# Alternative OR syntax using ||
python log_query.py 1759400000 --filter "error || warning"

# NOT with AND/OR combinations
python log_query.py 1759400000 --filter "error AND not(debug)"           # errors but not debug
python log_query.py 1759400000 --filter "component:alchemist AND !info"   # alchemist non-info messages
python log_query.py 1759400000 --filter "NOT warning OR error"            # exclude warnings OR show errors

# Complex expressions (left-to-right evaluation)
python log_query.py 1759400000 --filter "error AND component:alchemist OR warning"

# Multiple filter options (combined with AND logic)
python log_query.py 1759400000 --filter "error" --filter "component:reaper"

# Limit number of results
python log_query.py 1759400000 --limit 10

# Include UNIX timestamp in output
python log_query.py 1759400000 --withtime

# Custom output fields
python log_query.py 1759400000 --fields "component,message"
python log_query.py 1759400000 --fields "timestamp,ts,component,message"

# Use different database file
python log_query.py 1759400000 --database /path/to/other.db
```

### Query Command Reference

| Option | Description | Example |
|--------|-------------|----------|
| `TIMESTAMP` | Target timestamp (UNIX or ISO format) | `1759400000`, `"2025-10-02T06:11:20"` |
| `--database`, `--db` | Database file path (default: `logs.db`) | `--db /path/to/logs.db` |
| `--range`, `--r` | Time range in seconds (default: 120) | `--range 300` |
| `--filter`, `--f` | Filter expressions (multiple allowed) | `--filter "error"` |
| `--withtime` | Include UNIX timestamp column | `--withtime` |
| `--fields` | Specify output fields and order | `--fields "component,message"` |
| `--limit`, `-l` | Limit number of results | `--limit 50` |
| `--show-fields` | Show available fields and exit | `--show-fields` |

### Filter Syntax

The query tool supports flexible filtering with powerful AND/OR logic:

#### **Basic Filters**
- **General text search**: `--filter "error"` (searches in message field)
- **Field-specific search**: `--filter "component:alchemist"` (searches specific field)
- **Supported fields**: `component`, `message`, `timestamp`, `ts`

#### **NOT Filters (Exclusion)**
Three syntaxes available for excluding matching entries:
- **Function syntax**: `--filter "not(error)"` (excludes entries containing "error")
- **Keyword syntax**: `--filter "NOT warning"` (excludes entries containing "warning")
- **Exclamation syntax**: `--filter "!debug"` (excludes entries containing "debug")
- **Field-specific NOT**: `--filter "NOT component:reaper"` (excludes entries from reaper component)
- **NOT with function**: `--filter "not(component:debug_service)"` (excludes debug_service component)

#### **Logical Operators**
- **AND conditions**: `--filter "component:alchemist AND error"`
- **OR conditions**: `--filter "error OR warning"`
- **Alternative OR syntax**: `--filter "error || warning"`
- **Mixed conditions**: `--filter "component:forklift OR error"`
- **NOT with AND**: `--filter "error AND not(debug)"` (errors that don't contain "debug")
- **NOT with OR**: `--filter "NOT warning OR error"` (exclude warnings OR show errors)
- **Complex expressions**: `--filter "error AND component:alchemist OR warning"`

#### **Multiple Filter Options**
You can also use multiple `--filter` options (combined with AND logic):
```bash
# These are equivalent:
python log_query.py 1759400000 --filter "error AND component:alchemist"
python log_query.py 1759400000 --filter "error" --filter "component:alchemist"
```

#### **AND vs OR vs NOT: Key Differences**

| Operator | Behavior | Example | Result |
|----------|----------|---------|--------|
| **AND** | **Restrictive** - entries must match ALL conditions | `"component:alchemist AND error"` | Only alchemist entries that also contain "error" |
| **OR** | **Inclusive** - entries match ANY condition | `"component:alchemist OR error"` | All alchemist entries PLUS any entries containing "error" |
| **NOT** | **Exclusive** - entries must NOT match condition | `"not(error)"` | All entries that do NOT contain "error" |
| **NOT + AND** | **Restrictive exclusion** | `"component:alchemist AND not(debug)"` | Only alchemist entries that do NOT contain "debug" |
| **NOT + OR** | **Inclusive exclusion** | `"NOT warning OR error"` | Exclude warnings OR show errors (mixed logic) |

```bash
# AND Example (restrictive)
python log_query.py 1759400000 --filter "component:alchemist AND error"
# ✅ alchemist component + error message
# ❌ alchemist component + info message  
# ❌ forklift component + error message

# OR Example (inclusive)  
python log_query.py 1759400000 --filter "component:alchemist OR error"
# ✅ alchemist component + error message
# ✅ alchemist component + info message
# ✅ forklift component + error message
# ❌ forklift component + info message

# NOT Example (exclusion)
python log_query.py 1759400000 --filter "not(debug)"
# ✅ any component + error message
# ✅ any component + info message
# ❌ any component + debug message

# NOT + AND Example (restrictive exclusion)
python log_query.py 1759400000 --filter "component:alchemist AND not(debug)"
# ✅ alchemist component + error message
# ✅ alchemist component + info message
# ❌ alchemist component + debug message
# ❌ forklift component + any message
```

### Output Formats

The tool provides flexible output formatting:

```bash
# Default output: timestamp, component, message
python log_query.py 1759400000

# With UNIX timestamp
python log_query.py 1759400000 --withtime
# Output: timestamp, ts, component, message

# Custom fields only
python log_query.py 1759400000 --fields "component,message"
# Output: component, message
```

### Example Query Sessions

```bash
# Find all error messages in the last 10 minutes around a specific time
python log_query.py "2025-10-02T06:11:20" --range 600 --filter "error"

# Check what the alchemist component was doing at a specific time
python log_query.py 1759400000 --filter "component:alchemist" --limit 20

# Find either errors OR warnings (inclusive)
python log_query.py 1759400000 --filter "error OR warning" --limit 15

# Find messages from either alchemist OR forklift components
python log_query.py 1759400000 --filter "component:alchemist OR component:forklift" --range 300

# Find alchemist errors specifically (restrictive AND)
python log_query.py 1759400000 --filter "component:alchemist AND error" --withtime

# Mixed conditions: forklift messages OR any error messages
python log_query.py 1759400000 --filter "component:forklift OR error" --limit 10

# Complex filter: errors from alchemist OR any warning messages
python log_query.py 1759400000 --filter "error AND component:alchemist OR warning"

# Exclude debug messages to focus on important events
python log_query.py 1759400000 --filter "not(debug)" --limit 20

# Find errors but exclude known network warnings
python log_query.py 1759400000 --filter "error AND not(network)" --range 300

# Get alchemist messages but exclude info-level logs
python log_query.py 1759400000 --filter "component:alchemist AND !info" --withtime

# Find any errors OR warnings, but exclude debug entries
python log_query.py 1759400000 --filter "(error OR warning) AND not(debug)" --limit 15

# Exclude specific components from analysis
python log_query.py 1759400000 --filter "NOT component:debug_service" --range 600

# Get a clean view of just component and message for troubleshooting
python log_query.py 1759400000 --fields "component,message" --range 300

# Find connection-related issues across all components
python log_query.py 1759400000 --filter "connection" --withtime --limit 15
```

### Time Format Support

The query tool accepts timestamps in multiple formats:

- **UNIX timestamp**: `1759400000`
- **ISO format**: `"2025-10-02T06:11:20"`
- **ISO with Z suffix**: `"2025-10-02T06:11:20Z"`
- **Space-separated**: `"2025-10-02 06:11:20"`

## Log File Format

The analyzer expects log files with the following characteristics:

### Supported Formats

- **Timestamp Format**: `HH:MM:SS.mmm` (e.g., `14:45:36.507`)
- **File Naming**: `[prefix - ]component_name.log` (e.g., `01 - reaper.log`, `service.log`)
- **Multi-line Support**: Continuation lines without timestamps are associated with the previous timestamp

### Example Log File

```
14:45:36.507 [info] Service starting up
14:45:36.890 [info] Connected to database successfully
14:45:37.009 [error] Connection failed to external service
Stack trace follows:
  at module.function (file.js:123)
  at another.function (other.js:456)
14:45:37.100 [info] Retrying connection...
```

## Database Schema

The analyzer creates a SQLite database with the following schema:

```sql
CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER NOT NULL,              -- Unix timestamp (integer)
    timestamp VARCHAR(50) NOT NULL,   -- ISO format datetime string (e.g. "2023-10-15T14:45:36Z")
    component VARCHAR(255) NOT NULL,  -- Component name (extracted from filename)
    message TEXT NOT NULL             -- Log message content
);

-- Indexes for performance
CREATE INDEX idx_logs_ts ON logs(ts);
CREATE INDEX idx_logs_timestamp ON logs(timestamp);
CREATE INDEX idx_logs_component ON logs(component);
CREATE INDEX idx_logs_ts_component ON logs(ts, component);
```

## Example Queries

### Using log_query.py (Recommended)

The easiest way to query your processed logs:

```bash
# Find recent error messages
python log_query.py 1759400000 --filter "error" --limit 10

# Check what a specific component was doing
python log_query.py "2025-10-02T06:11:20" --filter "component:alchemist"

# Find errors OR warnings (inclusive search)
python log_query.py 1759400000 --filter "error OR warning" --limit 15

# Find messages from multiple components
python log_query.py 1759400000 --filter "component:alchemist OR component:forklift"

# Find specific component errors (restrictive search)
python log_query.py 1759400000 --filter "component:alchemist AND error" --withtime

# Exclude debug noise to focus on important messages
python log_query.py 1759400000 --filter "not(debug)" --limit 25

# Find errors but exclude known issues
python log_query.py 1759400000 --filter "error AND NOT timeout" --range 300

# Get messages from production components only (exclude test/debug services)
python log_query.py 1759400000 --filter "NOT component:test_service AND !debug" --limit 20

# Get a clean overview around a specific time
python log_query.py 1759400000 --fields "timestamp,component,message" --range 300

# Investigate connection issues with timestamps
python log_query.py 1759400000 --filter "connection" --withtime --limit 20
```

### Direct SQLite Queries

For advanced users who prefer SQL:

```sql
-- Count entries by component
SELECT component, COUNT(*) as count 
FROM logs 
GROUP BY component 
ORDER BY count DESC;

-- Find error messages (using ISO timestamp for easier reading)
SELECT timestamp, component, message 
FROM logs 
WHERE message LIKE '%error%' 
ORDER BY ts DESC 
LIMIT 10;

-- Get logs for a specific time range
SELECT timestamp, component, message 
FROM logs 
WHERE ts BETWEEN strftime('%s', '2023-10-15 14:45:00') 
              AND strftime('%s', '2023-10-15 14:46:00')
ORDER BY ts;

-- Query using ISO timestamp (human-readable format)
SELECT timestamp, component, message 
FROM logs 
WHERE timestamp = '2023-10-15T14:45:36Z'
ORDER BY ts;

-- Query by date range using ISO timestamps
SELECT timestamp, component, message 
FROM logs 
WHERE timestamp BETWEEN '2023-10-15T14:45:00Z' AND '2023-10-15T14:46:00Z'
ORDER BY timestamp;
```

## Development

### Running Tests

The project includes a comprehensive test suite with multiple execution options:

```bash
# Run all tests with coverage
python run_tests.py

# Run only unit tests
python run_tests.py --unit

# Run only integration tests
python run_tests.py --integration

# Run quick smoke tests
python run_tests.py --quick

# Run code quality checks
python run_tests.py --quality
```

### Test Structure

```
tests/
├── __init__.py
├── fixtures/                 # Test log files
│   ├── 01 - test_component.log
│   ├── 02 - another_service.log
│   └── simple_service.log
├── test_log_analyzer.py      # Unit tests for log analyzer
├── test_log_query.py         # Unit tests for log query tool
└── test_integration.py       # Integration tests
```

### Code Coverage

The project maintains high code coverage (96%+). Coverage reports are generated in `htmlcov/` directory.

### Code Quality

The project uses:
- **pytest** for testing
- **flake8** for linting
- **black** for code formatting
- **pytest-cov** for coverage reporting

## Architecture

### Core Components

1. **log_analyzer.py**: Main log processing module
   - `setup_database()`: Database initialization and migration
   - `extract_component_name()`: Component name extraction from filenames
   - `parse_time_to_unix_timestamp()`: Timestamp parsing and conversion
   - `discover_log_files()`: Log file discovery in directories
   - `process_log_file()`: Log file parsing and database insertion
   - `main()`: CLI interface for log processing

2. **log_query.py**: Advanced log querying tool
   - `parse_timestamp()`: Flexible timestamp format parsing
   - `parse_filter_expression()`: Filter syntax parsing
   - `build_sql_query()`: Dynamic SQL query construction
   - `format_output_line()`: Flexible output formatting
   - `get_available_fields()`: Database schema introspection
   - `main()`: CLI interface for log querying

3. **Test Suite**: Comprehensive testing (62 tests total)
   - Unit tests for individual functions in both modules
   - Integration tests for end-to-end workflows
   - CLI testing with Click's test runner for both tools
   - Error handling, edge cases, and database operations

### Design Principles

- **Modularity**: Each function has a single responsibility
- **Error Handling**: Graceful handling of malformed data
- **Performance**: Efficient database operations with proper indexing
- **Usability**: Clear CLI interface with helpful messages
- **Maintainability**: Well-documented code with comprehensive tests

## Performance

The analyzer efficiently processes large log files:

- **Throughput**: ~100,000 log entries per second (typical)
- **Memory Usage**: Minimal memory footprint using streaming processing
- **Database**: Optimized with proper indexes for fast queries
- **Progress Tracking**: Real-time feedback during processing

### Example Performance

```
Processing 4 log files with 695,517 total entries:
- reaper: 13,822 entries
- alchemist: 383,297 entries  
- valkyrie: 149,598 entries
- forklift: 148,800 entries

Completed in ~8 seconds
```

## Troubleshooting

### Common Issues

#### Log Processing (`log_analyzer.py`)

1. **No log files found**
   - Ensure `*.log` files exist in the specified directory
   - Check file permissions

2. **Database locked errors**
   - Ensure no other processes are accessing the database
   - Use different database files for concurrent processing

3. **Invalid timestamp formats**
   - Verify log timestamps follow the `HH:MM:SS.mmm` format
   - Check for timezone-related issues

4. **Memory issues with large files**
   - The analyzer uses streaming processing, but ensure sufficient disk space
   - Consider processing smaller batches of files

#### Log Querying (`log_query.py`)

1. **"Database file not found" errors**
   - Ensure the database file exists (run `log_analyzer.py` first)
   - Check the correct path with `--database` option

2. **"No matching log entries found"**
   - Verify the timestamp is within the data range
   - Try increasing the time range with `--range`
   - Check available data with `--show-fields`

3. **"Invalid fields" errors**
   - Use `--show-fields` to see available database fields
   - Ensure field names in `--fields` match exactly

4. **Invalid timestamp format errors**
   - Use UNIX timestamp: `1759400000`
   - Or ISO format: `"2025-10-02T06:11:20"`
   - Ensure quotes around ISO format timestamps

### Debug Mode

For debugging, you can examine the database directly:

```bash
sqlite3 logs.db
.tables
.schema logs
SELECT COUNT(*) FROM logs;
SELECT MIN(ts), MAX(ts), MIN(timestamp), MAX(timestamp) FROM logs;
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass: `python run_tests.py`
6. Submit a pull request

### Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd ride_logs

# Set up development environment
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements-test.txt

# Run tests
python run_tests.py
```

## License

This project is provided as-is for educational and analysis purposes.

## Original Specification

See [spec.md](spec.md) for the original project requirements and implementation details.

---

**Created**: 2023-10-02  
**Language**: Python 3.8+  
**Tools**: log_analyzer.py (log processing), log_query.py (log querying)  
**Dependencies**: click, tqdm, sqlite3 (built-in)  
**Test Coverage**: 96% (62 tests total)
