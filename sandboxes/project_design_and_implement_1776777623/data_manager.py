import json
import os

class DataManager:
    """
    Manages interactions with planetary data, handling JSON persistence.
    """
    def __init__(self, filename):
        self.filename = filename

    def load_data(self, filename):
        """
        Loads data from the specified JSON file.
        """
        try:
            with open(self.filename, 'r') as f:
                data = json.load(f)
                print(f"Successfully loaded data from {self.filename}")
                return data
        except FileNotFoundError:
            print(f"Error: File {self.filename} not found.")
            return {}
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {self.filename}.")
            return {}

    def save_data(self, data):
        """
        Saves data to the specified JSON file.
        """
        try:
            with open(self.filename, 'w') as f:
                json.dump(data, f, indent=4)
                print(f"Data successfully saved to {self.filename}")
        except IOError:
            print(f"Error: Could not write to {self.filename}.")

# Example usage simulation (not strictly necessary for runnable structure, but useful for context)
if __name__ == '__main__':
    # Test loading/saving functionality
    manager = DataManager("config.json")
    
    # Simulate loading (will fail if file doesn't exist, but structure is valid)
    data = manager.load_data("config.json")
    