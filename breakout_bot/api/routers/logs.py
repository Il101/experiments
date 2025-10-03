"""
Logs router
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import os
import json
from pathlib import Path

router = APIRouter()

class LogEntry(BaseModel):
    id: str
    timestamp: str
    level: str
    component: str
    message: str
    data: Optional[Dict[str, Any]] = None


@router.get("", response_model=List[LogEntry])
async def get_logs(
    level: Optional[str] = Query(None, description="Filter by log level"),
    component: Optional[str] = Query(None, description="Filter by component"),
    limit: int = Query(100, description="Number of logs to return")
):
    """Get system logs from log files"""
    try:
        logs = []
        log_dir = Path("logs")
        
        # Check if logs directory exists
        if not log_dir.exists():
            return []
        
        # Read from main log files
        log_files = [
            ("engine.log", "engine"),
            ("api.log", "api"),
            ("metrics.log", "metrics")
        ]
        
        all_entries = []
        
        for log_file, default_component in log_files:
            file_path = log_dir / log_file
            if file_path.exists() and file_path.is_file():
                try:
                    with open(file_path, 'r') as f:
                        lines = f.readlines()
                        # Get last N lines if file is too big
                        if len(lines) > limit * 2:  # Read more to allow filtering
                            lines = lines[-(limit * 2):]
                        
                        for i, line in enumerate(lines):
                            line = line.strip()
                            if not line:
                                continue
                            
                            # Try to parse as JSON first (structured logs)
                            try:
                                data = json.loads(line)
                                entry = LogEntry(
                                    id=f"{log_file}_{i}",
                                    timestamp=data.get('timestamp', datetime.now().isoformat()),
                                    level=data.get('level', 'INFO'),
                                    component=data.get('component', default_component),
                                    message=data.get('message', line),
                                    data=data.get('data')
                                )
                            except json.JSONDecodeError:
                                # Parse as regular log line
                                # Format: YYYY-MM-DD HH:MM:SS,mmm - component.module - LEVEL - message
                                parts = line.split(' - ', 3)
                                if len(parts) >= 4:
                                    timestamp_str = parts[0]
                                    component_part = parts[1]  
                                    level_part = parts[2]
                                    message_part = parts[3]
                                else:
                                    timestamp_str = datetime.now().isoformat()
                                    component_part = default_component
                                    level_part = "INFO"
                                    message_part = line
                                
                                entry = LogEntry(
                                    id=f"{log_file}_{i}",
                                    timestamp=timestamp_str,
                                    level=level_part,
                                    component=component_part.split('.')[0],  # Take first part
                                    message=message_part,
                                    data=None
                                )
                            
                            all_entries.append(entry)
                            
                except Exception as e:
                    # Skip files that can't be read
                    continue
        
        # Sort by timestamp (newest first)
        all_entries.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Apply filters
        filtered_entries = all_entries
        
        if level:
            filtered_entries = [e for e in filtered_entries if e.level.upper() == level.upper()]
        
        if component:
            filtered_entries = [e for e in filtered_entries if component.lower() in e.component.lower()]
        
        # Apply limit
        filtered_entries = filtered_entries[:limit]
        
        return filtered_entries
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")