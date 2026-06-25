# memoryschema.toml — Agent configuration
# Values here are inherited by child agents. Parent always wins on conflict.

[project]
name = "{project_name}"

# [store]
# path = "memory/store.jsonl"

# [neo4j]
# uri = "bolt://localhost:7687"
# user = "neo4j"
# NOTE: password and api_key must come from environment variables:
#   NEO4J_PASSWORD, VOYAGE_API_KEY — never store secrets in TOML.

# [voyage]
# embed_model = "voyage-4-lite"

# [retrieval]
# recency_decay = 0.995
# recall_depth = 2
# recall_decay = 0.8
# l0_token_budget = 2000
# max_inherit_depth = 3
