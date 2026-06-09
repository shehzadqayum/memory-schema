"""Tests for discovery module — frontmatter parsing, link extraction, file discovery."""

import os

import pytest

from memoryschema.discovery import parse_frontmatter, extract_related, discover_memory_files


class TestParseFrontmatter:
    def test_with_frontmatter(self):
        text = "---\nname: test\ntype: semantic\n---\nBody text."
        meta, body = parse_frontmatter(text)
        assert meta == {"name": "test", "type": "semantic"}
        assert body == "Body text."

    def test_without_frontmatter(self):
        text = "Just plain text."
        meta, body = parse_frontmatter(text)
        assert meta == {}
        assert body == "Just plain text."

    def test_quoted_values(self):
        text = '---\nname: "quoted value"\ndesc: \'single\'\n---\nBody.'
        meta, body = parse_frontmatter(text)
        assert meta["name"] == "quoted value"
        assert meta["desc"] == "single"

    def test_empty_frontmatter(self):
        text = "---\n---\nBody only."
        meta, body = parse_frontmatter(text)
        assert meta == {}
        assert body == "Body only."

    def test_no_closing_delimiter(self):
        text = "---\nname: broken\nNo closing."
        meta, body = parse_frontmatter(text)
        assert meta == {}
        assert body == text

    def test_empty_lines_in_frontmatter(self):
        text = "---\nname: test\n\ntype: semantic\n---\nBody."
        meta, body = parse_frontmatter(text)
        assert meta["name"] == "test"
        assert meta["type"] == "semantic"

    def test_colon_in_value(self):
        text = "---\nurl: http://example.com\n---\nBody."
        meta, body = parse_frontmatter(text)
        assert meta["url"] == "http://example.com"


class TestExtractRelated:
    def test_md_links(self):
        body = "See [other](other.md) and [more](more.md)."
        result = extract_related(body)
        assert result == ["other.md", "more.md"]

    def test_url_links_filtered(self):
        body = "See [docs](https://example.com/page.md) and [local](local.md)."
        result = extract_related(body)
        assert result == ["local.md"]

    def test_absolute_path_filtered(self):
        body = "See [root](/absolute/path.md)."
        result = extract_related(body)
        assert result == []

    def test_no_links(self):
        result = extract_related("No links here.")
        assert result == []

    def test_empty_body(self):
        result = extract_related("")
        assert result == []

    def test_non_md_links_ignored(self):
        body = "See [image](photo.png) and [doc](doc.md)."
        result = extract_related(body)
        assert result == ["doc.md"]


class TestDiscoverMemoryFiles:
    def test_finds_md_files(self, tmp_path):
        (tmp_path / "alpha.md").write_text("test")
        (tmp_path / "beta.md").write_text("test")
        (tmp_path / "gamma.txt").write_text("not md")
        result = discover_memory_files(str(tmp_path))
        assert len(result) == 2
        assert all(f.endswith(".md") for f in result)

    def test_excludes_memory_md(self, tmp_path):
        (tmp_path / "MEMORY.md").write_text("index")
        (tmp_path / "real.md").write_text("entity")
        result = discover_memory_files(str(tmp_path))
        assert len(result) == 1
        assert "real.md" in result[0]

    def test_nested_dirs(self, tmp_path):
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (tmp_path / "top.md").write_text("top")
        (subdir / "nested.md").write_text("nested")
        result = discover_memory_files(str(tmp_path))
        assert len(result) == 2

    def test_empty_dir(self, tmp_path):
        result = discover_memory_files(str(tmp_path))
        assert result == []

    def test_nonexistent_dir(self):
        result = discover_memory_files("/nonexistent/path")
        assert result == []

    def test_sorted_output(self, tmp_path):
        (tmp_path / "zebra.md").write_text("z")
        (tmp_path / "alpha.md").write_text("a")
        result = discover_memory_files(str(tmp_path))
        assert "alpha.md" in result[0]
        assert "zebra.md" in result[1]
