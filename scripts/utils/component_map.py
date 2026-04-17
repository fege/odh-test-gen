"""
Component to repository mapping for OpenDataHub components.

Based on opendatahub-io/odh-build-metadata manifests-config.yaml
Source: https://github.com/opendatahub-io/odh-build-metadata/blob/main/components/odh-operator/.../manifests-config.yaml
Updated: 2026-04-17

Maps component keywords (from TestPlan.md, TC files) to GitHub repositories.
"""

# Component name → GitHub repository (org/repo)
COMPONENT_REPO_MAP = {
    # Notebooks / Workbenches
    'notebook': 'opendatahub-io/notebooks',
    'notebooks': 'opendatahub-io/notebooks',
    'workbench': 'opendatahub-io/notebooks',
    'workbenches': 'opendatahub-io/notebooks',

    # Dashboard / UI
    'dashboard': 'opendatahub-io/odh-dashboard',
    'odh-dashboard': 'opendatahub-io/odh-dashboard',
    'ui': 'opendatahub-io/odh-dashboard',
    'catalog ui': 'opendatahub-io/odh-dashboard',

    # Model Serving - KServe
    'kserve': 'opendatahub-io/kserve',
    'model-serving': 'opendatahub-io/kserve',
    'model serving': 'opendatahub-io/kserve',
    'serving': 'opendatahub-io/kserve',

    # Model Serving - MLServer
    'mlserver': 'opendatahub-io/MLServer',

    # Model Serving - OpenVINO
    'openvino': 'opendatahub-io/openvino_model_server',

    # Model Registry / Model Catalog / AI Hub
    'model-registry': 'opendatahub-io/model-registry',
    'model registry': 'opendatahub-io/model-registry',
    'modelregistry': 'opendatahub-io/model-registry',
    'model-catalog': 'opendatahub-io/model-registry',
    'model catalog': 'opendatahub-io/model-registry',
    'ai-hub': 'opendatahub-io/model-registry',
    'ai hub': 'opendatahub-io/model-registry',

    # Model Controller
    'model-controller': 'opendatahub-io/odh-model-controller',
    'model controller': 'opendatahub-io/odh-model-controller',

    # Data Science Pipelines
    'pipeline': 'opendatahub-io/data-science-pipelines',
    'pipelines': 'opendatahub-io/data-science-pipelines',
    'data-science-pipelines': 'opendatahub-io/data-science-pipelines',
    'datasciencepipelines': 'opendatahub-io/data-science-pipelines',
    'data science pipelines': 'opendatahub-io/data-science-pipelines',

    # Pipelines - Argo
    'argo': 'opendatahub-io/argo-workflows',
    'argo-workflows': 'opendatahub-io/argo-workflows',

    # Pipelines - Components
    'pipelines-components': 'opendatahub-io/pipelines-components',

    # Distributed Workloads
    'distributed-workloads': 'opendatahub-io/distributed-workloads',
    'distributed workloads': 'opendatahub-io/distributed-workloads',

    # Training
    'training': 'opendatahub-io/training-operator',
    'training-operator': 'opendatahub-io/training-operator',
    'trainer': 'opendatahub-io/trainer',

    # Ray / Kuberay
    'ray': 'opendatahub-io/kuberay',
    'kuberay': 'opendatahub-io/kuberay',

    # TrustyAI
    'trustyai': 'opendatahub-io/trustyai-service-operator',
    'trusty-ai': 'opendatahub-io/trustyai-service-operator',
    'trusty ai': 'opendatahub-io/trustyai-service-operator',

    # Guardrails
    'guardrails': 'opendatahub-io/fms-guardrails-orchestrator',
    'fms-guardrails': 'opendatahub-io/fms-guardrails-orchestrator',

    # MaaS (Models as a Service)
    'maas': 'opendatahub-io/models-as-a-service',
    'models-as-a-service': 'opendatahub-io/models-as-a-service',
    'models as a service': 'opendatahub-io/models-as-a-service',

    # MLflow
    'mlflow': 'opendatahub-io/mlflow',
    'mlflow-operator': 'opendatahub-io/mlflow-operator',

    # Feast
    'feast': 'opendatahub-io/feast',
    'feast-operator': 'opendatahub-io/feast',
    'feature-server': 'opendatahub-io/feast',

    # Llama Stack
    'llama-stack': 'opendatahub-io/llama-stack-k8s-operator',
    'llama stack': 'opendatahub-io/llama-stack-k8s-operator',

    # Spark
    'spark': 'opendatahub-io/spark-operator',
    'spark-operator': 'opendatahub-io/spark-operator',

    # Kubeflow
    'kubeflow': 'opendatahub-io/kubeflow',

    # Workload Autoscaler
    'workload-variant-autoscaler': 'opendatahub-io/workload-variant-autoscaler',
    'wva': 'opendatahub-io/workload-variant-autoscaler',

    # AI Gateway
    'ai-gateway': 'opendatahub-io/ai-gateway-payload-processing',
    'ai gateway': 'opendatahub-io/ai-gateway-payload-processing',

    # Cluster Validation
    'cluster-validation': 'opendatahub-io/rhaii-cluster-validation',
    'rhaii-validator': 'opendatahub-io/rhaii-cluster-validation',

    # Downstream E2E tests
    'opendatahub-tests': 'opendatahub-io/opendatahub-tests',
}
