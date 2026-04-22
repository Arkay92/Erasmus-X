import json
import data_manager
import name_generator

def main():
    """
    Main function to run the Planet Explorer application.
    Orchestrates data loading and name generation.
    """
    print("--- Planet Explorer Initializing ---")

    # 1. Initialize Data Manager (loads configuration)
    data_manager.DataManager("config.json")
    print("Data loaded successfully.")

    # 2. Generate a new planet name using the current data state
    current_data = data_manager.DataManager.get_current_planet_data()
    if current_data:
        new_name = name_generator.generate_planet_name(current_data)
        print(f"Generated new planet name: {new_name}")
    else:
        print("Warning: No data found for generation.")

    # 3. Display status
    print("\n--- Application Run Complete ---")

if __name__ == "__main__":
    # Ensure the DataManager class is accessible for testing
    # Note: In a real application, we would load config here.
    # For this structure, we simulate the interaction.
    try:
        data_manager.DataManager("config.json")
    except Exception as e:
        print(f"Error during initialization: {e}")