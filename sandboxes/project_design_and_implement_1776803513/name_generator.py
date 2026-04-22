import random

def generate_planet_name(prefix: str, length: int = 10) -> str:
    """Generates a procedural planet name based on a prefix and length."""
    """
    Generates a procedural planet name based on a prefix and length.
    """
    # Example: Generate a random alphanumeric string
    name_chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
    
    # Generate a random string of specified length
    name = ''.join(random.choices(name_chars, k=length))
    return f"{prefix}_{name}"