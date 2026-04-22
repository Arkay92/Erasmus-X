import json
import os
import sys

# Define the persistent file path
DATA_FILENAME = "data.json"

def main():
    """
    Main function to run the Planet Explorer application.
    Orchestrates data loading and name generation.
    """
    print("--- Initializing Planet Explorer ---")

    # 1. Initialize Data Manager
    data_manager = data_manager.DataHandler(DATA_FILENAME)

    # 2. Load existing data (or create a new structure)
    print(f"Attempting to load data from: {DATA_FILENAME}")
    loaded_data = data_manager.load_data(DATA_FILENAME)

    # 3. Generate a new planet name using the generator
    generator = name_generator.NameGenerator()
    new_planet = generator.generate_name()

    print(f"\nSuccessfully loaded data.")
    print(f"Generated new planet name: {new_planet}")

    # 4. Save the generated name back to persist
    data_manager.save_data(new_planet)
    print("Data saved successfully.")

if __name__ == "__main__":
    # Ensure the script is runnable and handles execution flow
    try:
        main()
    except Exception as e:
        print(f"\n[FATAL ERROR]: An unhandled exception occurred: {e}", file=sys.stderr)
        # Defensive handling: ensures the program doesn't silently fail
        sys.exit(1)