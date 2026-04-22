import math

def gcd_euclidean(a: int, b: int) -> int:
    """
    Calculates the Greatest Common Divisor (GCD) of two non-negative integers
    using the Euclidean algorithm.

    Args:
        a: The first integer.
        b: The second integer.

    Returns:
        The GCD of a and b.
    """
    # Handle cases where inputs might be negative, though GCD is usually defined for positive integers.
    # We use the absolute values for the calculation.
    if a < 0 or b < 0:
        # For robustness, we can handle the absolute values
        a = abs(a)
        b = abs(b)

    # Euclidean Algorithm implementation
    while b != 0:
        # The remainder of the division of a by b is the new b
        a, b = b, a % b
    
    # When b is 0, the GCD is the current value of a (which is gcd(a, 0) = a)