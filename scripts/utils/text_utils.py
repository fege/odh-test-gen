"""
Text transformation utilities.

Provides functions for converting text to valid Python identifiers.
"""

import re


def sanitize_to_snake_case(text: str) -> str:
    """
    Convert text to valid Python snake_case identifier.

    Converts common separators (/, -, spaces) to underscores,
    removes special characters, collapses multiple underscores,
    and converts to lowercase.

    Args:
        text: Input text to convert

    Returns:
        snake_case string suitable for Python identifiers

    Examples:
        >>> sanitize_to_snake_case("Hello World")
        'hello_world'
        >>> sanitize_to_snake_case("Create/Update")
        'create_update'
        >>> sanitize_to_snake_case("Test API & Special!")
        'test_api_special'
    """
    # Convert common separators to underscores first
    text = re.sub(r'[/\s-]+', '_', text)

    # Remove remaining special characters (keep alphanumeric and underscore)
    text = re.sub(r'[^\w]', '', text)

    # Convert to lowercase
    text = text.lower()

    # Collapse multiple underscores
    text = re.sub(r'_+', '_', text)

    # Remove leading/trailing underscores
    text = text.strip('_')

    return text
