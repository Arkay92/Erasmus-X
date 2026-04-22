# Project: Planet Explorer

## Goal
To create a multi-file Python application that manages planetary data, handles procedural generation for planet names, and persists data using JSON for storage.

## Architecture
The application will follow a modular structure:
1.  **Data Module:** Handles all interactions with planetary data, including loading and saving data to a JSON file.
2.  **Generator Module:** Contains logic for generating unique, procedural planet names based on input parameters.
3.  **Main Entry Point:** Orchestrates the usage of the modules, handles user interaction, and manages the data flow.

## File Structure
- main.py — Primary entry point, handles user interaction and module interaction.
- data_manager.py — Module for handling JSON persistence operations.
- name_generator.py — Module for procedural planet name generation logic.
- config.json — Configuration file for settings (e.g., initial planet data).