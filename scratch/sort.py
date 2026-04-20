def bubble_sort(arr):
    """
    Implements the Bubble Sort algorithm to sort a list of numbers in ascending order.
    This function sorts the list in place.
    """
    n = len(arr)
    
    # Loop through the list, performing comparisons and swaps
    for i in range(n):
        # Loop through pairs to compare adjacent elements
        # We only need to iterate up to n - i - 1 because the largest elements
        # are already in their final position after 'i' passes.
        for j in range(n - i - 1):
            # Check if the current element is greater than the next element
            if arr[j] > arr[j + 1]:
                # Swap the elements
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                
    return arr

# Example usage:
if __name__ == '__main__':
    numbers = [64, 32, 2, 12, 14, 14]
    print(f"Original list: {numbers}")
    
    print("Sorting the list...")
    sorted_list = bubble_sort(numbers)
    print(f"Sorted list: {sorted_list}")