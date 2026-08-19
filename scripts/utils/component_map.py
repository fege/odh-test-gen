"""
Component to repository mapping for OpenDataHub components.

Based on opendatahub-io/odh-build-metadata manifests-config.yaml
Source: https://github.com/opendatahub-io/odh-build-metadata/blob/main/components/odh-operator/.../manifests-config.yaml
Updated: 2026-04-17

Maps component keywords (from TestPlan.md, TC files, Jira components) to GitHub repositories.

Note: All keys are lowercase. Use get_repo_for_component() for case-insensitive lookup.
"""

# Component name → GitHub repository (org/repo)
# NOTE: All keys must be lowercase for case-insensitive matching
COMPONENT_REPO_MAP = {
    # Notebooks / Workbenches
    "notebook": "opendatahub-io/notebooks",
    "notebooks": "opendatahub-io/notebooks",
    "workbench": "opendatahub-io/notebooks",
    "workbenches": "opendatahub-io/notebooks",
    # Dashboard / UI
    "dashboard": "opendatahub-io/odh-dashboard",
    "odh-dashboard": "opendatahub-io/odh-dashboard",
    "ui": "opendatahub-io/odh-dashboard",
    "catalog ui": "opendatahub-io/odh-dashboard",
    # Model Serving - KServe
    "kserve": "opendatahub-io/kserve",
    "model-serving": "opendatahub-io/kserve",
    "model serving": "opendatahub-io/kserve",
    "serving": "opendatahub-io/kserve",
    # Model Serving - MLServer
    "mlserver": "opendatahub-io/MLServer",
    # Model Serving - OpenVINO
    "openvino": "opendatahub-io/openvino_model_server",
    # Model Registry / Model Catalog / AI Hub
    "model-registry": "opendatahub-io/model-registry",
    "model registry": "opendatahub-io/model-registry",
    "modelregistry": "opendatahub-io/model-registry",
    "model-catalog": "opendatahub-io/model-registry",
    "model catalog": "opendatahub-io/model-registry",
    "ai-hub": "opendatahub-io/model-registry",
    "ai hub": "opendatahub-io/model-registry",
    # Model Controller
    "model-controller": "opendatahub-io/odh-model-controller",
    "model controller": "opendatahub-io/odh-model-controller",
    # Data Science Pipelines
    "pipeline": "opendatahub-io/data-science-pipelines",
    "pipelines": "opendatahub-io/data-science-pipelines",
    "data-science-pipelines": "opendatahub-io/data-science-pipelines",
    "datasciencepipelines": "opendatahub-io/data-science-pipelines",
    "data science pipelines": "opendatahub-io/data-science-pipelines",
    # Pipelines - Argo
    "argo": "opendatahub-io/argo-workflows",
    "argo-workflows": "opendatahub-io/argo-workflows",
    # Pipelines - Components
    "pipelines-components": "opendatahub-io/pipelines-components",
    # Distributed Workloads
    "distributed-workloads": "opendatahub-io/distributed-workloads",
    "distributed workloads": "opendatahub-io/distributed-workloads",
    # Training
    "training": "opendatahub-io/training-operator",
    "training-operator": "opendatahub-io/training-operator",
    "trainer": "opendatahub-io/trainer",
    # Ray / Kuberay
    "ray": "opendatahub-io/kuberay",
    "kuberay": "opendatahub-io/kuberay",
    # TrustyAI
    "trustyai": "opendatahub-io/trustyai-service-operator",
    "trusty-ai": "opendatahub-io/trustyai-service-operator",
    "trusty ai": "opendatahub-io/trustyai-service-operator",
    # Guardrails
    "guardrails": "opendatahub-io/fms-guardrails-orchestrator",
    "fms-guardrails": "opendatahub-io/fms-guardrails-orchestrator",
    # MaaS (Models as a Service)
    "maas": "opendatahub-io/models-as-a-service",
    "models-as-a-service": "opendatahub-io/models-as-a-service",
    "models as a service": "opendatahub-io/models-as-a-service",
    # MLflow
    "mlflow": "opendatahub-io/mlflow",
    "mlflow-operator": "opendatahub-io/mlflow-operator",
    # Feast
    "feast": "opendatahub-io/feast",
    "feast-operator": "opendatahub-io/feast",
    "feature-server": "opendatahub-io/feast",
    # Llama Stack
    "llama-stack": "opendatahub-io/llama-stack-k8s-operator",
    "llama stack": "opendatahub-io/llama-stack-k8s-operator",
    # Spark
    "spark": "opendatahub-io/spark-operator",
    "spark-operator": "opendatahub-io/spark-operator",
    # Kubeflow
    "kubeflow": "opendatahub-io/kubeflow",
    # Workload Autoscaler
    "workload-variant-autoscaler": "opendatahub-io/workload-variant-autoscaler",
    "wva": "opendatahub-io/workload-variant-autoscaler",
    # AI Gateway
    "ai-gateway": "opendatahub-io/ai-gateway-payload-processing",
    "ai gateway": "opendatahub-io/ai-gateway-payload-processing",
    # Cluster Validation
    "cluster-validation": "opendatahub-io/rhaii-cluster-validation",
    "rhaii-validator": "opendatahub-io/rhaii-cluster-validation",
    # Downstream E2E tests
    "opendatahub-tests": "opendatahub-io/opendatahub-tests",
    # UXD (product component, maps to dashboard)
    "uxd": "opendatahub-io/odh-dashboard",
    # EvalHub (Model Evaluation)
    "model eval": "eval-hub/eval-hub",
    "model-eval": "eval-hub/eval-hub",
    "evalhub": "eval-hub/eval-hub",
    "eval-hub": "eval-hub/eval-hub",
    "eval hub": "eval-hub/eval-hub",
    "evaluation hub": "eval-hub/eval-hub",
    # EvalHub SDK
    "eval-hub-sdk": "eval-hub/eval-hub-sdk",
    "evalhub-sdk": "eval-hub/eval-hub-sdk",
    "eval hub sdk": "eval-hub/eval-hub-sdk",
}


# Component name → test directory in opendatahub-tests
# Maps test plan/strategy/Jira components to opendatahub-tests subdirectories
# Source: https://github.com/opendatahub-io/opendatahub-tests/tree/main/tests
# NOTE: All keys must be lowercase for case-insensitive matching
COMPONENT_TEST_DIR_MAP = {
    # Dashboard / UI / UXD → ai_hub
    "dashboard": "ai_hub",
    "odh-dashboard": "ai_hub",
    "ui": "ai_hub",
    "catalog ui": "ai_hub",
    "uxd": "ai_hub",
    "ai core dashboard": "ai_hub",
    "gen ai studio": "ai_hub",
    # AI Hub / Model Registry / Model Catalog → ai_hub
    "ai-hub": "ai_hub",
    "ai hub": "ai_hub",
    "model-registry": "ai_hub",
    "model registry": "ai_hub",
    "modelregistry": "ai_hub",
    "model-catalog": "ai_hub",
    "model catalog": "ai_hub",
    # Model Serving → model_serving
    "kserve": "model_serving",
    "model-serving": "model_serving",
    "model serving": "model_serving",
    "serving": "model_serving",
    # Notebooks / Workbenches → workbenches
    "notebook": "workbenches",
    "notebooks": "workbenches",
    "workbench": "workbenches",
    "workbenches": "workbenches",
    # Pipelines → pipelines_components
    "pipeline": "pipelines_components",
    "pipelines": "pipelines_components",
    "data-science-pipelines": "pipelines_components",
    "data science pipelines": "pipelines_components",
    "pipelines-components": "pipelines_components",
    # AI Gateway → ai_gateway
    "ai-gateway": "ai_gateway",
    "ai gateway": "ai_gateway",
    # AI Safety / Guardrails → ai_safety
    "ai safety": "ai_safety",
    "ai-safety": "ai_safety",
    "guardrails": "ai_safety",
    "trustyai": "ai_safety",
    "trusty-ai": "ai_safety",
    "trusty ai": "ai_safety",
    # Spark → spark
    "spark": "spark",
    "spark-operator": "spark",
    # OpenShell → openshell
    "openshell": "openshell",
    "open shell": "openshell",
    # OGX → ogx
    "ogx": "ogx",
    # RHOAI MCP → rhoai_mcp
    "rhoai mcp": "rhoai_mcp",
    "rhoai-mcp": "rhoai_mcp",
    "mcp": "rhoai_mcp",
}


def get_repo_for_component(component: str) -> str | None:
    """
    Get GitHub repository for a component name (case-insensitive).

    Handles both lowercase content-discovered components and capitalized
    Jira product component names (e.g., "AI Hub", "Model Serving").

    Args:
        component: Component name (any case)

    Returns:
        GitHub repository (org/repo) or None if not found

    Examples:
        >>> get_repo_for_component("AI Hub")
        'opendatahub-io/model-registry'
        >>> get_repo_for_component("notebooks")
        'opendatahub-io/notebooks'
        >>> get_repo_for_component("Model Serving")
        'opendatahub-io/kserve'
    """
    normalized = component.strip().lower()
    return COMPONENT_REPO_MAP.get(normalized)


def get_test_dir_for_component(component: str) -> str | None:
    """
    Get test directory for a component in opendatahub-tests.

    Maps test plan/strategy/Jira component names to test subdirectories.

    Args:
        component: Component name (any case)

    Returns:
        Test directory name (e.g., "ai_hub", "model_serving") or None if not found

    Examples:
        >>> get_test_dir_for_component("AI Core Dashboard")
        'ai_hub'
        >>> get_test_dir_for_component("Model Registry")
        'ai_hub'
        >>> get_test_dir_for_component("Model Serving")
        'model_serving'
        >>> get_test_dir_for_component("Workbenches")
        'workbenches'
    """
    normalized = component.strip().lower()
    return COMPONENT_TEST_DIR_MAP.get(normalized)
