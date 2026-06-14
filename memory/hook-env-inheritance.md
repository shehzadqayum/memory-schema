<memory:entity schema="4" name="hook-env-inheritance" type="semantic" importance="6">
  <memory:description>Claude Code PostToolUse hook subprocesses inherit all parent env vars including VOYAGE_API_KEY</memory:description>
  <memory:observations>
    <memory:observation basis="measured">VOYAGE_API_KEY is available in the hook subprocess — verified by tracing os.environ.get in the hook's Python block</memory:observation>
    <memory:observation basis="measured">NEO4J_PASSWORD is also inherited — hook successfully connects to Neo4j when password is set in parent shell</memory:observation>
    <memory:observation basis="inferred">Claude Code does not sanitize or strip env vars from hook subprocesses</memory:observation>
  </memory:observations>
  <memory:prompt>Investigation into why hook wasn't embedding — turned out env vars were available all along</memory:prompt>
  <memory:reasoning>Initial assumption was that the hook subprocess didn't inherit VOYAGE_API_KEY. Testing proved the env var IS available. The actual failure was a bash quoting issue in a debug print that corrupted the Python code.</memory:reasoning>
</memory:entity>
