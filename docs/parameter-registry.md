# Epistemic Parameter Registry

> Every tunable epistemic parameter in the package: the thresholds, weights, decays, caps, windows,

**53 parameters** — 23 retrieval-ranking, 9 write-integrity, 8 lifecycle, 8 budget, 5 telemetry-window. (Since this audit, `gate.l0_echo_threshold`, `gate.numeric_probe_mode`, `gate.numeric_probe_enabled`, and `retrieval.mitigation_dampening` gained TOML keys.)
> and budgets that decide what gets WRITTEN (gate), RECALLED (scoring/ranking), or RETIRED
> (lifecycle/consolidation). These are **policy, not implementation detail** — miscalibration risks
> knowledge suppression (a memory that never surfaces, is never written, or is wrongly retired).
> Generated from the 2026-07-12 gate-tuning audit; regenerate when a parameter is added or moved.
>
> **Legibility rule:** a HIGH-suppression-risk parameter should be config-exposed (TOML) or carry a
> written justification for staying hardcoded. Tuning any parameter follows the calibration protocol
> (pre-committed thresholds, paired replay — see the gate-tuning evaluation in the memory store).
>
> ⚠ `recency_decay` (0.995/hr score decay) and `recall_decay` (0.8 per-hop BFS decay) are DIFFERENT
> parameters; note that LOWERING `recency_decay` decays FASTER (tightens), not looser.

## retrieval-ranking (23)

| param | where | default | config key | risk | effect |
|---|---|---|---|---|---|
| `recall_seed_count` | store.py:980 | 3 (scored[:3]; neo4j_store.py:498 to | HARDCODED | HIGH | Only the top-3 scored/vector-matched entries seed the activation cascade; everything else must be graph-reachable from them within recall_depth hops. |
| `semantic_weights` | config.py:106 | (0.2, 0.3, 0.5) | retrieval.semantic_weights | HIGH | (recency, importance, relevance) blend for semantic-mode scoring — the default mode for recall — resolved via store._resolve_weights (store.py:43) for |
| `as_of_overfetch` | cli/memory_cmd.py:79 | max(limit*4, 20) | HARDCODED | med | Point-in-time (--as-of) recall over-fetches before the temporal validity filter, then truncates back to limit. |
| `association_k` | config.py:98 | 10 | retrieval.association_k | med | k-NN neighbour count for ASSOCIATED_WITH edges (compute_associations, both stores; also CLI --k default index_cmd.py:138) — the association channel of |
| `bm25_boost_cap` | store.py:730 | min(score*0.1, 0.3) | HARDCODED | med | BM25 keyword score is scaled by 0.1 and capped at +0.3 before being added to the blend score (JSONL store only; Neo4j uses fulltext + a flat +0.1 inst |
| `embed_dimensions / embed_model / rerank_model` | config.py:61 | 1024 / voyage-4-lite / rerank-2 | voyage.embed_dimensions / voyage.embed_model / voyage.rera | med | Embedding vector size and Voyage model identities — the semantic substrate all cosine scores stand on. |
| `max_inherit_depth` | config.py:101 | 3 | retrieval.max_inherit_depth | med | Max project-hierarchy levels for scope matching in scoped recall (store.py:950, neo4j_store.py:591 post-filter). |
| `neo4j_scoped_vector_widening` | neo4j_store.py:697 | oversample multipliers (3, 9, 100) | HARDCODED | med | Project-scoped vector seed search over-fetches 3x/9x/100x and post-filters; stops widening once top_k survive. |
| `no_embedding_weight_redistribution` | store.py:816 | w_r += w_v*0.4; w_i += w_v*0.6 | HARDCODED (also neo4j_store.py:853-855) | med | When an entry has no embedding (or no query embedding), the relevance weight is redistributed 40% to recency / 60% to importance. |
| `recall_decay` | config.py:100 | 0.8 | retrieval.recall_decay | med | Per-hop score multiplier in the activation cascade (hop_score = parent_score * decay; store.py:1009, neo4j_store.py:547). |
| `recall_depth` | config.py:99 | 2 | retrieval.recall_depth | med | Max BFS hops of spreading activation from the seeds through relations/backlinks/associations (store.recall depth param; CLI passes config value at mem |
| `recency_decay` | config.py:97 | 0.995 | retrieval.recency_decay | med | Hourly exponential decay base for the recency component of every retrieval score (decay**hours since last_accessed); used identically in store.py:778  |
| `rerank_candidate_pool` | store.py:1081 | limit * 3 | HARDCODED | med | Only the top limit*3 cascade results are handed to the Voyage reranker; the reranker cannot resurrect anything below that line. |
| `semantic_recency_floor` | store.py:786 | 0.6 | HARDCODED (also neo4j_store.py:828) | med | Recency component of type=semantic entries never drops below 0.6 — persistent knowledge is exempt from full decay. |
| `structured_weights` | config.py:107 | (0.3, 0.5, 0.2) | retrieval.structured_weights | med | (recency, importance, relevance) blend for structured-mode queries (importance-led). |
| `bm25_k1_b_avgdl` | store.py:700 | k1=1.2, b=0.75, avg_dl=50 | HARDCODED | low | BM25 term-saturation and length-normalization constants for the keyword boost in JSONL seed scoring. |
| `combiner_default_space_weight` | spaces.py:89 | 1.0 | HARDCODED | low | In variance-weighted multi-space relevance the 'default' blend space always contributes with weight 1.0; field spaces contribute by their divergence f |
| `hub_bonus` | store.py:824 | 0.05 * log(1+backlinks) | HARDCODED (also neo4j_store.py:862) | low | Log-scale additive bonus for entries with inbound relations (hub memories), capped implicitly by the min(score,1.0) clamp. |
| `importance_default` | store.py:797 | 5 (normalized /10) | HARDCODED (also neo4j_store.py:835; display default memory | low | Entries without an importance get 0.5 on the importance axis of every score and rank mid-pack in the L0 index. |
| `mitigation_dampening` | config.py:103 | 0.95 | CONFIG FIELD mitigation_dampening, no TOML key (HARDCODED  | low | Score multiplier applied to entries with inbound MITIGATES backlinks (store.py:836, neo4j_store.py:872). |
| `neo4j_seed_keyword_bonus` | neo4j_store.py:520 | +0.1 (cap 1.0) | HARDCODED | low | Flat bonus when the query substring appears in a seed's searchable text (Neo4j backend only — a scoring-parity divergence from the JSONL BM25 boost). |
| `procedural_access_reinforcement` | store.py:793 | exponent = 1/(1 + 0.3*min(access_cou | HARDCODED (factor 0.3, cap 10; also neo4j_store.py:831) | low | Frequently accessed procedural entries decay slower (exponent 1.0 at 0 accesses down to 0.25 at 10+). |
| `rerank_limit_default` | embeddings.py:90 | 5 | HARDCODED (function default; recall passes its own limit) | low | Default top_k for the Voyage rerank-2 call when no limit is passed. |

**High-risk rationale:**
- `recall_seed_count` — The single hardest reachability gate in recall: a relevant but 4th-ranked, graph-isolated memory NEVER surfaces for that query, at any --limit.
- `semantic_weights` — Miscalibration directly reorders every recall; dropping the relevance weight makes topically-perfect but old/low-importance memories permanently lose the 3 seed slots and never surface.

## write-integrity (9)

| param | where | default | config key | risk | effect |
|---|---|---|---|---|---|
| `l0_echo_threshold` | config.py:113 | 0.6 (read at write_gate.py:143, comp | CONFIG FIELD l0_echo_threshold, no TOML key (HARDCODED def | HIGH | Jaccard content-word overlap vs any MEMORY.md entry description above which a new active entry with no external relations is QUARANTINED as an L0 echo |
| `numeric_probe_mode` | config.py:111 | 'log' (read at write_gate.py:142, br | CONFIG FIELD numeric_probe_mode, no TOML key (HARDCODED de | HIGH | 'log' = numeric contradictions become warnings (burn-in); 'quarantine' = they quarantine the write. |
| `consistency_near_dup_threshold` | write_gate.py:340 | 0.95 (strict mode only) | HARDCODED | med | Gate stage 2: in strict mode, an embedded candidate >0.95 cosine to an existing entry with a DIFFERENT description is QUARANTINED as a near-duplicate. |
| `hook_timeout` | cli/hook_cmd.py:41 | 10 seconds | HARDCODED (CLI --timeout default, written into settings.js | med | PostToolUse hook timeout — the window in which a hand-edited memory file must parse+embed+gate+dual-write. |
| `numeric_probe_sim_threshold` | config.py:112 | 0.80 (read at write_gate.py:153) | CONFIG FIELD numeric_probe_sim_threshold, no TOML key (HAR | med | Cosine similarity above which an existing active entry counts as a 'neighbour' whose numeric claims are compared against the candidate's. |
| `desc_length_nudge` | write_gate.py:93 | 120 chars | HARDCODED | low | Warn-only nudge when a non-chain description exceeds 120 chars (chains exempt). |
| `importance_mode_nudge` | write_gate.py:105 | store>=10 entries AND mode fraction  | HARDCODED (thresholds at write_gate.py:100 and :105) | low | Warn-only nudge when the declared importance equals the store's modal value and that mode covers >40% of entries (anti-7-inflation). |
| `numeric_probe_enabled` | config.py:110 | True | CONFIG FIELD numeric_probe_enabled, no TOML key (HARDCODED | low | Master switch for gate stage 5 (numeric contradiction detection against >=0.80-cosine neighbours). |
| `reconcile_shrink_guard` | reconcile.py:35 | 0.5 (_SHRINK_GUARD_FRACTION) | HARDCODED | low | Reconcile refuses to rebuild the stores when the parsed .md set has collapsed below 50% of the existing JSONL (wipe protection). |

**High-risk rationale:**
- `l0_echo_threshold` — The strongest write suppressor: too low and legitimate topical follow-ups are quarantined (unembedded, excluded from recall and L0) until manually released; the SUPERSEDES/self exemptions are the only escape valves.
- `numeric_probe_mode` — Flipping to 'quarantine' hands write-veto power to a deliberately heuristic regex extractor — legitimate updated counts ('457 trades' vs '412 trades') would quarantine unless SUPERSEDES/CONTRADICTS is declared.

## lifecycle (8)

| param | where | default | config key | risk | effect |
|---|---|---|---|---|---|
| `never_surfaced_grace_days` | dream_report.py:29 | 7 (NEVER_SURFACED_GRACE_DAYS) | HARDCODED | HIGH | Active non-chain entities older than 7 days with ZERO appearances in the recall log are reported as dead-weight archival candidates. |
| `reflect_score_threshold` | consolidation.py:93 | 0.7 (CLI default cli/reflect_cmd.py: | HARDCODED (CLI-overridable per run) | HIGH | Minimum association score for an edge when clustering episodic entries for reflection; each resulting cluster is synthesized into a semantic summary t |
| `dream_dup_cosine` | dream_report.py:26 | 0.80 (DUP_COSINE) | HARDCODED | med | Default-space cosine above which an active entity pair is reported as a merge candidate in the dream-pass report (LLM then judges). |
| `reflect_cluster_bounds` | consolidation.py:92 | min_cluster=2, max_cluster=10 | HARDCODED (CLI-overridable cli/reflect_cmd.py:10-11) | med | Only association components sized 2..10 are consolidated; smaller/larger components are left untouched. |
| `reflect_summary_content_caps` | consolidation.py:196 | observations[:10]; mechanical-fallba | HARDCODED (desc cap at consolidation.py:174) | med | The synthesized summary keeps at most 10 deduplicated observations (and, without an LLM, only the first 5 descriptions) from the archived cluster. |
| `chain_obs_rotation` | dream_report.py:28 | 40 (CHAIN_OBS_ROTATION) | HARDCODED | low | Active chain past 40 observations is flagged oversized (conclude/release/start successor). |
| `dream_stale_days` | dream_report.py:27 | 14 (STALE_DAYS) | HARDCODED | low | Keyed facts with valid_from older than 14 days and never superseded are flagged 'stale keyed' for review. |
| `promotion_citation_threshold` | dream_report.py:191 | >= 3 citations | HARDCODED | low | Entities cited 3+ times (or type=procedural) and not yet promoted are flagged as promotion candidates into standing surfaces. |

**High-risk rationale:**
- `never_surfaced_grace_days` — The report's archival suggestion inherits the recall log's top-10-hits blind spot — a real-but-low-ranked memory looks never-surfaced and can be wrongly retired by the dream session.
- `reflect_score_threshold` — Too low merges unrelated episodes into one summary that then retires them all (archive + SUPERSEDES = out of recall); the contradiction pre-check is the only brake.

## budget (8)

| param | where | default | config key | risk | effect |
|---|---|---|---|---|---|
| `embedding_input_max_chars` | embedding_input.py:22 | 8000 (DEFAULT_MAX_CHARS) | HARDCODED | HIGH | Truncation budget per embedding space; default space = name+description+summary+NEWEST observations (recency-biased tail), reasoning takes its tail. |
| `l0_token_budget` | config.py:94 | 2000 (also l0_budget.py:17 DEFAULT_T | retrieval.l0_token_budget | HIGH | Token cap for MEMORY.md (the always-in-context L0 index); rebuild_index drops the lowest-importance ACTIVE entries when over budget (l0_budget.py:268) |
| `recall_cli_limit` | cli/memory_cmd.py:54 | 10 | HARDCODED (CLI --limit default; kernel habit uses --limit  | med | Default number of recall results returned to the LLM. |
| `embed_batch_size` | cli/index_cmd.py:58 | 20 | HARDCODED (CLI --batch-size default) | low | Texts per Voyage API call during bulk index --embed. |
| `l0_desc_width` | l0_budget.py:197 | 160 (_L0_DESC_WIDTH) | HARDCODED | low | Per-entry description truncation on L0 index lines. |
| `l0_rank_importance_default` | l0_budget.py:213 | 5 | HARDCODED | low | L0 index ordering is importance DESC then name ASC (_rank_key); unrated entries rank as 5 and are mid-list for budget eviction. |
| `l0_token_estimator` | l0_budget.py:21 | len(text) // 4 | HARDCODED | low | Chars/4 token approximation used by both enforce_budget and rebuild_index. |
| `search_cli_limits` | cli/memory_cmd.py:249 | search 20; list/others 10 (memory_cm | HARDCODED (CLI defaults) | low | Default result caps for the substring/fulltext search and list commands. |

**High-risk rationale:**
- `embedding_input_max_chars` — Content that never fits the composed 8000 chars is semantically invisible forever — the previous 2000-char head-slice value caused the measured 'session recall misses' defect this comment documents.
- `l0_token_budget` — A dropped entry loses its ambient-context presence entirely — it exists only behind explicit recall, and low-importance entries are exactly the ones nobody thinks to recall.

## telemetry-window (5)

| param | where | default | config key | risk | effect |
|---|---|---|---|---|---|
| `recall_log_hits_cap` | recall_log.py:42 | [:10] hits per event | HARDCODED | HIGH | Each recall event logs only its top-10 hits; the surfaced-set for never_surfaced/attribution analysis is built from these. |
| `attribution_noise_threshold` | attribution.py:118 | recalls >= 3 AND citations == 0 | HARDCODED | med | Definition of 'recalled_never_cited' (retrieval-noise candidates surfaced in the dream report's attribution_review, top_attributed capped [:10] at :12 |
| `cite_window_hours` | attribution.py:23 | 24 (CITE_WINDOW_HOURS) | HARDCODED | med | A citation counts as 'attributed' to a recall only if it occurs within 24h after that recall; feeds attribution_rate. |
| `strong_hit_threshold` | recall_log.py:69 | 0.5 (CLI --strong default cli/memory | HARDCODED (CLI-overridable) | low | Top-score cutoff for counting a recall event as a 'strong hit' in recall-stats. |
| `verification_staleness_days` | config.py:102 | 7 (used cli/memory_cmd.py:120) | CONFIG FIELD verification_staleness_days, no TOML key (HAR | low | Age threshold after which a verified_at timestamp is displayed as stale in show output. |

**High-risk rationale:**
- `recall_log_hits_cap` — A memory that consistently ranks 11+ is telemetrically 'never surfaced' and becomes a dream-pass archival candidate despite actually appearing in results — a silent retire pipeline.

## Known systemic couplings (from the audit)

- Recall seeds are hardcoded top-3 (store.py:980, neo4j_store.py:498) — a relevant memory outside the top-3 seed set AND not graph-reachable within recall_depth hops can never surface regardless of limit
- The recall log records only the top-10 hits per event (recall_log.py:42) and dream_report's never_surfaced archival candidates are computed from that log, so a memory that consistently surfaces at rank 11+ is reported as dead weight — a telemetry-window→lifecycle suppression pipeline
- The L0-echo probe (threshold 0.6 Jaccard) quarantines the write (status=quarantined, embeddings stripped, excluded from recall/L0) — the single highest write-suppression lever
- Gate stage 2 (0.95 near-dup) runs only in strict mode, which no production caller (write_index.index_memory, the hook) enables — it is currently dormant
- Numeric_probe_mode defaults to 'log' (burn-in), so numeric contradictions currently warn, not quarantine — flipping to 'quarantine' raises write-suppression risk on the heuristic extractor.
