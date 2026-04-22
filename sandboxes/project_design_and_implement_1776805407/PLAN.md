# Project: Planet Explorer

## Goal
To create a multi-file Python application that manages planetary data, handles JSON persistence for data storage, and generates procedural planet names.

## Architecture
The application will be structured using Python principles, separating concerns:
1. **Data Module:** Handles loading and saving planetary data to a JSON file structure.
2. **Generator Module:** Contains logic for generating procedural planet names based on input parameters.
3. **Main Entry Point:** Orchestrates the application, interacting with the Data Module and Generator.
Data flow will be sequential: Input -> Data Module (Save/Load) -> Generator -> Output/Display.

## File Structure
- main.py — Entry point for application logic and execution.
- data_manager.py — Handles all interactions with JSON data persistence.
- planet_generator.py — Contains the logic for procedural planet name generation.
- data.json — Data storage file (will be created/managed by data_manager).