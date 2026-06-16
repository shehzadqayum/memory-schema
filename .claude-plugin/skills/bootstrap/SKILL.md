# /bootstrap — Bootstrap project knowledge map

Systematically reads a project's documentation and source code after `memoryschema init`, creating interconnected memory entities that form a knowledge graph. Future sessions start with project context from the first recall.

## Usage

```
/bootstrap
```

## When to use

After running `memoryschema init` in a new or existing project. Creates initial memories so the memory system has project context rather than starting from zero.

Safe to re-run — entity names are deterministic, upsert semantics handle duplicates.

## Procedure

### Phase 0: Preflight

1. Verify the memory system is initialized:

```bash
memoryschema status
```

If this fails, run `memoryschema init --project <name> --scopes working` first.

2. Release any active chain, then start the bootstrap chain:

```bash
memoryschema chain release 2>/dev/null
memoryschema chain start "chain-bootstrap"
```

3. Detect the project name:

```bash
grep 'project_name' memoryschema.toml 2>/dev/null || basename "$PWD"
```

Use this as PROJECT_NAME in all entities below.

4. Check for existing bootstrap entities (idempotent re-run):

```bash
memoryschema recall "bootstrap project overview" --limit 3
```

If bootstrap entities already exist, this is a re-run — upserts will update them.

### Phase 1: Project Overview

Read these files (skip any that don't exist):

- `README.md` (or `README.rst`, `README`)
- Package manifest: `pyproject.toml` / `package.json` / `Cargo.toml` / `go.mod` / `pom.xml` / `Gemfile` / `build.gradle` — whichever exists
- `CHANGELOG.md` (first 50 lines for version/maturity)

Write `memory/bootstrap-project-overview.md`:

```xml
<memory:entity schema="4" name="bootstrap-project-overview" type="semantic" importance="8">
  <memory:description>Project overview: NAME — one-line what it does</memory:description>
  <memory:observations>
    <memory:observation>Language/framework: detected from manifest</memory:observation>
    <memory:observation>Purpose: from README</memory:observation>
    <memory:observation>Current version: if detectable</memory:observation>
    <memory:observation>License: if present</memory:observation>
    <memory:observation>Entry point: main file or command</memory:observation>
  </memory:observations>
  <memory:reasoning>Bootstrap scan of project documentation. This is the anchor entity for the project knowledge map.</memory:reasoning>
  <memory:chain>bootstrapping project knowledge map</memory:chain>
  <memory:project>PROJECT_NAME</memory:project>
</memory:entity>
```

Write the chain entity `memory/chain-bootstrap.md`:

```xml
<memory:entity schema="4" name="chain-bootstrap" type="semantic" importance="8">
  <memory:description>Chain: bootstrapping project knowledge map for PROJECT_NAME</memory:description>
  <memory:observations>
    <memory:observation>Step 1: Read project overview — README, package manifest</memory:observation>
  </memory:observations>
  <memory:prompt>User invoked /bootstrap to create initial project knowledge map</memory:prompt>
  <memory:reasoning>Systematic scan of project to create interconnected memory entities.</memory:reasoning>
  <memory:chain>bootstrapping project knowledge map</memory:chain>
  <memory:relations>
    <memory:relation target="bootstrap-project-overview" type="USES"/>
  </memory:relations>
  <memory:project>PROJECT_NAME</memory:project>
</memory:entity>
```

### Phase 2: Directory Structure

Scan the project:

```bash
find . -type f \( -name '*.py' -o -name '*.ts' -o -name '*.js' -o -name '*.go' -o -name '*.rs' -o -name '*.java' -o -name '*.rb' -o -name '*.swift' -o -name '*.kt' -o -name '*.c' -o -name '*.cpp' -o -name '*.h' \) -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/venv/*' -not -path '*/__pycache__/*' -not -path '*/dist/*' -not -path '*/build/*' | head -200
```

```bash
ls -la
```

Identify:
- **Source directories** (src/, lib/, app/, cmd/, internal/, etc.)
- **Test directories** (tests/, test/, spec/, __tests__/)
- **Documentation directories** (docs/, doc/)

Determine project size tier by counting top-level source directories:
- **Small** (<5 source dirs): deep scan in Phase 5
- **Medium** (5-15 source dirs): entry points only in Phase 5
- **Large** (>15 source dirs): top 15 modules only in Phase 5

Write `memory/bootstrap-directory-structure.md`:

```xml
<memory:entity schema="4" name="bootstrap-directory-structure" type="semantic" importance="7">
  <memory:description>Directory structure: N source dirs, M test dirs, K doc dirs</memory:description>
  <memory:observations>
    <memory:observation>Source: list of source directories</memory:observation>
    <memory:observation>Tests: list of test directories</memory:observation>
    <memory:observation>Docs: list of doc directories</memory:observation>
    <memory:observation>Size tier: small/medium/large (N source dirs)</memory:observation>
    <memory:observation>Total source files: approximate count from scan</memory:observation>
  </memory:observations>
  <memory:reasoning>Spatial orientation for the project. Identifies module boundaries and test coverage areas.</memory:reasoning>
  <memory:chain>bootstrapping project knowledge map</memory:chain>
  <memory:relations>
    <memory:relation target="bootstrap-project-overview" type="DEPENDS_ON"/>
  </memory:relations>
  <memory:project>PROJECT_NAME</memory:project>
</memory:entity>
```

Update chain entity — add Step 2 observation.

### Phase 3: Tech Stack

Read the package manifest identified in Phase 1. If a lock file exists (`package-lock.json`, `poetry.lock`, `Cargo.lock`, `go.sum`), scan it for version constraints.

Write `memory/bootstrap-tech-stack.md`:

```xml
<memory:entity schema="4" name="bootstrap-tech-stack" type="semantic" importance="7">
  <memory:description>Tech stack: language, framework, key dependencies</memory:description>
  <memory:observations>
    <memory:observation>Runtime deps: list key dependencies and their roles</memory:observation>
    <memory:observation>Dev deps: testing framework, linter, formatter</memory:observation>
    <memory:observation>Key framework: e.g., Express, Django, React, tokio</memory:observation>
    <memory:observation>Build tool: e.g., webpack, cargo, make, gradle</memory:observation>
  </memory:observations>
  <memory:reasoning>Understanding dependencies reveals architectural constraints and available abstractions.</memory:reasoning>
  <memory:chain>bootstrapping project knowledge map</memory:chain>
  <memory:relations>
    <memory:relation target="bootstrap-project-overview" type="DEPENDS_ON"/>
  </memory:relations>
  <memory:project>PROJECT_NAME</memory:project>
</memory:entity>
```

Update chain entity — add Step 3 observation.

### Phase 4: Configuration

Scan for config files:

```bash
ls -la .env* config/ *.config.* docker* Docker* Makefile justfile tsconfig* webpack* vite* 2>/dev/null
```

Read `.env.example` or `.env.sample` if present. Read `Dockerfile` and `docker-compose.yml` if present. Read build config files.

Write `memory/bootstrap-configuration.md`:

```xml
<memory:entity schema="4" name="bootstrap-configuration" type="semantic" importance="6">
  <memory:description>Configuration: env vars, config files, build setup</memory:description>
  <memory:observations>
    <memory:observation>Required env vars: list from .env.example</memory:observation>
    <memory:observation>Config files: list with purpose</memory:observation>
    <memory:observation>Docker: yes/no, services if present</memory:observation>
    <memory:observation>Build command: how to build/run</memory:observation>
    <memory:observation>Test command: how to run tests</memory:observation>
  </memory:observations>
  <memory:reasoning>Configuration knowledge accelerates debugging and onboarding. Required env vars are the most common missing-context blocker.</memory:reasoning>
  <memory:chain>bootstrapping project knowledge map</memory:chain>
  <memory:relations>
    <memory:relation target="bootstrap-project-overview" type="DEPENDS_ON"/>
  </memory:relations>
  <memory:project>PROJECT_NAME</memory:project>
</memory:entity>
```

Update chain entity — add Step 4 observation.

### Phase 5: Module Deep Dive

For each significant source directory identified in Phase 2, scaled by size tier:

- **Small** (<5 dirs): Read every source file's first 50 lines. One entity per directory.
- **Medium** (5-15 dirs): Read entry point / index files only (e.g., `__init__.py`, `index.ts`, `mod.rs`). One entity per top-level directory.
- **Large** (>15 dirs): Read only the top 15 modules (by file count or manifest references). Note skipped modules in the architecture entity.

For each module, write `memory/bootstrap-module-<name>.md`:

```xml
<memory:entity schema="4" name="bootstrap-module-NAME" type="semantic" importance="6">
  <memory:description>Module NAME: one-line responsibility</memory:description>
  <memory:observations>
    <memory:observation>Entry point: file path</memory:observation>
    <memory:observation>Key exports: public functions, classes, types</memory:observation>
    <memory:observation>Pattern: observed architectural pattern</memory:observation>
    <memory:observation>Dependencies: what this module imports from other modules</memory:observation>
  </memory:observations>
  <memory:reasoning>Why this module matters, what depends on it, what it depends on.</memory:reasoning>
  <memory:chain>bootstrapping project knowledge map</memory:chain>
  <memory:relations>
    <memory:relation target="bootstrap-project-overview" type="DEPENDS_ON"/>
    <memory:relation target="bootstrap-module-OTHER" type="USES"/>
  </memory:relations>
  <memory:project>PROJECT_NAME</memory:project>
</memory:entity>
```

Rules:
- Do not create entities for test files, build artifacts, or generated code
- If a module is just re-exports or a thin wrapper, mention it in the parent entity's observations instead
- Cap at 15 module entities maximum
- Add `USES` relations between modules where you observe import dependencies

Update chain entity after each module — add one observation per module.

### Phase 6: Architecture and API Surface

Synthesize patterns observed across all modules:

- Error handling patterns (exceptions, Result types, error codes)
- Naming conventions (camelCase, snake_case, module naming)
- Architectural patterns (MVC, repository, service layer, hexagonal, etc.)
- Testing patterns (unit, integration, mocking strategy)

Write `memory/bootstrap-architecture-patterns.md`:

```xml
<memory:entity schema="4" name="bootstrap-architecture-patterns" type="semantic" importance="8">
  <memory:description>Architecture patterns: conventions and structural patterns</memory:description>
  <memory:observations>
    <memory:observation>Pattern: identified architectural pattern</memory:observation>
    <memory:observation>Error handling: approach used</memory:observation>
    <memory:observation>Naming: conventions observed</memory:observation>
    <memory:observation>Testing: strategy and patterns</memory:observation>
  </memory:observations>
  <memory:reasoning>Understanding conventions prevents introducing inconsistencies. Architecture knowledge guides where to put new code.</memory:reasoning>
  <memory:chain>bootstrapping project knowledge map</memory:chain>
  <memory:relations>
    <memory:relation target="bootstrap-project-overview" type="DEPENDS_ON"/>
  </memory:relations>
  <memory:project>PROJECT_NAME</memory:project>
</memory:entity>
```

Identify the public API surface — endpoints, CLI commands, exported functions:

Write `memory/bootstrap-api-surface.md`:

```xml
<memory:entity schema="4" name="bootstrap-api-surface" type="semantic" importance="7">
  <memory:description>API surface: public endpoints, CLI commands, exports</memory:description>
  <memory:observations>
    <memory:observation>Endpoints: list if web service</memory:observation>
    <memory:observation>CLI commands: list if CLI tool</memory:observation>
    <memory:observation>Public exports: key functions/classes</memory:observation>
    <memory:observation>Entry points: how users interact with the system</memory:observation>
  </memory:observations>
  <memory:reasoning>The API surface defines what external users and other systems interact with. Changes here have the widest impact.</memory:reasoning>
  <memory:chain>bootstrapping project knowledge map</memory:chain>
  <memory:relations>
    <memory:relation target="bootstrap-project-overview" type="DEPENDS_ON"/>
  </memory:relations>
  <memory:project>PROJECT_NAME</memory:project>
</memory:entity>
```

Update chain entity — add Step 6 observations.

### Phase 7: Release and Report

1. Append a final Conclusion observation to the chain entity:

```
<memory:observation>Conclusion: Bootstrap complete — N entities created covering project overview, structure, tech stack, configuration, M modules, architecture, and API surface</memory:observation>
```

2. Release the chain:

```bash
memoryschema chain release
```

3. Verify:

```bash
memoryschema status
```

4. Present a summary to the user:

```
## Bootstrap Complete

**Project:** PROJECT_NAME
**Entities created:** N (1 chain + 7 structural + M modules)
**Store:** backend and count from status

### Knowledge Map
- bootstrap-project-overview (hub)
- bootstrap-directory-structure
- bootstrap-tech-stack
- bootstrap-configuration
- bootstrap-module-* (M modules)
- bootstrap-architecture-patterns
- bootstrap-api-surface
- chain-bootstrap (released)

### Relation Graph
(list key DEPENDS_ON and USES relations)

The project knowledge map is now available via /recall.
```

## Rules

- Entity names MUST use the `bootstrap-` prefix (chain uses `chain-bootstrap`)
- The `<memory:project>` field should match the project name from `memoryschema.toml`
- Do NOT create entities for test files, build artifacts, or generated code
- If a module is a thin wrapper or re-export only, mention it in the parent entity's observations
- Cap total entities at 22 (1 chain + 7 structural + up to 15 modules)
- Every entity MUST include `<memory:chain>bootstrapping project knowledge map</memory:chain>`
- Update the chain entity after every phase (append Step N observation)
- For monorepos: bootstrap the top level; individual sub-projects should run their own `/bootstrap`
- If hook errors occur during writes, run `memoryschema index` afterwards to batch-index
