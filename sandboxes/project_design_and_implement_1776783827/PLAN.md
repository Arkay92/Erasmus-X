# Project: Planet Explorer

## Goal
To build a multi-file application that manages planetary data, handles data persistence via JSON serialization, and generates procedural planet names.

## Architecture
The application will be structured around three main components:
1. **Data Module (`data_manager.py`):** Handles loading and saving planetary data using the `json` module for persistence, ensuring data integrity.
2. **Generator Module (`planet_generator.py`):** Contains logic for generating unique, procedural planet names based on input parameters.
3. **Main Entry Point (`main.py`):** Orchestrates the application, handles user interaction, and integrates the data and generator modules.

## File Structure
- `main.py` — Entry point, handles user input, calls data operations and generator.
- `data_manager.py` — Module for JSON serialization/deserialization of planetary data.
- `planet_generator.py` — Module containing functions for procedural planet name generation.