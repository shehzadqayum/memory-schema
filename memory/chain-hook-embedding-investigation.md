<memory:entity schema="4" name="chain-hook-embedding-investigation" type="semantic" importance="7">
  <memory:description>Chain: hook embedding appeared broken but was actually a bash quoting issue — 4-step debugging sequence</memory:description>
  <memory:observations>
    <memory:observation>Step 1: Test write produced entry with no embedding — assumed VOYAGE_API_KEY not inherited by subprocess</memory:observation>
    <memory:observation>Step 2: Added config passthrough to embed_text (TOML fallback) — still no embedding</memory:observation>
    <memory:observation>Step 3: Added debug stderr prints to hook — discovered NameError from double-quoted dict key in bash python3 -c block</memory:observation>
    <memory:observation>Step 4: Verified env var IS available in subprocess, embed succeeds — the debug print itself caused the failure</memory:observation>
    <memory:observation>Conclusion: silent except:pass hid a bash quoting error, not an env var inheritance problem — wrong hypothesis wasted time</memory:observation>
  </memory:observations>
  <memory:prompt>Why weren't embeddings being computed in the PostToolUse hook?</memory:prompt>
  <memory:reasoning>The initial hypothesis (env var not inherited) was wrong. The actual cause (bash quoting corrupting Python code) was only found by adding error logging to the except block. The key lesson: debug silent except:pass by adding temporary error prints, not by assuming the guard condition failed.</memory:reasoning>
  <memory:relations>
    <memory:relation target="bash-python-quoting-rule" type="USES"/>
    <memory:relation target="hook-env-inheritance" type="USES"/>
    <memory:relation target="debug-silent-except-pattern" type="USES"/>
  </memory:relations>
</memory:entity>
