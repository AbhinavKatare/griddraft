# GitHub Workflows & Automation (`/.github`)

This directory contains GitHub configuration files, issue templates, PR templates, and Continuous Integration (CI) workflows.

## Workflows

* **`workflows/ci.yml`:** Automated CI pipeline triggered on all commits and pull requests against `main`.
  * **Backend Pipeline:** Ruff linting, Mypy static type checking, and Pytest execution (14 unit and edge case tests).
  * **Frontend Pipeline:** Dependency audit, TypeScript type checking (`tsc -b`), and Vite production compilation.
