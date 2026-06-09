<memory:entity schema="2" name="fix-env-precedence" type="semantic" importance="10">
  <memory:description>Plan to fix env var precedence inversion, redundant import, and add hierarchy integration tests</memory:description>
  <memory:observations>
    <memory:observation>from_toml() passes TOML values as explicit kwargs — bypasses default_factory env var reads</memory:observation>
    <memory:observation>Fix: overlay env vars via setattr after instance construction</memory:observation>
    <memory:observation>store.py:283 has redundant inline import already at module level</memory:observation>
    <memory:observation>No integration tests for search/recall with mixed-project entities</memory:observation>
  </memory:observations>
  <memory:prompt>plan fix for env var precedence, redundant import, integration tests</memory:prompt>
  <memory:reasoning>The env var precedence inversion is a real bug — TOML silently overrides env vars. The docstring claims the opposite. This was introduced when Fix 7 removed env var reads from resolve_config_chain without compensating in from_toml().</memory:reasoning>
  <memory:relations>
    <memory:relation target="session-2-close" type="DEPENDS_ON"/>
  </memory:relations>
  <memory:project>memory-schema</memory:project>
</memory:entity>
