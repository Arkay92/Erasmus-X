import json
import data_manager
import name_generator

def main():
    """
    Main function to run the Planet Explorer application.
    Orchestrates data loading, name generation, and saving.
    """
    print("--- Planet Explorer Application ---")

    # 1. Initialize Data Manager (ensures file existence check)
    data_manager.initialize_data()

    # 2. Load existing data
    data = data_manager.load_data()
    print(f"Loaded existing data: {data}")

    # 3. Generate a new planet name
    new_name = name_generator.generate_planet_name(data)
    print(f"Generated new planet name: {new_name}")

    # 4. Save the new data
    data_manager.save_data(data)
    print("Data saved successfully.")

    # Example interaction simulation
    print("\n--- Simulation Complete ---")

if __name__ == "__main__":
    main()