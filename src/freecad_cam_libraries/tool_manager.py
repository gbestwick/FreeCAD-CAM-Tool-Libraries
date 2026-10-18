"""Duplicate policy shared by preview and installation."""
from .validation import fingerprint


def classify(tool, existing):
    """Return new, reuse, conflict, or equivalent; never merge different IDs."""
    if tool.id in existing:
        current = existing[tool.id]
        if fingerprint(current, include_name=True) == fingerprint(tool.data, include_name=True):
            return "reuse", tool.id
        return "conflict", tool.id
    signature = fingerprint(tool.data)
    for ident, data in existing.items():
        try:
            if fingerprint(data) == signature:
                return "equivalent", ident
        except (ValueError, TypeError):
            # Unknown/custom existing definitions cannot be proven equivalent.
            continue
    return "new", tool.id
