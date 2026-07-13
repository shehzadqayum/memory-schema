---
schema: 5
importance: 6
---

Claude Code PostToolUse hook subprocesses inherit all parent env vars including VOYAGE_API_KEY

## Observations

- VOYAGE_API_KEY is available in the hook subprocess — verified by tracing os.environ.get in the hook's Python block
- NEO4J_PASSWORD is also inherited — hook successfully connects to Neo4j when password is set in parent shell
- Claude Code does not sanitize or strip env vars from hook subprocesses

## Reasoning

Initial assumption was that the hook subprocess didn't inherit VOYAGE_API_KEY. Testing proved the env var IS available. The actual failure was a bash quoting issue in a debug print that corrupted the Python code.

## Prompt

Investigation into why hook wasn't embedding — turned out env vars were available all along

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
