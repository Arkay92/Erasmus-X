import json
import data_manager
import planet_generator
import sys

def main():
    """
    Main entry point for the Planet Explorer application.
    Orchestrates data handling and generation.
    """
    print("--- Planet Explorer Initialized ---")

    # 1. Test Data Management: Save data
    try:
        # Test saving data
        data_manager.save_planet_data("Mars", {"temp": 20, "moons": 1})
        print("Successfully saved planetary data for Mars.")
    except Exception as e:
        print(f"Error during data save: {e}")

    # 2. Test Planet Generation: Generate a new planet name
    try:
        new_planet_name = planet_generator.generate_name("Terra")
        print(f"Successfully generated new planet name: {new_planet_name}")
    except Exception as e:
        print(f"Error during planet generation: {e}")

    # Example of loading data (simulated)
    # In a real application, we'd load data here.
    print("\nApplication finished execution.")

if __name__ == "__main__":
    # Defensive check: Ensure the script runs cleanly
    try:
        main()
    except Exception as e:
        print(f"Fatal error encountered: {e}")