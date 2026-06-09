<memory:entity schema="2" name="centralize-env-vars" type="semantic" importance="10">
  <memory:description>Plan to centralize os.environ reads into config.py — resolving session 1 residual</memory:description>
  <memory:observations>
    <memory:observation>5 direct os.environ reads outside config.py: 3 in neo4j_store.py, 2 in embeddings.py</memory:observation>
    <memory:observation>Fix: use MemoryConfig() as fallback when no config/params passed</memory:observation>
    <memory:observation>Plan at .claude/plans/velvet-purring-fern.md</memory:observation>
  </memory:observations>
  <memory:prompt>plan residuals</memory:prompt>
  <memory:reasoning>Addresses the only residual from S4 5fc565b. Removes dual env var read paths that can diverge between config.py and the module-level reads.</memory:reasoning>
  <memory:relations>
    <memory:relation target="session-1-close" type="DEPENDS_ON"/>
  </memory:relations>
  <memory:project>memory-schema</memory:project>
</memory:entity>
