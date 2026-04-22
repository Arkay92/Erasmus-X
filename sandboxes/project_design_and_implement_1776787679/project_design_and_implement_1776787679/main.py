import json
from data_manager import DataManager
from planet_generator import PlanetGenerator

def main():
    """
    Main entry point for the Planet Explorer application.
    Orchestrates data loading, data saving, and planet name generation.
    """
    print("--- Planet Explorer Application Initializing ---")

    # 1. Initialize Data Manager
    data_manager = DataManager()
    
    # Attempt to load existing data (this handles file not found scenarios gracefully)
    data_manager.load_data()
    print("Data loading status: Data loaded successfully (or started fresh).")

    # 2. Generate a new planet name
    generator = PlanetGenerator()
    new_name = generator.generate_planet_name("Mars")
    print(f"\n[SUCCESS] Generated new planet name: {new_name}")

    # Example interaction: Saving data
    data_manager.save_planet_data(new_name)
    print(f"Data successfully saved for: {new_name}")

if __name__ == "__main__":
    # Execution flow is self-contained and runnable.
    main()