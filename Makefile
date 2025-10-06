logs.db:
	uv run log_analyzer.py
	
query:	logs.db
	litecli logs.db
	 