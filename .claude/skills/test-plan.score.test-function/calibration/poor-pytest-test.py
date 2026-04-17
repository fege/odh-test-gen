# Example of LOW QUALITY test (should score 3-4/10)
#
# Coverage: 1/2 - Missing some expected results, has TODOs for specified requirements
# Assertions: 0/2 - Generic assertions, no messages
# Conventions: 1/2 - Uses invented marker not in repo's pytest.ini
# Test Data: 0/2 - Uses placeholder "test-model" instead of exact ID from TC
# Code Quality: 0/2 - Excessive TODOs, fabricated helper, missing error checks

import pytest


@pytest.mark.p0  # Bad - marker invented, not from repo conventions
def test_retrieve_tool_calling_metadata(api_client):
    """TC-API-001: Verify that the API returns complete tool-calling metadata."""
    # Arrange
    model_id = "test-model"  # Placeholder instead of exact ID from TC

    # Act
    response = get_model_metadata(api_client, model_id)  # Fabricated helper not in repo

    # Assert
    assert response is not None  # Generic assertion
    assert response.status_code == 200  # No message

    # TODO: Check tool_calling_supported field  # TC specifies this - shouldn't be TODO
    # TODO: Verify required_cli_args  # TC specifies this - shouldn't be TODO
    # TODO: Check chat_template_path  # TC specifies this - shouldn't be TODO


def get_model_metadata(client, model_id):
    """Fabricated helper function that doesn't exist in repository."""
    return client.get(f'/models/{model_id}')
