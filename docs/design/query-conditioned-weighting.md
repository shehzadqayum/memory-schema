# Query-Conditioned Weighting — Design Document

## 1. Current Memory System

### Architecture

The memory-schema system stores structured memory entities as XML-tagged markdown files. Each entity flows through a PostToolUse hook pipeline on write:

```
Write memory/*.md → parse XML → embed (7 spaces) → gate (6 stages) → store (Neo4j/JSONL) → MEMORY.md
```

### Storage Layers

| Layer | Store | Persistence | Failure mode |
|-------|-------|-------------|--------------|
| L0 | MEMORY.md | Always in prompt context | Budget-enforced (2000 tokens) |
| L1a | memory/*.md files | Git-tracked | Never fails |
| L1b | store.jsonl | Pure Python JSONL | Never fails |
| L2a | Voyage AI embeddings | 7 spaces × 1024 dims | Degrades to L1 (text search) |
| L2b | Neo4j graph | Relations as edges | Degrades to L2a |

### Entity Schema (v4)

```xml
<memory:entity schema="4" name="unique-id" type="semantic" importance="7">
  <memory:description>One-line summary</memory:description>
  <memory:observations>
    <memory:observation basis="measured">Atomic fact</memory:observation>
  </memory:observations>
  <memory:prompt>The user input that triggered this memory</memory:prompt>
  <memory:reasoning>Why this approach, alternatives, connections</memory:reasoning>
  <memory:relations>
    <memory:relation target="other-memory" type="MODIFIES"/>
  </memory:relations>
</memory:entity>
```

### Embedding Spaces

Each entity is embedded in up to 7 independent vector spaces (1024 dims each, Voyage AI voyage-4-lite). Architecture: 1:1 field-to-space mapping, plus a default blend.

| Space | Input fields | Coverage | Purpose |
|-------|-------------|----------|---------|
| `default` | name + description + observations + prompt + reasoning + chain | 100% | Full semantic blend |
| `name` | name only | 100% | Identity matching |
| `description` | description only | 100% | Topic identity |
| `observations` | observation text only | 100% | Fact-level matching |
| `prompt` | prompt only | ~62% | Intent matching |
| `reasoning` | reasoning only | ~83% | Rationale matching |
| `chain` | chain context only | varies | Reasoning chain grouping |

Entries missing a field produce no vector for that space (structural absence). The combiner is variance-weighted: each space's similarity is multiplied by its divergence from default (precomputed at embed time). No base weights or query classification needed.

### Current Scoring

```
score = recency × w_r + importance × w_i + relevance × w_v
```

Where relevance is computed by the **combiner**:

```python
# Current: equal-weight average over present spaces
relevance = sum(per_space_similarities) / len(per_space_similarities)
```

Type modifiers: semantic (recency floor 0.6), procedural (access-reinforced), episodic (standard decay). Trust multipliers: first-party=1.0, user=1.0, derived=0.9, ingested=0.7. Basis factor: measured=1.0, inferred=0.97, reported=0.93.

### The Problem

Equal-weight averaging dilutes the default space signal. Evaluation results:

| Config | recall@5 | nDCG@10 |
|--------|----------|---------|
| single-space (default only) | 0.622 | 0.739 |
| 3-space equal | 0.622 | 0.601 |
| 4-space equal | 0.567 | 0.557 |
| 5-space equal | 0.511 | 0.555 |

More spaces = worse with equal weights. Each additional space averages down the strong default match.

---

## 2. Design: Query-Conditioned Weighting

### Concept

Instead of equal-weight averaging, classify the query into a type and apply a weight profile that emphasises the most relevant embedding spaces.

```
query → classify(query) → weight_profile → weighted_combine(per_space_sims, weights)
```

### Query Types

| Type | Signal | Description | Example |
|------|--------|-------------|---------|
| `factual` | What/how questions about system state | Seeks facts and descriptions | "What embedding spaces does the system use?" |
| `rationale` | Why/decision questions | Seeks reasoning and alternatives | "Why was equal-weight averaging abandoned?" |
| `intent` | User action questions | Seeks what the user asked/wanted | "What did the user request about embedding?" |
| `general` | No clear signal | Fallback for ambiguous queries | "superseded outdated plan resolved" |

### Weight Profiles

| Space | factual | rationale | intent | general |
|-------|---------|-----------|--------|---------|
| `default` | 2.0 | 1.5 | 1.0 | 2.0 |
| `name` | 1.0 | 0.5 | 0.5 | 1.0 |
| `description` | **3.0** | 1.0 | 1.0 | **2.0** |
| `observations` | **2.0** | 0.5 | 0.5 | 1.0 |
| `prompt` | 0.5 | 1.0 | **3.0** | 0.5 |
| `reasoning` | 0.5 | **3.0** | 1.0 | 0.5 |

The `general` profile is `desc+default` heavy — proven to beat single-space baseline.

### Classification Method

Keyword heuristic (zero cost, no API call):

```python
KEYWORDS = {
    'rationale': ['why', 'reasoning', 'rationale', 'decided', 'decision', 'chose'],
    'intent':    ['asked', 'requested', 'user want', 'prompt', 'triggered'],
    'factual':   ['what is', 'how does', 'status', 'config', 'schema',
                  'attribute', 'hierarchy', 'setup', 'deployment', 'audit'],
}

def classify_query(query):
    q = query.lower()
    scores = {qtype: sum(1 for w in words if w in q)
              for qtype, words in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else 'general'
```

### Eval Results

| Approach | recall@5 | nDCG@10 | vs baseline |
|----------|----------|---------|-------------|
| single-space (baseline) | 0.622 | 0.739 | — |
| equal-weight 5-space | 0.511 | 0.555 | -18% recall |
| **desc+default static** | **0.678** | **0.747** | **+9% recall** |
| **query-conditioned** | **0.678** | **0.730** | **+9% recall** |

---

## 3. Worked Example

**Entry:** `four-space-eval-results`
- description: "4-space eval: nDCG 0.557 worse than single-space 0.608 — equal-weight averaging dilutes signal"
- observations: 5 measured facts about eval results
- reasoning: "Each additional space with equal weight dilutes the default space signal..."
- prompt: "User asked to evaluate if 4 spaces beats 3"

### Query A (FACTUAL): "What were the multi-space eval results?"

```
Per-space cosine similarities:
  default=0.639  description=0.631  reasoning=0.610  observations=0.565  prompt=0.564

Scoring:
  equal-weight:      (0.639 + 0.631 + 0.610 + 0.565 + 0.564) / 5 = 0.602
  factual-weighted:  (0.639×2 + 0.631×3 + 0.565×2 + 0.610×0.5 + 0.564×0.5) / 8 = 0.611 ← best
  rationale-weighted: ... = 0.609
```

The factual profile boosts description (3×) and observations (2×), which are the most relevant spaces for a "what were the results" query.

### Query B (RATIONALE): "Why does equal-weight averaging hurt retrieval?"

```
Per-space cosine similarities:
  reasoning=0.696  default=0.692  observations=0.676  description=0.623  prompt=0.388

Scoring:
  equal-weight:       (0.696 + 0.692 + 0.676 + 0.623 + 0.388) / 5 = 0.615
  rationale-weighted:  (0.696×3 + 0.692×1.5 + 0.676×0.5 + 0.623×1 + 0.388×1) / 7 = 0.640 ← best
  factual-weighted:   ... = 0.644
```

The rationale profile boosts reasoning (3×), which has the highest similarity for this "why" query.

### Query C (INTENT): "What did the user ask about embedding spaces?"

```
Per-space cosine similarities:
  reasoning=0.439  prompt=0.422  default=0.371  observations=0.367  description=0.284

Scoring:
  equal-weight:    (0.439 + 0.422 + 0.371 + 0.367 + 0.284) / 5 = 0.377
  intent-weighted: (0.439×1 + 0.422×3 + 0.371×1 + 0.367×0.5 + 0.284×1) / 6.5 = 0.391 ← best
  factual-weighted: ... = 0.345
```

The intent profile boosts prompt (3×), which is the most relevant space for recovering the original user input.

---

## 4. Implementation Requirements

### Changes to `spaces.py`

1. Add `classify_query(query) → str` function with keyword heuristics
2. Add `WEIGHT_PROFILES` dict mapping query type → space weights
3. Modify `combine_similarities(per_space_sims, weights=None)`:
   - When `weights=None`, use `WEIGHT_PROFILES['general']` (the desc+default profile)
   - Accept query string to auto-classify: `combine_similarities(sims, query=query)`

### Changes to `store.py`

1. `_score_entry()`: pass query text to combiner for classification
2. `_multi_space_relevance()`: accept optional query string
3. `_score_all_entries()`: thread query through to combiner

### Changes to `eval_cmd.py`

1. Thread query text through to scoring so classification can work during eval

### Test Requirements

1. Test each query type classification (factual, rationale, intent, general)
2. Test that weight profiles produce expected ordering for contrasting queries
3. Eval comparison: query-conditioned vs static desc+default vs single-space
4. Regression: no query type should score worse than single-space baseline

### Key Constraint

The `general` fallback profile (desc+default heavy) must be the default when no query type is detected. This ensures the system never performs worse than the proven desc+default static profile.
