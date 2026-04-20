def filter_long_fruits(fruit_list):
    """
    Filters a list of fruits, returning only those names that have more than 5 letters.
    """
    long_fruits = [fruit for fruit in fruit_list if len(fruit) > 5]
    return long_fruits

if __name__ == "__main__":
    # Example list of fruits
    fruit_list = ["apple", "banana", "kiwi", "orange", "pineapple"]
    
    print(f"Original list: {fruit_list}")
    
    filtered_list = filter_long_fruits(fruit_list)
    
    print(f"Fruits with more than 5 letters: {filtered_list}")