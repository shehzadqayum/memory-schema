"""Tests for recency-biased embedding composition + the provenance hash.

The defect under repair: head-slice [:2000] made accumulating fields embed
only their OLDEST content (chains represented step 1 from weeks ago).
"""

from memoryschema.embedding_input import (
    DEFAULT_MAX_CHARS,
    compose_embedding_text,
    compose_full_text,
    embed_input_hash,
)


def _chain_like(n_obs=100, obs_len=400, desc_len=3000):
    return {
        "name": "chain-big",
        "description": "D" * desc_len,
        "observations": ["Step %d: %s" % (i + 1, "x" * obs_len) for i in range(n_obs)],
        "prompt": "the trigger",
        "reasoning": "OLD." * 1000 + " NEWEST-REASONING-MARKER",
        "chain": "chain context",
    }


class TestObservationsTail:
    def test_newest_observations_embedded(self):
        e = _chain_like()
        text = compose_embedding_text(e, space="observations", max_chars=2000)
        assert "Step 100:" in text, "the NEWEST observation must be in the embed input"
        assert "Step 99:" in text
        assert "Step 2:" not in text, "weeks-old middle steps must not crowd the budget"

    def test_anchor_first_observation_when_room(self):
        e = _chain_like(n_obs=10, obs_len=50)
        text = compose_embedding_text(e, space="observations", max_chars=8000)
        # everything fits — all observations present in chronological order
        assert text.index("Step 1:") < text.index("Step 10:")

    def test_whole_observation_alignment(self):
        e = _chain_like(n_obs=100, obs_len=400)
        text = compose_embedding_text(e, space="observations", max_chars=2000)
        # No torn observation at the start: text starts at an observation boundary
        # (either the anchor "Step 1:" or the first picked tail observation).
        assert text.startswith("Step "), text[:40]

    def test_short_list_unchanged(self):
        e = {"name": "n", "observations": ["a", "b", "c"]}
        assert compose_embedding_text(e, space="observations") == "a b c"


class TestReasoningTail:
    def test_tail_kept(self):
        e = _chain_like()
        text = compose_embedding_text(e, space="reasoning", max_chars=500)
        assert "NEWEST-REASONING-MARKER" in text
        assert len(text) <= 500


class TestDefaultSpace:
    def test_default_includes_recent_observations(self):
        e = _chain_like(desc_len=3000)
        text = compose_embedding_text(e, space="default", max_chars=8000)
        assert "chain-big" in text
        assert "Step 100:" in text, "default space must carry the newest content"

    def test_default_cap_respected(self):
        e = _chain_like(desc_len=30000)
        text = compose_embedding_text(e, space="default", max_chars=8000)
        assert len(text) <= 8000

    def test_default_max_chars_raised(self):
        assert DEFAULT_MAX_CHARS >= 8000


class TestProvenanceHash:
    def test_deterministic(self):
        e = _chain_like()
        assert embed_input_hash(e) == embed_input_hash(dict(e))

    def test_any_field_change_changes_hash(self):
        e = _chain_like()
        h0 = embed_input_hash(e)
        e2 = dict(e)
        e2["observations"] = list(e["observations"]) + ["Step 101: new"]
        assert embed_input_hash(e2) != h0
        e3 = dict(e)
        e3["reasoning"] = e["reasoning"] + " more"
        assert embed_input_hash(e3) != h0

    def test_change_beyond_truncation_still_detected(self):
        """The old defect: a change past the cap was invisible to the drift key.
        The hash is over the FULL text, so it must change."""
        e = _chain_like(desc_len=30000)
        h0 = embed_input_hash(e)
        e2 = dict(e)
        e2["description"] = e["description"][:-1] + "Z"  # change at char 30000
        assert embed_input_hash(e2) != h0

    def test_full_text_field_separators(self):
        # 'ab'+'c' vs 'a'+'bc' must hash differently (separator prevents collisions)
        a = {"name": "ab", "description": "c"}
        b = {"name": "a", "description": "bc"}
        assert compose_full_text(a) != compose_full_text(b)


class TestBatchComposition:
    def test_embed_all_spaces_batches_and_maps(self):
        from memoryschema.spaces import embed_all_spaces
        e = _chain_like(n_obs=5, obs_len=20, desc_len=50)
        calls = []
        def fake(text):
            calls.append(text)
            return [float(len(text))] * 4
        emb, div = embed_all_spaces(e, embed_fn=fake)
        assert set(emb) == {"default", "name", "description", "observations",
                            "prompt", "reasoning", "chain"}
        # mapping correctness: the name-space vector reflects the name text length
        assert emb["name"][0] == float(len("chain-big"))
