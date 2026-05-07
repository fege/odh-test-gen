// SCORER CALIBRATION: HIGH QUALITY test (should score 9-10/10)
//
// Purpose: Trains scorer to recognize excellent Go test quality.
//          For PATTERN guidance, see Tiger Team rules at:
//          ~/Code/Red-Hat-Quality-Tiger-Team/.claude/rules/go-tests.md
//
// Rubric Scores (5 criteria, 0-2 each, total 10):
// ✅ Coverage: 2/2 - All TC requirements implemented (preconditions, steps, assertions)
// ✅ Assertions: 2/2 - Gomega matchers with clear expectation messages
// ✅ Conventions: 2/2 - Follows Tiger Team go-tests.md patterns (Ginkgo/Gomega, By() statements)
// ✅ Test Data: 2/2 - Uses exact values from TC, repo mock factories
// ✅ Code Quality: 2/2 - No TODOs for specified requirements, no fabricated helpers
//
// This example demonstrates QUALITY LEVEL (9/10), not just patterns.

package api_test

import (
	"net/http"

	"github.com/kubeflow/model-registry/ui/bff/internal/mocks"
	"github.com/kubeflow/model-registry/ui/bff/internal/integrations/kubernetes"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("TC-API-001: Retrieve tool-calling metadata", func() {
	It("should return complete tool-calling metadata for granite model", func() {
		By("setting up request identity from TC preconditions")
		requestIdentity := kubernetes.RequestIdentity{
			UserID: "user@example.com",
		}

		By("fetching model by exact ID from TC test data")
		modelID := "RedHatAI/granite-3.1-8b-instruct" // Exact ID from TC Expected Response

		actual, rs, err := setupApiTest[ModelEnvelope](
			http.MethodGet,
			"/api/v1/models/" + modelID,
			nil,
			mockedClientFactory,
			requestIdentity,
		)

		By("verifying successful response from TC expected results")
		Expect(err).NotTo(HaveOccurred(), "API call should succeed without errors")
		Expect(rs.StatusCode).To(Equal(http.StatusOK), "Should return 200 OK for valid model")

		By("verifying tool-calling metadata fields from TC")
		Expect(actual.Data.ToolCallingSupported).To(BeTrue(), "Model should support tool calling")
		Expect(actual.Data.RequiredCLIArgs).NotTo(BeEmpty(), "Required CLI args must be present")
		Expect(actual.Data.RequiredCLIArgs).To(ContainElement("--enable-tool-calling"))
		Expect(actual.Data.ChatTemplatePath).To(Equal("examples/tool_chat_template_granite.jinja"))
	})
})
