def validate_modules(module_ids: list[str], catalog: list[dict]) -> tuple[list[str], list[str]]:
    """
    Split module IDs into valid (in catalog) and invalid (hallucinated).
    Returns (valid_ids, rejected_ids).
    """
    catalog_ids = {m["id"] for m in catalog}
    valid = [mid for mid in module_ids if mid in catalog_ids]
    rejected = [mid for mid in module_ids if mid not in catalog_ids]
    if rejected:
        print(f"[HallucinationGuard] BLOCKED {len(rejected)} unknown module IDs: {rejected}")
    return valid, rejected

def filter_traces(traces: list[dict], catalog: list[dict]) -> list[dict]:
    """Remove any reasoning trace whose module_id isn't in catalog."""
    catalog_ids = {m["id"] for m in catalog}
    return [t for t in traces if t.get("module_id") in catalog_ids]