# Conventional Commits Specification Guide

This repository enforces the **[Conventional Commits v1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)** specification to maintain a clean git history, enable automated semantic versioning, and streamline changelog generation.

---

## 1. Commit Message Structure

Each commit message consists of a **header**, an optional **body**, and an optional **footer**:

```text
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Constraints:
* The header must not exceed **72 characters**.
* Use the **imperative mood** in the description ("add", not "added" or "adds").
* Do not end the description with a period (`.`).
* Separate header, body, and footers with a blank line.

---

## 2. Commit Types

| Type | Purpose | Semantic Version Impact |
| :--- | :--- | :--- |
| `feat` | A new feature or user-facing capability | **MINOR** (`0.X.0`) |
| `fix` | A bug fix or calculation error correction | **PATCH** (`0.0.X`) |
| `perf` | Code change improving compute speed or query performance | **PATCH** (`0.0.X`) |
| `refactor`| Code restructuring without changing behavior | None / PATCH |
| `test` | Adding missing tests or refactoring test suites | None |
| `docs` | Documentation changes only | None |
| `style` | Formatting, whitespace, or visual polish (no logic change)| None |
| `build` | Changes to build system, Docker, Makefile, or npm scripts | None |
| `ci` | Changes to CI workflows (`.github/workflows/ci.yml`) | None |
| `chore` | Routine maintenance, dependencies, or repo hygiene | None |

---

## 3. Monorepo Scopes

In this monorepo, use scopes to identify which subsystem was modified:

* `(backend)`: FastAPI app, endpoints, or dependency injection
* `(frontend)`: React components, UI styling, charts, or state
* `(ingestion)`: Elexon BMRS client, date range chunker, data pipeline
* `(analytics)`: Trading metrics, MAE, RMSE, horizon decay, percentiles
* `(point-in-time)`: D-1 cutoff logic, information leakage prevention
* `(cache)`: Parquet storage, metadata, PyArrow loader
* `(docker)`: Dockerfile, docker-compose.yml, Nginx proxy
* `(ci)`: GitHub Actions workflows and pre-commit hooks

---

## 4. Breaking Changes

Breaking changes must be signaled in the header by placing an exclamation mark (`!`) before the colon, or by including a `BREAKING CHANGE:` footer:

```text
feat(backend)!: change default decision cutoff from 09:00 to 11:00 GMT

BREAKING CHANGE: The default D-1 decision cutoff for API queries is now 11:00 GMT (EPEX SPOT auction close) instead of 09:00 GMT.
```

---

## 5. Domain-Specific Examples

### Feature Additions (`feat`)
```text
feat(point-in-time): add configurable D-1 cutoff timestamp selector
feat(frontend): add settlement period diurnal profile chart
feat(analytics): compute P90 and P99 wind shortfall risk percentiles
```

### Bug Fixes (`fix`)
```text
fix(point-in-time): prevent look-ahead bias on delivery day forecasts
fix(ingestion): handle Elexon 7-day date window limit
fix(analytics): safely calculate lead time when publish timestamp is null
```

### Performance & Caching (`perf`)
```text
perf(cache): vectorize horizon decay calculation using pandas floor('h')
perf(backend): stream parquet queries into memory on application lifespan
```

### Testing & Quality (`test`)
```text
test(point-in-time): add test ensuring post-cutoff forecasts are excluded
test(metrics): add edge case test for empty forecast dataframes
```

### Documentation & Maintenance (`docs`, `chore`)
```text
docs(domain): document GB day-ahead auction timeline and gate closures
chore(deps): upgrade pandas to 3.1.0 and pyarrow to 26.0.0
```
