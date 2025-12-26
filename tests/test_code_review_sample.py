#!/usr/bin/env python3
"""
Unit tests for test_code_review_sample module.

This module contains tests for the functions in test_code_review_sample.py
to verify that the review comments have been properly addressed.
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path to import test_code_review_sample
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_code_review_sample import (
    calculate_average,
    find_max_value,
    process_user_data,
    validate_email,
    get_file_size,
    calculate_discount,
    format_currency,
    DataProcessor
)


class TestCalculateAverage(unittest.TestCase):
    """Test cases for calculate_average function."""
    
    def test_calculate_average_normal(self):
        """Test calculate_average with normal input."""
        result = calculate_average([10, 20, 30, 40, 50])
        self.assertEqual(result, 30)
    
    def test_calculate_average_single_value(self):
        """Test calculate_average with single value."""
        result = calculate_average([42])
        self.assertEqual(result, 42)
    
    def test_calculate_average_empty_list(self):
        """Test calculate_average with empty list raises ValueError."""
        with self.assertRaises(ValueError) as context:
            calculate_average([])
        self.assertIn("empty list", str(context.exception))
    
    def test_calculate_average_negative_numbers(self):
        """Test calculate_average with negative numbers."""
        result = calculate_average([-10, -20, -30])
        self.assertEqual(result, -20)


class TestFindMaxValue(unittest.TestCase):
    """Test cases for find_max_value function."""
    
    def test_find_max_value_normal(self):
        """Test find_max_value with normal input."""
        result = find_max_value([5, 2, 8, 1, 9, 3])
        self.assertEqual(result, 9)
    
    def test_find_max_value_single_value(self):
        """Test find_max_value with single value."""
        result = find_max_value([42])
        self.assertEqual(result, 42)
    
    def test_find_max_value_empty_list(self):
        """Test find_max_value with empty list raises ValueError."""
        with self.assertRaises(ValueError) as context:
            find_max_value([])
        self.assertIn("empty list", str(context.exception))
    
    def test_find_max_value_negative_numbers(self):
        """Test find_max_value with negative numbers."""
        result = find_max_value([-5, -2, -8, -1, -9, -3])
        self.assertEqual(result, -1)
    
    def test_find_max_value_duplicates(self):
        """Test find_max_value with duplicate max values."""
        result = find_max_value([5, 9, 2, 9, 3])
        self.assertEqual(result, 9)


class TestOtherFunctions(unittest.TestCase):
    """Test cases for other functions to ensure they still work."""
    
    def test_process_user_data(self):
        """Test process_user_data function."""
        result = process_user_data(1, "John Doe", "john@example.com")
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["name"], "John Doe")
        self.assertEqual(result["email"], "john@example.com")
    
    def test_validate_email_valid(self):
        """Test validate_email with valid email."""
        self.assertTrue(validate_email("test@example.com"))
    
    def test_validate_email_invalid(self):
        """Test validate_email with invalid email."""
        self.assertFalse(validate_email("invalid-email"))
    
    def test_calculate_discount_valid(self):
        """Test calculate_discount with valid input."""
        result = calculate_discount(100, 20)
        self.assertEqual(result, 80)
    
    def test_calculate_discount_invalid_percent(self):
        """Test calculate_discount with invalid discount percent."""
        self.assertIsNone(calculate_discount(100, 150))
        self.assertIsNone(calculate_discount(100, -10))
    
    def test_format_currency(self):
        """Test format_currency function."""
        result = format_currency(99.99)
        self.assertEqual(result, "$99.99")


class TestDataProcessor(unittest.TestCase):
    """Test cases for DataProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.processor = DataProcessor("test_processor")
    
    def test_add_data(self):
        """Test adding data to processor."""
        self.processor.add_data(5)
        self.processor.add_data(10)
        self.assertEqual(len(self.processor.data), 2)
    
    def test_process(self):
        """Test processing data."""
        self.processor.add_data(5)
        self.processor.add_data(10)
        result = self.processor.process()
        self.assertEqual(result, [10, 20])
    
    def test_get_summary_empty(self):
        """Test get_summary with no data."""
        summary = self.processor.get_summary()
        self.assertEqual(summary, "No data")
    
    def test_get_summary_with_data(self):
        """Test get_summary with data."""
        self.processor.add_data(5)
        self.processor.add_data(10)
        self.processor.add_data(15)
        summary = self.processor.get_summary()
        self.assertIn("Total: 30", summary)
        self.assertIn("Count: 3", summary)
        self.assertIn("Average: 10", summary)


if __name__ == '__main__':
    unittest.main(verbosity=2)

