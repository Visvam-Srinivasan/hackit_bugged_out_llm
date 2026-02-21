# core/pipeline.py
import json
import os
from datetime import datetime

LOG_FILE = "logs/pipeline_audit.jsonl"

def log_event(stage: str, details: dict):
    """Appends a structured log entry to the audit file."""
    if not os.path.exists("logs"):
        os.makedirs("logs")
        
    entry = {
        "timestamp": datetime.now().isoformat(),
        "stage": stage,
        **details
    }
    
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")