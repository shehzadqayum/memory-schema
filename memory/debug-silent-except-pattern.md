<memory:entity schema="4" name="debug-silent-except-pattern" type="procedural" importance="8">
  <memory:description>Debug silent except:pass by adding temporary error prints, not by assuming the guard condition failed</memory:description>
  <memory:observations>
    <memory:observation basis="measured">Silent except:pass blocks hide the actual failure mode — you cannot distinguish guard-false from exception-caught</memory:observation>
    <memory:observation basis="measured">Adding temporary stderr prints reveals whether the code entered the try block and what exception occurred</memory:observation>
    <memory:observation>When debugging, print BEFORE the try (to confirm entry), INSIDE (to confirm success), and in except (to show error)</memory:observation>
  </memory:observations>
  <memory:prompt>Learned from hook embedding investigation where wrong assumption (env var missing) wasted time</memory:prompt>
  <memory:reasoning>The initial hypothesis was that VOYAGE_API_KEY wasn't available in the subprocess. Multiple approaches were tried based on this wrong assumption (TOML config, env file sourcing). The actual cause was only found by adding error logging to the except block, which revealed a NameError from bash quoting — a completely different failure mode.</memory:reasoning>
</memory:entity>
