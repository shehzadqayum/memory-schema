---
schema: 5
type: procedural
importance: 7
---

Never use double-quoted dict keys in f-strings inside bash python3 -c blocks

## Observations

- Double quotes in f-string expressions like memory["embedding"] terminate the bash string in python3 -c "..." blocks
- The except Exception: pass pattern silently swallows the resulting NameError, making the failure invisible
- Use single quotes for dict access inside these blocks: memory['embedding'] works, memory["embedding"] breaks

## Reasoning

Spent significant time investigating why embeddings weren't computed on write. The root cause was a debug f-string using double-quoted dict keys inside the hook's python3 -c block. The bash shell interpreted the inner double quotes as ending the python3 -c argument string, corrupting the Python code. The except: pass caught the error silently.

## Prompt

Debugging session where hook embedding appeared broken but was actually a quoting issue

## Notes

Migrated from genesis 2026-07-13 (extraction seeding).
