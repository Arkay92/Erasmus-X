def bubble_sort(arr):
    """
    Implements the Bubble Sort algorithm to sort a list of numbers in ascending order.
    """
    n = len(arr)
    
    # Loop through the list, performing comparisons and swaps
    for i in range(n):
        # If the current element is greater than the next element, swap them
        if arr[i] > arr[i+1]:
            # Swap operation
            arr[i], arr[i+1] = arr[i+1], arr[i]
        
    # Optional: If you want to print the sorted list (not strictly required by prompt, but useful)
    # print(f"Sorted array: {arr}")
    return arr

if __name__ == '__main__':
    # Example usage
    numbers = [64, 34, 25, 10, 14]
    print(f"Original list: {numbers}")
    
    sorted_numbers = bubble_sort(numbers)
    print(f"Sorted list: {sorted_numbers}")