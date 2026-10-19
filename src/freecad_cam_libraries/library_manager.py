"""Library naming and deterministic numbering without FreeCAD imports."""
import uuid

NAMESPACE = uuid.UUID("641b3abb-22d7-4943-b346-163391106933")


def library_id(collection_id):
    return str(uuid.uuid5(NAMESPACE, collection_id))


def next_number(numbers):
    """Append after the highest existing number; preserve gaps and user choices."""
    if any(type(n) is not int or n <= 0 for n in numbers):
        raise ValueError("Existing tool numbers must be positive integers")
    return max(numbers, default=0) + 1


def find_library(collection, libraries):
    ident = library_id(collection.id)
    by_id = [lib for lib in libraries if lib["id"] == ident]
    accepted_names = (collection.name,) + collection.legacy_names
    by_name = [lib for lib in libraries if lib["label"] in accepted_names]
    if by_id and by_id[0]["label"] not in accepted_names:
        raise ValueError(f"Managed library {ident} was renamed; preserving it without changes")
    if len(by_name) > 1 or (by_id and by_name and by_id[0] is not by_name[0]):
        raise ValueError(f"Ambiguous destination library: {collection.name}")
    return (by_id or by_name or [None])[0]
