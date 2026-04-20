import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# 1. Create a mock dataset for global temperature changes
np.random.seed(42)
years = np.arange(1950, 2024, 10)
# Simulate temperature data (e.g., starting around 14°C and increasing)
temp_data = 14 + np.cumsum(np.random.randn(len(years)) * 0.5)

# Create a DataFrame
data = pd.DataFrame({
    'Year': years,
    'Temperature_C': temp_data
})

# 2. Data Visualization Script
def visualize_temperature_data(df):
    """Generates a plot showing the trend of global temperature over time."""
    plt.figure(figsize=(10, 6))
    
    # Plot the temperature trend
    plt.plot(df['Year'], df['Temperature_C'], marker='o', linestyle='-', color='red')
    
    # Add labels and title
    plt.title('Mock Global Temperature Trend Over Time')
    plt.xlabel('Year')
    plt.ylabel('Temperature (°C)')
    plt.grid(True)
    
    # Add annotations for context
    for i in range(len(df)):
        plt.annotate(f"{df['Temperature_C'].iloc[i]:.1f}°C", 
                     (df['Year'].iloc[i], df['Temperature_C'].iloc[i]),
                     alpha=0.5,
                     fontsize=8)

    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    print("--- Generating Mock Data ---")
    print(data.head())
    
    print("\n--- Visualizing Data ---")
    visualize_temperature_data(data)