def convert_f_to_c(fahrenheit):
    """Converts a temperature from Fahrenheit to Celsius."""
    # Formula: C = (F - 32) / 1.7
    celsius = (fahrenheit - 32) / 1.7
    return celsius

if __name__ == "__main__":
    fahrenheit_temp = 100
    result = convert_f_to_c(fahrenheit_temp)
    print(f"{fahrenheit_temp} degrees Fahrenheit is {result:.2f} Celsius.")