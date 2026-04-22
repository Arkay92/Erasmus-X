import json
import os

class DataManager:
    """Handles loading and saving planetary data using JSON."""

    def __init__(self, filename="planetary_data.json"):
        self.filename = filename

    def save_data(self, data_dict: dict):
        """Saves the planetary data dictionary to a JSON file."""
        try:
            with open(self.filename, 'w') as f:
                json.dump(data_dict, f, indent=4)
            print(f"Data successfully saved to {self.filename}")
        except IOError:
            print(f"Error: Could not write to {self.filename}")

    def load_data(self, filename: str) -> dict:
        """Loads planetary data from a JSON file."""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                return data
        except FileNotFoundError:
            print(f"Error: File not found at {filename}. Returning empty data.")
            return {}
        except json.JSONDecodeError:
            print(f"Error: File {filename} is empty or invalid JSON.")
            return {}
