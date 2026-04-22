import json
from data_manager import DataManager
from planet_generator import PlanetGenerator

def main():
    """
    Main function to orchestrate the Planet Explorer application.
    Demonstrates loading data, generating a new planet name, and saving it.
    """
    print("--- Planet Explorer Application ---")

    # 1. Initialize Data Manager
    data_manager = DataManager()
    
    # 2. Initialize Generator
    generator = PlanetGenerator()

    # --- Simulation Setup ---
    # Create a dummy data structure to load/save
    initial_data = {
        "planet_id": "TerraNova",
        "temp": 300,
        "status": "Explored"
    }
    
    # Attempt to load existing data (will fail if file doesn't exist, handled by DataManager)
    try:
        data = data_manager.load_data()
        print(f"Loaded existing data: {data}")

        # Generate a new planet name based on existing ID
        print("\n--- Generating New Planet ---")
        new_name = generator.generate_name(data.get("planet_id"))
        print(f"Generated new planet name: {new_name}")

        # Save the updated data
        data_manager.save_data(data)
        print(f"Data saved successfully for planet: {data.get('planet_id')}")

    except Exception as e:
        print(f"An error occurred during execution: {e}")

if __name__ == "__main__":
    main()