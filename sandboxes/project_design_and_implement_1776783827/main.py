import json
import data_manager
import planet_generator

def main():
    """Main function to run the Planet Explorer application."""
    print("--- Planet Explorer Initializing ---")

    # 1. Test Data Generation
    generator = planet_generator.PlanetGenerator()
    print(f"Generated planet name: {generator.generate_name('Mars')}")

    # 2. Data Management Test
    data_manager.DataManager()
    print("Data manager initialized.")

    # Example of loading/saving (simplified)
    # Note: In a real application, file handling would be more robust.
    try:
        data = data_manager.load_data('saved_data.json')
        print(f"Successfully loaded data: {data}")
    except FileNotFoundError:
        print("Data file not found, starting fresh.")
        
    # Example usage of the generator
    print(f"Generated new planet name: {generator.generate_name('Venus')}")

if __name__ == "__main__":
    main()