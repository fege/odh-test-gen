#!/usr/bin/env python3
"""
Repository discovery and management utilities for test-plan skills.

NON-INTERACTIVE utilities - no user prompts, no LLM calls.
Skills orchestrate: find → ask user → clone (if needed).
"""

import os
import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Known repository configurations
KNOWN_REPOS = {
    'odh-test-context': {
        'name': 'odh-test-context',
        'url': 'https://github.com/opendatahub-io/odh-test-context',
        'verify': lambda p: os.path.isdir(os.path.join(p, "tests")) and
                           len(list(Path(p).glob("tests/*.json"))) > 0
    },
    'tiger-team': {
        'name': 'Red-Hat-Quality-Tiger-Team',
        'url': 'https://github.com/RedHatQE/Red-Hat-Quality-Tiger-Team',
        'verify': lambda p: os.path.isdir(os.path.join(p, ".claude", "skills"))
    }
}


def find_repo_in_common_locations(repo_name: str, verify_func=None) -> Optional[str]:
    """
    Find repository in common locations.

    Checks:
    - ~/Code/<repo_name>
    - ~/<repo_name>
    - ~/workspace/<repo_name>
    - ../<repo_name>

    Args:
        repo_name: Repository directory name
        verify_func: Optional function to verify repo (returns bool)

    Returns:
        Absolute path or None if not found
    """
    common_bases = ["~/Code", "~", "~/workspace", ".."]

    for base in common_bases:
        full_path = os.path.abspath(os.path.expanduser(os.path.join(base, repo_name)))
        if os.path.isdir(full_path):
            # Verify if function provided
            if verify_func:
                if verify_func(full_path):
                    return full_path
            # Default: check .git exists
            elif os.path.isdir(os.path.join(full_path, ".git")):
                return full_path

    return None


def find_known_repo(repo_type: str) -> Tuple[Optional[str], str]:
    """
    Find a known repository (odh-test-context, tiger-team).

    Args:
        repo_type: Type of repo ('odh-test-context' or 'tiger-team')

    Returns:
        (path, clone_url): Tuple of (path if found else None, clone URL for convenience)
    """
    if repo_type not in KNOWN_REPOS:
        raise ValueError(f"Unknown repo type: {repo_type}. Valid: {list(KNOWN_REPOS.keys())}")

    config = KNOWN_REPOS[repo_type]
    path = find_repo_in_common_locations(config['name'], config['verify'])

    return (path, config['url'])


def find_target_repo(repo_name: str) -> Optional[str]:
    """
    Find target code repository (e.g., 'odh-dashboard' or 'opendatahub-io/odh-dashboard').

    Checks:
    - ~/Code/<repo>
    - ~/Code/<org>-<repo> (if org/repo format)
    - ~/<repo>
    - ~/workspace/<repo>

    Args:
        repo_name: Repository name (with or without org)

    Returns:
        Absolute path or None
    """
    # Parse org/repo if present
    if '/' in repo_name:
        org, repo = repo_name.split('/', 1)
        # Try with org prefix too
        path = find_repo_in_common_locations(f"{org}-{repo}")
        if path:
            return path
    else:
        repo = repo_name

    # Try without org
    return find_repo_in_common_locations(repo)


def clone_repo(repo_url: str, target_path: str) -> Optional[str]:
    """
    Clone Git repository.

    Args:
        repo_url: GitHub URL
        target_path: Where to clone (~ expanded)

    Returns:
        Absolute path to cloned repo or None if failed
    """
    target = os.path.abspath(os.path.expanduser(target_path))
    os.makedirs(os.path.dirname(target), exist_ok=True)

    try:
        subprocess.run(
            ["git", "clone", repo_url, target],
            capture_output=True,
            text=True,
            check=True
        )
        return target
    except subprocess.CalledProcessError as e:
        print(f"Clone failed ({repo_url}): {e.stderr}")
        return None


def map_components_to_repos(
    components: List[str],
    odh_test_context_path: Optional[str] = None
) -> Dict[str, str]:
    """
    Map component names to GitHub repos.

    Uses odh-test-context if available, else hardcoded fallback.

    Args:
        components: Component names (['notebooks', 'dashboard'])
        odh_test_context_path: Path to odh-test-context (if available)

    Returns:
        {component: 'org/repo'}
    """
    component_repo_map = {}

    # Load from odh-test-context
    if odh_test_context_path:
        tests_dir = os.path.join(odh_test_context_path, "tests")
        if os.path.isdir(tests_dir):
            for json_file in Path(tests_dir).glob("*.json"):
                repo_name = json_file.stem
                try:
                    with open(json_file, 'r') as f:
                        context = json.load(f)
                    org = context.get('org', 'opendatahub-io')
                    repo_full = f"{org}/{repo_name}"

                    component_repo_map[repo_name.lower()] = repo_full

                    # Alias: "odh-dashboard" → "dashboard"
                    if repo_name.startswith('odh-'):
                        component_repo_map[repo_name[4:].lower()] = repo_full
                except (json.JSONDecodeError, IOError):
                    continue

    # Fallback map
    fallback = {
        'notebooks': 'opendatahub-io/notebooks',
        'notebook': 'opendatahub-io/notebooks',
        'dashboard': 'opendatahub-io/odh-dashboard',
        'odh-dashboard': 'opendatahub-io/odh-dashboard',
        'model-serving': 'kserve/kserve',
        'model serving': 'kserve/kserve',
        'model-registry': 'opendatahub-io/model-registry',
        'model registry': 'opendatahub-io/model-registry',
        'pipelines': 'opendatahub-io/data-science-pipelines',
        'data-science-pipelines': 'opendatahub-io/data-science-pipelines',
        'workbenches': 'opendatahub-io/notebooks',
        'workbench': 'opendatahub-io/notebooks',
        'kserve': 'kserve/kserve',
        'modelmesh': 'opendatahub-io/modelmesh-serving',
        'model-mesh': 'opendatahub-io/modelmesh-serving',
    }

    # Merge (odh-test-context wins)
    for k, v in fallback.items():
        component_repo_map.setdefault(k, v)

    # Match components
    matched = {}
    for component in components:
        key = component.lower().replace(' ', '-')
        if key in component_repo_map:
            matched[component] = component_repo_map[key]

    return matched


def load_repo_test_context(repo_name: str, odh_test_context_path: str) -> Optional[Dict]:
    """
    Load test context from odh-test-context.

    Args:
        repo_name: Repo name ('odh-dashboard')
        odh_test_context_path: Path to odh-test-context

    Returns:
        Context dict or None
    """
    context_file = os.path.join(odh_test_context_path, "tests", f"{repo_name}.json")

    if not os.path.exists(context_file):
        return None

    try:
        with open(context_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading {context_file}: {e}")
        return None


def extract_conventions_from_context(test_context: Dict) -> Dict:
    """Extract test conventions from odh-test-context."""
    return {
        'framework': test_context.get('testing', {}).get('framework', 'unknown'),
        'test_file_pattern': test_context.get('conventions', {}).get('test_file_pattern', 'test_*.py'),
        'test_function_pattern': test_context.get('conventions', {}).get('test_function_pattern', 'test_*'),
        'import_style': test_context.get('conventions', {}).get('import_style', 'absolute'),
        'markers': test_context.get('conventions', {}).get('markers', []),
        'linting_tools': [t.get('tool') for t in test_context.get('linting', {}).get('tools', [])],
        'linting_commands': [c.get('command') for c in test_context.get('linting', {}).get('commands', [])],
        'test_directories': test_context.get('testing', {}).get('directories', []),
        'test_commands': test_context.get('testing', {}).get('commands', []),
    }


def get_framework(test_context: Optional[Dict] = None) -> Optional[str]:
    """
    Get framework from odh-test-context data.

    Returns None if not found - caller uses sub-agent for discovery.

    Args:
        test_context: Test context from odh-test-context

    Returns:
        Framework name or None
    """
    if test_context:
        fw = test_context.get('testing', {}).get('framework')
        if fw and fw != 'unknown':
            return fw

    return None


def get_git_root(path: str) -> Optional[str]:
    """
    Get git repository root directory.

    Args:
        path: Directory inside a git repo

    Returns:
        Absolute path to git root or None if not a git repo
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=path,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_git_remote(path: str) -> Optional[str]:
    """
    Get git repository remote in owner/repo format.

    Args:
        path: Directory inside a git repo

    Returns:
        Remote in "owner/repo" format (e.g., "opendatahub-io/opendatahub-test-plans") or None
    """
    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=path,
            capture_output=True,
            text=True,
            check=True
        )
        url = result.stdout.strip()

        # Extract owner/repo from URL
        # Handles: https://github.com/owner/repo.git, git@github.com:owner/repo.git
        match = re.search(r'github\.com[:/]([^/]+/[^/.]+)', url)
        if match:
            return match.group(1).replace('.git', '')

        return None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
