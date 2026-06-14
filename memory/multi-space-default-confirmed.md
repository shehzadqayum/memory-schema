<memory:entity schema="4" name="multi-space-default-confirmed" type="episodic" importance="2">
  <memory:description>Confirmed multi-space embedding is now the default hook behavior</memory:description>
  <memory:observations>
    <memory:observation>Every hook write produces 3 embedding spaces (default, observations, reasoning) with 1024 dims each</memory:observation>
    <memory:observation>No flag or configuration needed — it is the default behavior in hook-post-write.sh</memory:observation>
  </memory:observations>
</memory:entity>
