"""Schema validation commands."""

import sys

import click


@click.command("validate")
@click.argument("path", required=False)
@click.option("--strict", is_flag=True, help="Include content quality checks (Q1-Q7).")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for agent consumption.")
@click.pass_obj
def validate(config, path, strict, as_json):
    """Validate memory files against schema (V1-V10, R1-R5, F1-F3).

    If PATH is a file, validates that file. If a directory, validates
    all .md files in it. If omitted, validates memory/ directory.

    Example:
        memoryschema validate
        memoryschema validate memory/my-memory.md --strict
        memoryschema validate memory/ --json
    """
    import json as json_mod
    import os
    from memoryschema.validator import validate as _validate, validate_file, validate_directory

    if path is None:
        path = str(config.memory_dir)

    if not os.path.exists(path):
        click.echo(f"Error: Path not found: {path}", err=True)
        click.echo(f"Fix: Run 'memoryschema init' to create the memory directory.", err=True)
        sys.exit(1)

    if os.path.isfile(path):
        with open(path) as f:
            content = f.read()
        errors = _validate(content, path, strict=strict)
        if as_json:
            click.echo(json_mod.dumps({path: [(r, m) for r, m in errors]}))
        elif errors:
            click.echo(f"{path}:")
            for rule, msg in errors:
                click.echo(f"  [{rule}] {msg}")
            sys.exit(1)
        else:
            click.echo(f"{path}: valid")
    else:
        results = validate_directory(path)
        total_files = len([f for f in os.listdir(path)
                          if f.endswith('.md') and f != 'MEMORY.md'])
        error_files = len(results)

        if as_json:
            click.echo(json_mod.dumps({fp: [(r, m) for r, m in errs]
                                       for fp, errs in results.items()}))
        elif results:
            click.echo(f"Validated {total_files} files, {error_files} with errors:")
            for fp, errs in results.items():
                click.echo(f"\n  {os.path.basename(fp)}:")
                for rule, msg in errs:
                    click.echo(f"    [{rule}] {msg}")
            sys.exit(1)
        else:
            click.echo(f"Validated {total_files} files: all valid.")
