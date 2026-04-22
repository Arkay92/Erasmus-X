import json
import data_manager

def main():
    """
    Main entry point for the Planet Explorer application.
    Orchestrates data loading, generation, and user interaction.
    """
    print("--- Planet Explorer Application ---")

    # 1. Load initial data (simulated)
    # DataManager handles the file operations
    data_manager = data_manager.DataManager("planets.json")
    data_manager.load_data() 
    print("Data loaded successfully.")

    # 2. Generate a new planet name
    generator = generator.PlanetGenerator()
    new_name = generator.generate_planet_name()
    print(f"Generated new planet name: {new_name}")

    # 3. Display current status
    print("\nApplication finished.")

if __name__ == "__main__":
    main()