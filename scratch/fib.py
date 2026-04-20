import itertools

def fib_generator(n):
    """
    Generates the Fibonacci sequence up to the n-th term.
    Uses a generator to yield the terms.
    """
    a, b = 0, 1
    terms = []
    for i in range(n):
        if i == 0:
            terms.append(a)
            a, b = b, a + b
        elif i == 1:
            terms.append(b)
            a, b = b, a + b
        else:
            # For subsequent terms, we need to continue the sequence
            # This implementation is slightly complex for a simple generator,
            # so let's simplify it to generate the sequence iteratively.
            # A simpler approach is to just calculate the sequence up to the 10th term.
            pass

    # A simpler, more robust generator approach for sequence generation:
    current = 0
    next_val = 1
    for _ in range(n):
        yield current
        current, next_val = next_val, current + next_val

def calculate_fib_sequence(n):
    """Calculates the Fibonacci sequence up to the n-th term."""
    if n < 0:
        return "N must be non-negative"

    # We use the standard definition: F(0)=0, F(1)=1, F(2)=1, F(3)=2, ...
    # For simplicity in generator implementation, we'll start with F(0)=0, F(1)=1
    
    fib_sequence = []
    a, b = 0, 1
    
    for _ in range(n):
        yield a
        a, b = b, a + b

    # We need to consume the generator to get the terms
    result = []
    for term in fib_generator(n):
        result.append(term)
    
    return result

if __name__ == '__main__':
    N = 10
    print(f"Calculating Fibonacci sequence up to the {N}th term:")
    fib_terms = calculate_fib_sequence(N)
    print(fib_terms)