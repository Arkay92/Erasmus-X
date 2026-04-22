# Project: Planet Explorer

## Goal
To create a multi-file Python application capable of managing planetary data, persisting that data via JSON, and generating procedural planet names.

## Architecture
The project will follow a modular structure.
1. **data_manager.py**: Handles all interactions with planetary data, responsible for loading and saving data to a JSON file system.
2. **generator.py**: Contains logic for generating random, procedural planet names based on input parameters.
3. **main.py**: Serves as the entry point, orchestrating data loading, generation, and interaction, managing the application flow.

## File Structure
- main.py — Entry point, handles program flow and data interaction.
- data_manager.py — Module for JSON persistence operations.
- generator.py — Module for procedural planet name generation logic.
- planet_data.json — Data storage file (will be created/managed by data_manager).