"""Dependency preflight — the operator's "Neo4j + Voyage up at all times" default mode.

Fast (sub-second when healthy), distinct from the heavy `doctor`. Verifies the dependency
chain and either auto-recovers a merely-stopped container or reports a clear, loud failure
— never a silent JSONL fallback.

Chain: Docker engine -> Neo4j container (auto `up` if stopped) -> bolt -> schema -> Voyage.
Policy: Neo4j is hard-required by default (config.require_neo4j); Voyage degrades to
keyword/BM25 with a visible warning unless config.require_voyage. We start the CONTAINER
but never Docker Desktop itself (heavy GUI) — that's reported with an instruction.

helios local patch — re-apply on re-vendor.
"""
import subprocess
import time


def _run(args, timeout=10):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
    except Exception as e:
        return 1, "", str(e)


def _docker_engine_up():
    rc, out, _ = _run(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=10)
    return rc == 0 and bool(out)


def _container_running(config):
    # `--filter name=` is an UNANCHORED substring match, so a different container
    # whose name merely contains ours (helios-neo4j-test) would read as running and
    # skip the auto-start of the real one. Anchor with ^...$ and confirm the exact name.
    name = config.neo4j_container_name
    rc, out, _ = _run(["docker", "ps", "--filter", f"name=^{name}$",
                       "--filter", "status=running", "--format", "{{.Names}}"], timeout=10)
    return rc == 0 and name in (out or "").split()


# preflight is ALWAYS-ON, so the auto-recovery path should not casually `compose up` whatever
# docker-compose.yml happens to sit in the current working directory. This sentinel is an ANTI-FOOTGUN, not a
# security boundary: it stops preflight from accidentally running an *unrelated* compose file, but it is a
# plaintext token an adversary could copy into a hostile file — it does not defend against a deliberate
# attacker who has studied memoryschema. The real boundary is "don't run memoryschema in an untrusted CWD."
# Note preflight prefers `docker start` (which executes NO file at all) and only reaches `compose up` on a
# genuine first-bootstrap of a missing container.
_COMPOSE_SENTINEL = "memoryschema-managed"


def _compose_is_trusted(compose_path):
    """True iff the compose file looks memoryschema-generated (carries the sentinel in its header). An
    anti-footgun gate on the automatic `compose up` — see the note above on why this is not an adversarial
    boundary."""
    try:
        with open(compose_path, encoding="utf-8", errors="replace") as f:
            head = f.read(4096)
    except OSError:
        return False
    return _COMPOSE_SENTINEL in head


def _start_container(config):
    """Recover the (existing) Neo4j container — never Docker Desktop, and not an unrecognized compose file.

    (1) `docker start <name>` first: recovers a merely-stopped named container and executes NO file — the
        common case. (Tradeoff: `docker start` does NOT reconcile against an edited docker-compose.yml; a
        deliberate config change is applied by the explicit `memoryschema neo4j up`, which recreates.)
    (2) Only if the container does not exist do we bootstrap via `docker compose up`, and only when the
        compose file carries the memoryschema sentinel (the anti-footgun gate above)."""
    rc, _, err = _run(["docker", "start", config.neo4j_container_name], timeout=30)
    if rc == 0:
        return True, ""
    compose = str(config.docker_compose_path)
    if not _compose_is_trusted(compose):
        return False, (f"Neo4j container '{config.neo4j_container_name}' is not present and {compose} is not "
                       f"a memoryschema-managed compose file — refusing to auto-run it. Bring it up in a "
                       f"trusted project (`memoryschema neo4j up` / `memoryschema init`).")
    rc, _, err = _run(["docker", "compose", "-f", compose, "up", "-d"], timeout=60)
    return rc == 0, err


def _wait_bolt(config, timeout=40):
    from memoryschema.neo4j_store import Neo4jMemoryStore
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        try:
            s = Neo4jMemoryStore(config=config)
            s.close()
            return True, ""
        except Exception as e:
            last = str(e)
            time.sleep(2)
    return False, last


def _bolt_and_schema(config):
    """(bolt_ok, schema_ok, detail) — connect (shared probe + auth wrap) and assert the
    memory_embedding vector index."""
    from memoryschema.neo4j_store import connect
    try:
        driver = connect(config=config)        # build + RETURN 1 probe + friendly auth error
    except Exception as e:
        return False, False, str(e)[:160]
    try:
        with driver.session() as s:
            names = [r["name"] for r in s.run("SHOW INDEXES YIELD name RETURN name")]
        return True, ("memory_embedding" in names), ""
    except Exception as e:
        return False, False, str(e)[:160]
    finally:
        driver.close()


def _voyage_ok(config):
    """(ok, detail) — a live 1-token embed (the real availability test)."""
    if not config.voyage_api_key:
        return False, "VOYAGE_API_KEY not set"
    try:
        from memoryschema.embeddings import embed_text
        t0 = time.time()
        vec = embed_text("ok", config=config)
        return (bool(vec), f"{len(vec)} dims ({time.time() - t0:.2f}s)")
    except Exception as e:
        return False, str(e)[:160]


def ensure_backend(config, auto_start=True, require=None):
    """Verify the default-mode dependency chain.

    Returns {ok, degraded, checks, failures, warnings, require} where each check is
    {name, ok, detail, hard}. `ok` is False iff a HARD-required dep failed; `degraded`
    is True if a soft dep (e.g. Voyage when not required) is down.
    """
    if require is None:
        require = (["neo4j"] if getattr(config, "require_neo4j", True) else []) + \
                  (["voyage"] if getattr(config, "require_voyage", False) else [])
    neo4j_hard = "neo4j" in require
    voyage_hard = "voyage" in require

    checks = []
    def add(name, ok, detail, hard):
        checks.append({"name": name, "ok": ok, "detail": detail, "hard": hard})

    # 1. Docker engine
    engine = _docker_engine_up()
    add("docker_engine", engine,
        "up" if engine else "DOWN — start Docker Desktop (not auto-started)", neo4j_hard)

    if not engine:
        add("neo4j", False, "unchecked — Docker engine down", neo4j_hard)
    else:
        # 2. container (auto-recover if merely stopped)
        running = _container_running(config)
        started = False
        if not running and auto_start:
            ok, _ = _start_container(config)
            if ok:
                running, _ = _wait_bolt(config, timeout=40)
                started = running
        detail = ("running" + (" (auto-started)" if started else "")) if running \
                 else "not running — run `memoryschema neo4j up`"
        add("neo4j_container", running, detail, neo4j_hard)

        # 3. bolt + schema
        bolt_ok, schema_ok, bdetail = (_bolt_and_schema(config) if running else (False, False, "container down"))
        add("neo4j_bolt", bolt_ok, "connected" if bolt_ok else (bdetail or "unreachable"), neo4j_hard)
        add("neo4j_schema", schema_ok,
            "memory_embedding present" if schema_ok else "missing — run `memoryschema neo4j schema`",
            False)  # schema is auto-creatable; not a hard gate on its own

    # 4. Voyage
    v_ok, v_detail = _voyage_ok(config)
    add("voyage", v_ok,
        v_detail if v_ok else (v_detail + " — embeddings degrade to keyword/BM25"), voyage_hard)

    failures = [c for c in checks if c["hard"] and not c["ok"]]
    warnings = [c for c in checks if not c["hard"] and not c["ok"]]
    return {"ok": not failures, "degraded": bool(warnings),
            "checks": checks, "failures": failures, "warnings": warnings, "require": require}


def format_report(result):
    """One-line-per-check human report."""
    lines = []
    for c in result["checks"]:
        mark = "✓" if c["ok"] else ("✗" if c["hard"] else "⚠")
        lines.append(f"  {mark} {c['name']:<16} {c['detail']}")
    if result["ok"]:
        lines.append("  preflight: OK" + (" (degraded)" if result["degraded"] else ""))
    else:
        lines.append("  preflight: FAIL — " + ", ".join(c["name"] for c in result["failures"]))
    return "\n".join(lines)
