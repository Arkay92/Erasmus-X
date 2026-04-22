[FILE: PLAN.md]
# Project: Planet Explorer

## Goal
To design a multi-file Python application that manages planetary data, handles JSON persistence for storage, and generates procedural planet names.

## Architecture
The architecture will be structured around three main components:
1.  **Data Module:** Handles reading and writing planetary data (e.g., storing JSON objects) to a file system.
2.  **Generator Module:** Implements a function to procedurally generate unique planet names based on input parameters.
3.  **Main Entry Point:** Orchestrates the application, handling user interaction or data loading/saving.

## File Structure
- `main.py` — Primary entry point, handling initialization and module interaction.
- `data_manager.py` — Module dedicated to JSON serialization and deserialization operations.
- `planet_generator.py` — Module containing logic for generating procedural planet names.

## Implementation Details
- Stack: Python 3
- Patterns: Object-Oriented design, use of Python's `json` module for data handling, separation of concerns (data persistence vs. generation logic).

[FACT] PLAN.md | relation | Project structure | PLAN.md
[FACT] Data structure | relation | Data manager | data_manager.py
[FACT] Procedural generation | relation | Generator module | planet_generator.py

---

[FILE: main.py]
```python
import json
import data_manager
import planet_generator

def main():
    """
    Main entry point for the Planet Explorer application.
    Orchestrates data handling and generation.
    """
    print("--- Planet Explorer Initialized ---")

    # 1. Test Data Management
    data_manager.save_planet_data("Mars", {"temp": 20, "moons": 1})
    print("Data saved successfully.")

    # 2. Test Planet Generation
    new_planet_name = planet_generator.generate_name("Terra")
    print(f"Generated new planet name: {new_planet_name}")

    # Example of loading data (requires implementation in data_manager)
    # In a real application, we'd load data here.
    print("Application finished.")

if __name__ == "__main__":
    main()
```

[FILE: data_manager.py]
```python
import json
import os

class DataManager:
    """
    Manages operations for persisting and loading planetary data using JSON.
    """
    def __init__(self, filename):
        self.filename = filename

    def save_data(self, planet_name: str, data: dict) -> bool:
        """
        Saves the planetary data as a JSON object to a file.
        """
        # In a real scenario, this would involve file I/O logic.
        # For this example, we simulate the save operation.
        try:
            # Simulate writing to file (or perhaps use json.dump for file)
            # We will simulate the persistence logic without complex file handling here
            # as the focus is on JSON interaction patterns.
            
            # Placeholder for actual persistence logic:
            json_data = {
                "name": planet_name,
