// SCORER CALIBRATION: HIGH QUALITY test (should score 9-10/10)
//
// Purpose: Trains scorer to recognize excellent Cypress test quality.
//          For PATTERN guidance, see Tiger Team rules at:
//          ~/Code/Red-Hat-Quality-Tiger-Team/.claude/rules/cypress-tests.md
//
// Rubric Scores (5 criteria, 0-2 each, total 10):
// ✅ Coverage: 2/2 - All TC requirements implemented (preconditions, user actions, verifications)
// ✅ Assertions: 2/2 - Specific assertions with should() and clear expectations
// ✅ Conventions: 2/2 - Follows Tiger Team cypress-tests.md patterns (data-testid, page objects, intercepts)
// ✅ Test Data: 2/2 - Uses exact values from TC, fixture data
// ✅ Code Quality: 2/2 - No TODOs for specified requirements, proper waits, no hardcoded delays
//
// This example demonstrates QUALITY LEVEL (9/10), not just patterns.

describe('TC-E2E-001: View tool-calling metadata in model catalog', () => {
  beforeEach(() => {
    // Arrange - from TC preconditions
    cy.intercept('GET', '/api/model_catalog/v1alpha1/models/*', {
      fixture: 'models/granite-tool-calling.json', // Fixture with TC test data
    }).as('getModel');

    cy.visit('/model-catalog');
  });

  it('should display complete tool-calling metadata for granite model', () => {
    // Act - from TC test steps
    cy.findByTestId('model-search-input').type('granite-3.1-8b-instruct'); // Exact ID from TC
    cy.findByTestId('search-button').click();

    cy.wait('@getModel');

    cy.findByTestId('model-card-granite-3.1-8b-instruct').click();

    // Assert - from TC expected results
    cy.findByTestId('model-title').should('contain', 'RedHatAI/granite-3.1-8b-instruct');

    cy.findByTestId('tool-calling-badge')
      .should('be.visible')
      .and('contain', 'Supported');

    // Verify required CLI args from TC
    cy.findByTestId('cli-args-list').within(() => {
      cy.contains('--enable-tool-calling').should('be.visible');
      cy.contains('--temperature=0.7').should('be.visible');
    });

    // Verify chat template path from TC expected response
    cy.findByTestId('chat-template-path')
      .should('contain', 'examples/tool_chat_template_granite.jinja');
  });
});
