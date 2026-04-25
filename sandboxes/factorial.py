import sys

def calculate_factorial(n: int) -> int:
    """Calculates the factorial of a non-negative integer."""
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers.")
    if n == 0:
        return 1
    else:
        result = 1
        for i in range(1, n + 1):
            result *= i
        return result

if __name__ == "__main__":
    try:
        # Read input from standard input
        input_str = sys.stdin.read().strip()
        if not input_str:
            print("Error: No input provided.")
            sys.exit(1)

        # Attempt to parse the input
        number = int(input_str)
        
        # Calculate and print the result
        factorial_result = calculate_factorial(number)
        print(f"The factorial of {number} is: {factorial_result}")

    except ValueError as e:
        print(f"Error: Invalid input provided: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)