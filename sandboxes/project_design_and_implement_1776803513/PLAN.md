# Project: Planet Explorer

## Goal
To develop a multi-file application that generates procedural planet names, manages planetary data using JSON persistence, and handles data retrieval.

## Architecture
The application will be structured around three core components:
1. **Data Module:** Handles reading and writing planetary data (JSON persistence).
2. **Generator Module:** Generates procedural planet names based on input parameters.
3. **Main Entry Point:** Orchestrates the logic, handles data loading, and interacts with the user.

## File Structure
- planet_data.py — Module for handling JSON serialization and persistence operations.
- name_generator.py — Module for generating procedural planet names.
- main.py — The primary entry point, responsible for application flow and interaction.