#!/usr/bin/env python3
"""
Input Validation Utilities for n8n Workflows
Provides sanitization and validation functions for user inputs
"""

import re
from typing import Any, Optional, List, Dict
from uuid import UUID


class InputValidator:
    """Validation utilities for n8n workflow inputs"""

    @staticmethod
    def sanitize_string(value: Any, max_length: int = 500) -> str:
        """
        Sanitize string input by removing dangerous characters
        and limiting length.
        """
        if value is None:
            return ""

        # Convert to string
        text = str(value).strip()

        # Remove null bytes
        text = text.replace('\x00', '')

        # Limit length
        if len(text) > max_length:
            text = text[:max_length]

        return text

    @staticmethod
    def validate_uuid(value: Any) -> Optional[str]:
        """
        Validate that value is a valid UUID.
        Returns UUID string or None if invalid.
        """
        try:
            uuid_obj = UUID(str(value))
            return str(uuid_obj)
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def validate_enum(value: Any, allowed_values: List[str], default: str) -> str:
        """
        Validate that value is in allowed enum values.
        Returns the value if valid, default otherwise.
        """
        value_str = str(value).lower() if value else ""
        return value_str if value_str in allowed_values else default

    @staticmethod
    def validate_integer(value: Any, min_val: int = None, max_val: int = None, default: int = 0) -> int:
        """
        Validate integer value with optional min/max constraints.
        """
        try:
            int_val = int(value)

            if min_val is not None and int_val < min_val:
                return default
            if max_val is not None and int_val > max_val:
                return default

            return int_val
        except (ValueError, TypeError):
            return default

    @staticmethod
    def validate_float(value: Any, min_val: float = None, max_val: float = None, default: float = 0.0) -> float:
        """
        Validate float value with optional min/max constraints.
        """
        try:
            float_val = float(value)

            if min_val is not None and float_val < min_val:
                return default
            if max_val is not None and float_val > max_val:
                return default

            return float_val
        except (ValueError, TypeError):
            return default

    @staticmethod
    def sanitize_array(value: Any, max_items: int = 50, max_item_length: int = 100) -> List[str]:
        """
        Sanitize array of strings.
        """
        if not isinstance(value, (list, tuple)):
            return []

        sanitized = []
        for item in value[:max_items]:
            sanitized_item = InputValidator.sanitize_string(item, max_item_length)
            if sanitized_item:
                sanitized.append(sanitized_item)

        return sanitized

    @staticmethod
    def validate_file_path(value: Any) -> Optional[str]:
        """
        Validate file path - prevent directory traversal.
        """
        if not value:
            return None

        path_str = str(value)

        # Prevent directory traversal
        if '..' in path_str or path_str.startswith('/etc') or path_str.startswith('/sys'):
            return None

        # Remove null bytes
        path_str = path_str.replace('\x00', '')

        return path_str

    @staticmethod
    def validate_priority(value: Any) -> str:
        """
        Validate task/reminder priority.
        """
        return InputValidator.validate_enum(
            value,
            ['low', 'medium', 'high', 'critical'],
            'medium'
        )

    @staticmethod
    def validate_status(value: Any, context: str = 'task') -> str:
        """
        Validate status field based on context.
        """
        if context == 'task':
            return InputValidator.validate_enum(
                value,
                ['todo', 'in_progress', 'waiting', 'done', 'cancelled'],
                'todo'
            )
        elif context == 'reminder':
            return InputValidator.validate_enum(
                value,
                ['pending', 'fired', 'completed', 'cancelled'],
                'pending'
            )
        elif context == 'event':
            return InputValidator.validate_enum(
                value,
                ['scheduled', 'in_progress', 'completed', 'cancelled'],
                'scheduled'
            )
        else:
            return 'unknown'

    @staticmethod
    def validate_preference(value: Any) -> str:
        """
        Validate food preference.
        """
        return InputValidator.validate_enum(
            value,
            ['liked', 'disliked', 'favorite', 'never_again'],
            'liked'
        )

    @staticmethod
    def validate_meal_type(value: Any) -> Optional[str]:
        """
        Validate meal type.
        """
        validated = InputValidator.validate_enum(
            value,
            ['breakfast', 'lunch', 'dinner', 'snack'],
            ''
        )
        return validated if validated else None

    @staticmethod
    def validate_email(value: Any) -> Optional[str]:
        """
        Basic email validation.
        """
        if not value:
            return None

        email_str = str(value).strip().lower()

        # Basic regex for email validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        if re.match(pattern, email_str) and len(email_str) <= 254:
            return email_str

        return None

    @staticmethod
    def create_safe_payload(data: Dict[str, Any], schema: Dict[str, str]) -> Dict[str, Any]:
        """
        Create safe payload for database operations by validating all fields.

        schema format: {
            'field_name': 'validation_type',  # e.g., 'string', 'uuid', 'integer', 'enum:value1,value2'
        }
        """
        safe_payload = {}

        for field, validation_type in schema.items():
            value = data.get(field)

            if validation_type == 'string':
                safe_payload[field] = InputValidator.sanitize_string(value)
            elif validation_type == 'uuid':
                safe_payload[field] = InputValidator.validate_uuid(value)
            elif validation_type == 'integer':
                safe_payload[field] = InputValidator.validate_integer(value)
            elif validation_type == 'float':
                safe_payload[field] = InputValidator.validate_float(value)
            elif validation_type == 'array':
                safe_payload[field] = InputValidator.sanitize_array(value)
            elif validation_type.startswith('enum:'):
                allowed = validation_type.split(':', 1)[1].split(',')
                safe_payload[field] = InputValidator.validate_enum(value, allowed, allowed[0])
            else:
                safe_payload[field] = value  # Pass through unknown types

        return safe_payload


# Example usage in n8n Python Code node
if __name__ == "__main__":
    # Example: Validate food log input
    validator = InputValidator()

    input_data = {
        "food_name": "Pizza' OR 1=1; DROP TABLE food_log; --",
        "location": "Home",
        "preference": "super_liked",  # Invalid
        "calories": "9999",
        "ingredients": ["cheese", "tomato"] * 100,  # Too many
    }

    schema = {
        "food_name": "string",
        "location": "string",
        "calories": "integer",
        "ingredients": "array",
    }

    safe_data = validator.create_safe_payload(input_data, schema)
    validated_preference = validator.validate_preference(input_data["preference"])

    print("Safe data:", safe_data)
    print("Validated preference:", validated_preference)
