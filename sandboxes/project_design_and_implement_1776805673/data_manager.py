import json
from typing import Dict, Any

class DataRepository:
    """
    Handles persistence operations for planetary data using JSON files.
    """
    def __init__(self, file_name: str = "planets.json"):
        self.file_name = file_name
        self.data: Dict[str, Any] = {}

    def load_data(self):
        """Loads data from the JSON file."""
        try:
            with open(self.file_name, 'r') as f:
                content = json.load(f)
                self.data = content
                print(f"Data successfully loaded from {self.file_name}.")
        except FileNotFoundError:
            self.data = {}
            print(f"Data file {self.file_name} not found. Initializing empty data.")

    def save_data(self):
        """Saves the current data dictionary to the JSON file."""