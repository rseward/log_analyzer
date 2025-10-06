# log_query

Implement an easy to use log query tool to pull information from logs.db
databases compiled by the analyzer.

log_query.py

The python script shall:
- use the uv command for managing python deps as necessary
- use the click module for CLI args
- use the tqdm module to display progress info
- Allow the user to specify a timestamp either a UNIX timestamp integer or
  an ISO formatted timestring (without timezone)
- Allow the user to specify an amount of time in seconds to display before
  and after the specified timestamp above. The default number of seconds shall be 120 seconds.
- Additionally allow optional filter strings to be anded and ored together in 
  a manner similar to the UNIX find command
- All matching log messages that match these conditions will be returned
  in the closest time order in which the log statements were generated.
- The script will output matching lines as follows by default:
  - timestamp field
  - component
  - message
- Alternatively the user may specify the "--withtime" option, which will also display the ts column after the timestamp field.
- Alternatively the user can specify the fields to return and their column order in a manner similar to the docker command.


# log_analyzer

Implement a Kubernetes log analyzer for a micro service architecture application.

Call the script log_analyzer.py

The python script shall:
  - use the click module for CLI args
  - use the tqdm module to provide progress information while processing.
  - store log messages into a sqlite3 database
  - Have a log table with the following fields:  ts (unix timestamp), component (varchar), message (long string). The log table records should be indexed by ts and component fields
  - The script will analyze and process log messages found in *.log files in the directory.
  - The component field will be set based on the name of the log file. Strip the prefix like  "01 - " and the extension ".log" from the component name
  - When the script finds a string that looks a timestamp. Eg. 14:45:36.507 it will interpret the string into a UNIX Timestamp assuming the date is today (or a value specified in the CLI).
  - Further lines will be associated with that timestamp, until the next time stamp string is found at the start of a log line.
  - The script will write each log line into the log table.
  
  Implement repeatable unit tests for the project.
  