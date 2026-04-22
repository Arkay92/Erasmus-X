import json
import os
from typing import Dict, Any

class DataManager:
    """
    Manages loading and saving planetary data using JSON files.
    Ensures data persistence and robust file handling.
    """
    def __init__(self, filename: str):
        """Initialize the DataManager with a specific file name."""
        self.filename = filename

    def load_data(self) -> Dict[str, Any]:
        """
        Loads data from the specified JSON file. Handles file existence checks.
        """
        if not os.path.exists(self.filename):
            print(f"INFO: File {self.filename} does not exist. Creating a new file structure.")
            data = {}
            self.save_data(data)
            return data
        
        try:
            with open(self.filename, 'r') as f:
                # Use json.load for reading
                return json.load(f)
        except FileNotFoundError:
            # This path is redundant if the check above passes, but good for safety
            print(f"ERROR: File {self.filename} was not found.")
            return {}

    def save_data(self, data: Dict[str, Any]):
        """
        Saves the provided data dictionary to the JSON file, ensuring proper writing.
        """
        try:
            # Ensure the directory exists before writing (in a real scenario, we'd handle paths)
            with open(self.filename, 'w') as f:
                # Use json.dump for writing
                json.dump(data, f, indent=4)
        except IOError as e:
            # Defensive design: handle file write errors gracefully
            print(f"CRITICAL ERROR: Failed to write data to {self.filename}. Details: {e}")
            # Return an empty structure or raise an exception if strict adherence is needed
            raise IOError(f"Data write failure for {self.filename}")
            
# Example usage logic (