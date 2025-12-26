"""
Sample module for testing code review functionality.
This module contains intentional minor issues for demonstration purposes.
"""

import math
import os


def calculate_average(numbers):
    # Calculate the average of a list of numbers
    if not numbers:
        raise ValueError("Cannot calculate average of an empty list")
    total = 0
    for num in numbers:
        total = total + num
    average = total / len(numbers)
    return average


def process_user_data(user_id, name, email):
    unused_variable = "This is not used"
    
    user_info = {
        "id": user_id,
        "name": name,
        "email": email,
        "created_at": "2024-01-01"
    }
    
    return user_info


def validate_email(email):
    if "@" in email:
        return True
    else:
        return False


def get_file_size(filepath):
    """Get the size of a file in bytes."""
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        return size
    return None


def calculate_discount(price, discount_percent):
    """
    Calculate the final price after applying a discount.
    
    Args:
        price: The original price
        discount_percent: The discount percentage (0-100)
    
    Returns:
        The final price after discount
    """
    if discount_percent < 0 or discount_percent > 100:
        return None
    
    discount_amount = price * (discount_percent / 100)
    final_price = price - discount_amount
    
    return final_price


def find_max_value(values):
    if not values:
        raise ValueError("Cannot find max value of an empty list")
    max_val = values[0]
    i = 0
    while i < len(values):
        if values[i] > max_val:
            max_val = values[i]
        i = i + 1
    return max_val


def format_currency(amount):
    # Format amount as currency string
    formatted = "$" + str(round(amount, 2))
    return formatted


class DataProcessor:
    def __init__(self, name):
        self.name = name
        self.data = []
        self.config = {}
    
    def add_data(self, item):
        self.data.append(item)
    
    def process(self):
        result = []
        for item in self.data:
            processed_item = item * 2
            result.append(processed_item)
        return result
    
    def get_summary(self):
        if len(self.data) == 0:
            return "No data"
        total = sum(self.data)
        count = len(self.data)
        avg = total / count
        return f"Total: {total}, Count: {count}, Average: {avg}"


def main():
    # Test the functions
    numbers = [10, 20, 30, 40, 50]
    avg = calculate_average(numbers)
    print(f"Average: {avg}")
    
    user = process_user_data(1, "John Doe", "john@example.com")
    print(f"User: {user}")
    
    email_valid = validate_email("test@example.com")
    print(f"Email valid: {email_valid}")
    
    price = 100
    discount = 20
    final_price = calculate_discount(price, discount)
    print(f"Final price: {format_currency(final_price)}")
    
    values = [5, 2, 8, 1, 9, 3]
    max_value = find_max_value(values)
    print(f"Max value: {max_value}")
    
    processor = DataProcessor("test_processor")
    processor.add_data(5)
    processor.add_data(10)
    processor.add_data(15)
    print(f"Summary: {processor.get_summary()}")


if __name__ == "__main__":
    main()

