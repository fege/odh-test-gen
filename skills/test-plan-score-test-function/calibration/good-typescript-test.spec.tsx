// SCORER CALIBRATION: HIGH QUALITY test (should score 9-10/10)
//
// Purpose: Trains scorer to recognize excellent TypeScript/React test quality.
//          For PATTERN guidance, see Tiger Team rules at:
//          ~/Code/Red-Hat-Quality-Tiger-Team/.claude/rules/typescript-unit-tests.md
//
// Rubric Scores (5 criteria, 0-2 each, total 10):
// ✅ Coverage: 2/2 - All TC requirements implemented (preconditions, user actions, assertions)
// ✅ Assertions: 2/2 - Specific assertions using React Testing Library matchers with messages
// ✅ Conventions: 2/2 - Follows Tiger Team typescript-unit-tests.md patterns (RTL queries, userEvent)
// ✅ Test Data: 2/2 - Uses exact values from TC, repo mock factories
// ✅ Code Quality: 2/2 - No TODOs for specified requirements, no fabricated helpers
//
// This example demonstrates QUALITY LEVEL (9/10), not just patterns.

import '@testing-library/jest-dom';
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { mockToolCallingModel } from '~/__mocks__/mockModels';
import ModelCatalogView from '~/app/components/ModelCatalogView';

describe('TC-UI-001: Display tool-calling metadata', () => {
  it('should display complete tool-calling metadata for granite model', async () => {
    // Arrange - from TC preconditions and test data
    const model = mockToolCallingModel({
      id: 'RedHatAI/granite-3.1-8b-instruct', // Exact ID from TC
      toolCallingSupported: true,
      requiredCliArgs: ['--enable-tool-calling', '--temperature=0.7'],
      chatTemplatePath: 'examples/tool_chat_template_granite.jinja',
    });

    // Act - from TC test steps
    render(<ModelCatalogView model={model} />);

    // Assert - from TC expected results
    await waitFor(() => {
      expect(screen.getByText('RedHatAI/granite-3.1-8b-instruct')).toBeInTheDocument();
    });

    expect(screen.getByTestId('tool-calling-badge')).toHaveTextContent('Supported');
    expect(screen.getByText('--enable-tool-calling')).toBeInTheDocument();
    expect(screen.getByText('--temperature=0.7')).toBeInTheDocument();

    const templatePath = screen.getByTestId('chat-template-path');
    expect(templatePath).toHaveTextContent('examples/tool_chat_template_granite.jinja');
  });
});
