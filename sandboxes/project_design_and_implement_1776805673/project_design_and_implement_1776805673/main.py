import json
import data_manager
import name_generator
import os

def main():
    """
    Main execution function for the Planet Explorer application.
    Orchestrates the data loading, generation, and persistence process.
    """
    print("--- Planet Explorer Application Initializing ---")

    # 1. Initialize Data Repository
    data_repo = data_manager.DataRepository()

    # 2. Load existing data (or initialize new)
    data_repo.load_data()
    print("Data loaded successfully.")

    # --- Demonstration of Data Management ---
    
    # 3. Generate a new planet name using the generator module
    initial_planet_name = name_generator.generate_planet_name(
        theme="Andromeda", seed="A1"
    )
    print(f"\n[INFO] Generated new planet name: {initial_planet_name}")

    # 4. Simulate saving new data
    new_data_entry = {
        "planet_name": initial_planet_name,
        "status": "discovered",
        "orbital_period": 100
    }
    
    # In a real application, this data would be saved.
    # For this demonstration, we will explicitly call save.
    data_repo.save_data(new_data_entry)
    print(f"\n[INFO] Data entry saved: {initial_planet_name}")
    
    # Verify persistence (optional, but good for demonstration)
    print("\n--- Verification ---")
    data_repo.load_data()
    print(f"Verification successful. Current planet name: {data_repo.data.get('planet_name')}")
    
    print("\n--- Application Finished ---")

if __name__ == "__main__":
    main()