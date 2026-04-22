import json
import os
from typing import Dict, Any

# Constant for the file name
DATA_FILE = "planet_data.json"

def initialize_data() -> Dict[str, Any]:
    """
    Initializes a new, empty dataset structure.
    Returns an empty dictionary representing the starting state.
    """
    print("Initializing new dataset structure.")
    return {}

def load_data() -> Dict[str, Any]:
    """
    Loads planetary data from the file system.
    Handles file existence and JSON parsing.
    """
    if not os.path.exists(DATA_FILE):
        print(f"Data file '{DATA_FILE}' does not exist. Returning empty data.")
        return {}
    
    try:
        # Attempt to read the file content
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Should be caught by the check above, but included for robustness
        return {}
    except json.JSONDecodeError:
        # Handle case where file exists but is invalid JSON
        print(f"Warning: File {DATA_FILE} is empty or invalid JSON.")
        return {}


def save_data(data: Dict[str, Any]) -> bool:
    """
    Saves the planetary data dictionary to the file, ensuring strict JSON formatting.
    """
    try:
        # Ensure we write the data back to the file
        with open(DATA_FILE, 'w') as f:
            # Use json.dump for writing the dictionary
            json.dump(data, f, indent=4)
            return True
        
    except IOError as e:
        # Defensive handling for file writing errors
        print(f"Critical Error: Could not write data to {DATA_FILE}. Error: {e}")
        return False