<memory:entity schema="4" name="system-status-snapshot" type="semantic" importance="5">
  <memory:description>Memory system snapshot: 56 entries, 4 embedding spaces, 659 tests, single-space scoring best</memory:description>
  <memory:observations>
    <memory:observation basis="measured">56 entries (47 active, 9 superseded), 6150 KB store, 41 entries in MEMORY.md (1421/2000 token budget)</memory:observation>
    <memory:observation basis="measured">All 56 entries embedded: 48 with 4 spaces, 8 with 3 (no reasoning text)</memory:observation>
    <memory:observation basis="measured">266 total observations, 54 with basis attribute (45 measured, 5 reported, 4 inferred)</memory:observation>
    <memory:observation basis="measured">55 relations (18 DEPENDS_ON, 17 MODIFIES, 14 SUPERSEDES, 6 USES), 560 k-NN associations</memory:observation>
    <memory:observation basis="measured">Eval: single-space best (nDCG 0.608), multi-space worse (3-space 0.601, 4-space 0.557)</memory:observation>
  </memory:observations>
  <memory:reasoning>The system is fully operational with rich metadata. The key finding remains: equal-weight multi-space averaging dilutes the default signal. The infrastructure for 4 spaces is in place but scoring should use single-space (default only) until query-conditioned weighting is implemented.</memory:reasoning>
</memory:entity>
