def gcd_euclidean(a, b):
    """
    Calculates the Greatest Common Divisor (GCD) of two non-negative integers 
    using the Euclidean algorithm.
    """
    # Ensure inputs are non-negative for standard GCD calculation
    if a < 0 or b < 0:
        # Handle error or raise an exception if inputs are strictly required to be non-negative
        # For this implementation, we'll proceed assuming inputs are non-negative
        pass

    # The Euclidean algorithm: GCD(a, b) = GCD(b, a % b)
    while b != 0:
        # Update the values: the new 'a' becomes the old 'b', and the new 'b' becomes the remainder (a % b)
        a, b = b, a % b
    
    # When b is 0, the GCD is the value currently held in 'a'
    return a

# Example usage (optional, but useful for testing)
# print(gcd_euclidean(48, 12)) # Should return 12
# print(gcd_euclidean(17, 39)) # Should return 1)