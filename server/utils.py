import json
import os
from pathlib import Path
from typing import List, Dict

import aiofiles

from models import EventCreate


async def load_events_from_file(file_path: str) -> List[Dict]:
    """Download from JSON file"""
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            events = json.loads(content)
            return events
    except FileNotFoundError:
        print(f"File {file_path} not found")
        return []
    except json.JSONDecodeError:
        print(f"Bad parsing JSON from file {file_path}")
        return []


async def process_events_file(server_file_path: str):
    """Handle events file: create dir, download data"""
    await ensure_data_directory()
    
    # Check if file exists
    if not os.path.exists(server_file_path):
        raise FileNotFoundError(f"File {server_file_path} not found at server")
    
    # Download events from file
    events_data = await load_events_from_file(server_file_path)
    
    # Convert to Pydantic models for validation
    validated_events = []
    for event_data in events_data:
        try:
            event = EventCreate(**event_data)
            validated_events.append(event)
        except Exception as e:
            print(f"Error of events validation: {e}")
    
    return validated_events