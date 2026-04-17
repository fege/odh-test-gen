# Example of HIGH QUALITY test (should score 9-10/10)
#
# Coverage: 2/2 - All preconditions, steps, expected results implemented
# Assertions: 2/2 - Specific assertions with messages, checks exact values
# Conventions: 2/2 - Follows pytest patterns, uses actual repo markers
# Test Data: 2/2 - Uses exact model ID from TC Expected Response
# Code Quality: 2/2 - No TODOs, clean implementation
#
# NOTE: Markers shown are examples - actual test should use markers from conventions file

import pytest


@pytest.mark.tier1
def test_retrieve_tool_calling_metadata(model_catalog_client):
    """TC-API-001: Verify Model Catalog BFF API returns complete tool-calling metadata."""
    # Arrange - from TC preconditions
    model_id = "RedHatAI/granite-3.1-8b-instruct"  # Exact ID from TC Expected Response

    # Act - from TC test steps
    response = model_catalog_client.get(f'/api/model_catalog/v1alpha1/models/{model_id}')

    # Assert - from TC expected results
    assert response.status_code == 200, "API should return 200 OK for valid model"
    data = response.json()

    # Check all required fields from TC
    assert data['tool_calling_supported'] is True, "Model should have tool calling enabled"
    assert 'required_cli_args' in data, "Response must include required_cli_args field"
    assert isinstance(data['required_cli_args'], list), "required_cli_args should be a list"
    assert len(data['required_cli_args']) > 0, "required_cli_args should not be empty"

    assert 'chat_template_path' in data, "Response must include chat_template_path"
    assert data['chat_template_path'] == "examples/tool_chat_template_granite.jinja"
