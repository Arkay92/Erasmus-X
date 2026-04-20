def gcd_euclidean(a, b):
    """
    Calculates the Greatest Common Divisor (GCD) of two non-negative integers 
    using the Euclidean algorithm.
    """
    # The Euclidean algorithm requires non-negative inputs for standard GCD definition.
    if a < 0 or b < 0:
        raise ValueError("Inputs must be non-negative for standard Euclidean GCD calculation.")
        
    # Handle the case where one input is zero (GCD(x, 0) = x)
    if b == 0:
        return a
    
    # Euclidean Algorithm implementation
    while b != 0:
        remainder = a % b
        a = b
        b = remainder
        
    return a

# Example usage (optional, but useful for testing)
# print(gcd_euclidean(48, 12)) # Should return 12