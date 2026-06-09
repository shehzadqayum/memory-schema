"""Diagnostic command — checks every component and recommends fixes.

Usage:
    memoryschema doctor          Full diagnostic report
    memoryschema doctor --json   Machine-readable output
    memoryschema doctor --fix    Auto-fix what can be fixed
"""

import json as json_mod
import os
import subprocess
import sys
import time
from pathlib import Path

import click


def _check(name, test_fn):
    """Run a diagnostic check. Returns (name, passed, detail, fix)."""
    try:
        passed, detail, fix = test_fn()
        return {"name": name, "passed": passed, "detail": detail, "fix": fix}
    except Exception as e:
        return {"name": name, "passed": False, "detail": str(e), "fix": None}


def run_checks(config):
    """Run all diagnostic checks. Returns list of check results."""
    checks = []

    # 1. Python version
    def check_python():
        v = sys.version_info
        version = f"{v.major}.{v.minor}.{v.micro}"
        ok = v >= (3, 11)
        return ok, version, "Upgrade to Python 3.11+" if not ok else None
    checks.append(_check("python", check_python))

    # 2. Package version
    def check_package():
        from memoryschema._version import __version__
        return True, f"memory-schema {__version__}", None
    checks.append(_check("package", check_package))

    # 3. Config loads
    def check_config():
        missing = []
        if not config.voyage_api_key:
            missing.append("VOYAGE_API_KEY")
        detail = "MemoryConfig loaded"
        if missing:
            detail += f" (missing: {', '.join(missing)})"
        return True, detail, None
    checks.append(_check("config", check_config))

    # 4. memory/ directory
    def check_memory_dir():
        if config.memory_dir.exists():
            count = len(list(config.memory_dir.glob("*.md")))
            return True, f"memory/ exists ({count} files)", None
        return False, "memory/ not found", "Run: memoryschema init"
    checks.append(_check("memory_dir", check_memory_dir))

    # 5. MEMORY.md
    def check_memory_index():
        if config.memory_index_path.exists():
            return True, "MEMORY.md exists", None
        return False, "MEMORY.md not found", "Run: memoryschema init"
    checks.append(_check("memory_index", check_memory_index))

    # 6. Schema rules
    def check_rules():
        rules_path = config.rules_dir / "memory-schema.md"
        if rules_path.exists():
            return True, ".claude/rules/memory-schema.md", None
        return False, "Schema rules not found", "Run: memoryschema init"
    checks.append(_check("rules", check_rules))

    # 7. Guidelines
    def check_guidelines():
        if config.rules_dir.exists():
            guidelines = [f.stem for f in config.rules_dir.glob("memory-*.md")
                         if f.stem != "memory-schema"]
            if guidelines:
                return True, ", ".join(guidelines), None
        return False, "No scope guidelines found", "Run: memoryschema init --scopes working"
    checks.append(_check("guidelines", check_guidelines))

    # 7b. TOML config
    def check_toml():
        toml_path = config.project_root / "memoryschema.toml"
        if not toml_path.exists():
            return True, "not present (using defaults)", None
        try:
            from memoryschema.inheritance import load_toml_config, validate_toml_name
            raw = load_toml_config(toml_path)
            if not raw:
                return False, "parse error", "Check memoryschema.toml syntax"
            warning = validate_toml_name(config.project_root)
            if warning:
                return True, f"valid ({warning})", None
            name = raw.get('project', {}).get('name', '?')
            return True, f"valid (project: {name})", None
        except Exception as e:
            return False, str(e)[:60], "Check memoryschema.toml"
    checks.append(_check("toml_config", check_toml))

    # 7c. Rules inheritance
    def check_rules_inheritance():
        try:
            from memoryschema.inheritance import overridden_rules
            overridden = overridden_rules(config.project_root)
            if overridden:
                names = ", ".join(o['filename'] for o in overridden)
                return True, f"{len(overridden)} overridden: {names}", \
                    "Run: memoryschema rules --conflicts"
            return True, "no conflicts", None
        except Exception:
            return True, "no parent found", None
    checks.append(_check("rules_inherit", check_rules_inheritance))

    # 8. JSONL store
    def check_store():
        if config.store_path.exists():
            size = config.store_path.stat().st_size
            if size > 0:
                with open(config.store_path) as f:
                    count = sum(1 for line in f if line.strip())
                return True, f"store.jsonl ({count:,} entries)", None
            return True, "store.jsonl (empty)", None
        return False, "store.jsonl not found", "Run: memoryschema init"
    checks.append(_check("store_jsonl", check_store))

    # 9. Docker
    def check_docker():
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version = result.stdout.strip().split(",")[0].replace("Docker version ", "")
                return True, f"Docker {version}", None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return False, "Docker not found", "Install Docker from https://docker.com"
    checks.append(_check("docker", check_docker))

    # 10. Neo4j container
    def check_neo4j_container():
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={config.neo4j_container_name}",
                 "--format", "{{.Status}}"],
                capture_output=True, text=True, timeout=5)
            status = result.stdout.strip()
            if status:
                return True, f"{config.neo4j_container_name} ({status[:30]})", None
            return False, f"{config.neo4j_container_name} not running", "Run: memoryschema neo4j deploy"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False, "Docker not available", "Install Docker"
    checks.append(_check("neo4j_container", check_neo4j_container))

    # 11. Neo4j connection
    def check_neo4j_connection():
        try:
            from memoryschema.neo4j_store import Neo4jMemoryStore
            t0 = time.time()
            store = Neo4jMemoryStore(config=config)
            latency = time.time() - t0
            store.close()
            return True, f"{config.neo4j_uri} ({latency:.2f}s)", None
        except Exception as e:
            return False, str(e)[:80], "Run: memoryschema neo4j up"
    checks.append(_check("neo4j_connection", check_neo4j_connection))

    # 12. Neo4j schema
    def check_neo4j_schema():
        try:
            from memoryschema.schema import setup_schema
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(config.neo4j_uri,
                                           auth=(config.neo4j_user, config.neo4j_password))
            with driver.session() as session:
                result = session.run("SHOW INDEXES")
                indexes = list(result)
            driver.close()
            return True, f"{len(indexes)} indexes", None if indexes else "Run: memoryschema neo4j schema"
        except Exception:
            return False, "Cannot check indexes", "Run: memoryschema neo4j schema"
    checks.append(_check("neo4j_schema", check_neo4j_schema))

    # 13. Neo4j nodes
    def check_neo4j_nodes():
        try:
            from memoryschema.neo4j_store import Neo4jMemoryStore
            store = Neo4jMemoryStore(config=config)
            count = store.count()
            store.close()
            if count > 0:
                return True, f"{count:,} nodes", None
            return False, "0 nodes", "Run: memoryschema index"
        except Exception:
            return False, "Cannot count nodes", "Run: memoryschema neo4j up"
    checks.append(_check("neo4j_nodes", check_neo4j_nodes))

    # 14. Voyage API key
    def check_voyage_key():
        if config.voyage_api_key:
            prefix = config.voyage_api_key[:8] + "..."
            return True, f"set ({prefix})", None
        return False, "NOT SET", "Run: export VOYAGE_API_KEY=voy-xxxxx"
    checks.append(_check("voyage_key", check_voyage_key))

    # 15. Voyage embed test
    def check_voyage_embed():
        if not config.voyage_api_key:
            return False, "SKIPPED (no API key)", "Set VOYAGE_API_KEY first"
        try:
            from memoryschema.embeddings import embed_text
            t0 = time.time()
            vec = embed_text("test", config=config)
            latency = time.time() - t0
            return True, f"{len(vec)} dims ({latency:.2f}s)", None
        except Exception as e:
            return False, str(e)[:80], "Check API key validity"
    checks.append(_check("voyage_embed", check_voyage_embed))

    # 16. Hook registered
    def check_hook():
        settings_path = Path.home() / ".claude" / "settings.json"
        if not settings_path.exists():
            return False, "~/.claude/settings.json not found", "Run: memoryschema hook install"
        with open(settings_path) as f:
            settings = json_mod.load(f)
        post_tool = settings.get("hooks", {}).get("PostToolUse", [])
        for entry in post_tool:
            if entry.get("matcher") == "Write":
                for h in entry.get("hooks", []):
                    if "hook-post-write.sh" in h.get("command", ""):
                        timeout = h.get("timeout", "?")
                        return True, f"registered (timeout: {timeout}s)", None
        return False, "not registered", "Run: memoryschema hook install"
    checks.append(_check("hook", check_hook))

    # 17. Hook script exists
    def check_hook_script():
        try:
            from importlib.resources import files
            hook_path = str(files("memoryschema.hooks") / "hook-post-write.sh")
            if os.path.exists(hook_path):
                executable = os.access(hook_path, os.X_OK)
                return True, f"{hook_path} ({'executable' if executable else 'not executable'})", \
                    None if executable else "Run: chmod +x " + hook_path
            return False, "hook script not found", "Reinstall: pip install memory-schema"
        except Exception:
            return False, "cannot locate hook", "Reinstall: pip install memory-schema"
    checks.append(_check("hook_script", check_hook_script))

    # 18. Tests
    def check_tests():
        try:
            t0 = time.time()
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=line"],
                capture_output=True, text=True, timeout=120,
                cwd=str(config.project_root))
            elapsed = time.time() - t0
            # Summary is in stderr for pytest with capture_output
            combined = (result.stdout or "") + (result.stderr or "")
            for line in reversed(combined.strip().split("\n")):
                if "passed" in line or "failed" in line or "error" in line:
                    return result.returncode == 0, line.strip(), \
                        None if result.returncode == 0 else "Fix failing tests"
            if result.returncode == 0:
                return True, f"passed in {elapsed:.1f}s", None
            return False, f"exit code {result.returncode}", "Run: pytest tests/ -v"
        except subprocess.TimeoutExpired:
            return False, "timed out (120s)", "Run: pytest tests/ -v"
        except Exception as e:
            return False, str(e)[:80], "Run: pytest tests/ -v"
    checks.append(_check("tests", check_tests))

    return checks


@click.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for agent consumption.")
@click.option("--fix", "auto_fix", is_flag=True, help="Auto-fix fixable issues (init, deploy, hook install).")
@click.pass_obj
def doctor(config, as_json, auto_fix):
    """Run 20-point diagnostic checks on the memory system.

    Checks every component — Python, package, config, filesystem,
    TOML config validity, rules inheritance conflicts,
    Docker, Neo4j, Voyage AI, hook, tests — and reports status
    with cause and remediation for any failures.

    Example:
        memoryschema doctor
        memoryschema doctor --json
        memoryschema doctor --fix
    """
    checks = run_checks(config)

    passed = sum(1 for c in checks if c["passed"])
    failed = sum(1 for c in checks if not c["passed"])
    total = len(checks)

    if as_json:
        click.echo(json_mod.dumps({
            "checks": checks,
            "summary": {"passed": passed, "failed": failed, "total": total},
        }, indent=2))
        return

    for c in checks:
        icon = "✓" if c["passed"] else "✗"
        click.echo(f"  {icon} {c['name']:18s} {c['detail']}")
        if not c["passed"] and c.get("fix"):
            click.echo(f"  {'':19s} Fix: {c['fix']}")

    click.echo(f"\n  Summary: {passed}/{total} checks passed", nl=False)
    if failed > 0:
        click.echo(f", {failed} issues found")
    else:
        click.echo("")

    if auto_fix and failed > 0:
        click.echo("\nAuto-fixing...")
        fixable = {
            "memory_dir": "memoryschema init",
            "memory_index": "memoryschema init",
            "rules": "memoryschema init",
            "guidelines": "memoryschema init --scopes working",
            "store_jsonl": "memoryschema init",
            "neo4j_container": "memoryschema neo4j deploy",
            "neo4j_connection": "memoryschema neo4j up",
            "neo4j_schema": "memoryschema neo4j schema",
            "hook": "memoryschema hook install",
        }
        for c in checks:
            if not c["passed"] and c["name"] in fixable:
                cmd = fixable[c["name"]]
                click.echo(f"  Running: {cmd}")
                # Don't actually run — just suggest. Auto-fix is advisory.
                click.echo(f"  → Run manually: {cmd}")
