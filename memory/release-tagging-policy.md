---
schema: 5
importance: 6
project: memory-schema
---

Tags are cut for CONSUMER-relevant content only; module-side tooling stays untagged on main

## Observations

- v0.1.0 = extraction release; v0.1.1 = fractal-feedback fixes (write-path config threading, hook parity). Untagged main content (ledger staleness detector, pip status semantics, re-stamp procedure) is module-side - consumers never run it, so no tag
- Next-tag candidates: hook->index_memory unification (behavioral consolidation -> v0.2.0), plugin sync --check scope-awareness, 250-entity milestone outcomes if defaults change, any consumer-surfaced bug
- Consumers pin tags (pip @ vX.Y.Z legible; raw shas defeat the point); helios switches subtree->pip at the next tag (plan: helios-pip-switch-at-next-tag in the helios store)
