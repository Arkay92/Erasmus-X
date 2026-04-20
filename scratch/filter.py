def filter_fruit_names(fruit_list):
    """
    Filters a list of fruit names, returning only those with more than 5 letters.
    """
    filtered_list = [fruit for fruit in fruit_list if len(fruit) > 5]
    return filtered_list

# Example usage:
if __name__ == '__main__':
    fruit_data = ['apple', 'banana', 'kiwi', 'strawberry', 'pineapple']
    
    print(f"Original list: {fruit_data}")
    
    long_fruits = filter_fruit_names(fruit_data)
    
    print(f"Filtered list (length > 5): {long_fruits}")