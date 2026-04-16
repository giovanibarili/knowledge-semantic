"""
frontmatter.py — Parse YAML frontmatter from markdown files.

Extracts metadata (description, category, glossary_terms, project) from
the YAML block between --- delimiters at the start of a markdown file.
No external YAML dependency — uses a simple line-based parser for the
flat structure used in knowledge files.
"""

import re

# Matches a YAML frontmatter block: starts with ---, ends with ---
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def parse_frontmatter(content):
    """Extract frontmatter metadata from markdown content.

    Returns (metadata_dict, body) where metadata_dict contains any recognized
    fields (description, category, glossary_terms, project) and body is the
    content after the frontmatter block.

    If no frontmatter is found, returns (None, content).
    """
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return None, content

    raw_block = match.group(1)
    body = content[match.end():]
    metadata = _parse_yaml_block(raw_block)

    return metadata, body


def _parse_yaml_block(block):
    """Parse a simple YAML block into a dict.

    Handles:
    - Simple key: value pairs
    - Multi-line strings with > continuation
    - Lists with - item syntax
    - Nested list-of-dicts for glossary_terms
    """
    result = {}
    lines = block.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # Skip blank lines and comments
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue

        # Match key: value
        kv_match = re.match(r"^(\w[\w_-]*)\s*:\s*(.*)", line)
        if not kv_match:
            i += 1
            continue

        key = kv_match.group(1).strip()
        value = kv_match.group(2).strip()

        if value == ">" or value == "|":
            # Multi-line scalar — collect indented continuation lines
            parts = []
            i += 1
            while i < len(lines) and (lines[i].startswith("  ") or not lines[i].strip()):
                if lines[i].strip():
                    parts.append(lines[i].strip())
                i += 1
            result[key] = " ".join(parts)
            continue

        if not value:
            # Could be a list or nested structure
            items = []
            i += 1
            while i < len(lines) and lines[i].startswith("  "):
                item_line = lines[i].strip()
                if item_line.startswith("- "):
                    item_val = item_line[2:].strip()
                    # Check if this is a dict item (has nested keys)
                    if i + 1 < len(lines) and re.match(r"^\s{4,}\w", lines[i + 1]):
                        # Nested dict under list item
                        item_dict = {}
                        if ":" in item_val:
                            k, v = item_val.split(":", 1)
                            item_dict[k.strip()] = v.strip().strip('"').strip("'")
                        i += 1
                        while i < len(lines) and re.match(r"^\s{4,}", lines[i]):
                            nested_line = lines[i].strip()
                            if ":" in nested_line:
                                k, v = nested_line.split(":", 1)
                                v = v.strip().strip('"').strip("'")
                                # Handle inline list [a, b, c]
                                if v.startswith("[") and v.endswith("]"):
                                    v = [x.strip().strip('"').strip("'")
                                         for x in v[1:-1].split(",") if x.strip()]
                                item_dict[k.strip()] = v
                            i += 1
                        items.append(item_dict)
                        continue
                    else:
                        items.append(item_val.strip('"').strip("'"))
                i += 1
            result[key] = items
            continue

        # Strip quotes from simple values
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]

        # Handle inline list [a, b, c]
        if value.startswith("[") and value.endswith("]"):
            value = [x.strip().strip('"').strip("'")
                     for x in value[1:-1].split(",") if x.strip()]

        # Handle null/none
        if value in ("null", "~", ""):
            value = None

        result[key] = value
        i += 1

    return result


def extract_index_metadata(content):
    """Extract indexing metadata from file content with frontmatter.

    Returns a dict with keys: description, category, glossary_terms, project.
    Only includes keys that were found in the frontmatter.
    Returns None if no frontmatter is present.
    """
    metadata, _body = parse_frontmatter(content)
    if metadata is None:
        return None

    result = {}

    if "description" in metadata and metadata["description"]:
        result["description"] = metadata["description"]

    if "category" in metadata and metadata["category"]:
        result["category"] = metadata["category"]

    if "project" in metadata and metadata["project"]:
        result["project"] = metadata["project"]

    if "glossary_terms" in metadata:
        terms = metadata["glossary_terms"]
        if isinstance(terms, list):
            # Could be list of strings (simple terms) or list of dicts
            normalized = []
            for t in terms:
                if isinstance(t, str):
                    normalized.append({"term": t})
                elif isinstance(t, dict) and "term" in t:
                    normalized.append(t)
            if normalized:
                result["glossary_terms"] = normalized

    return result if result else None
