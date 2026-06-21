def serialize_feedback(feedback: list) -> list:
    """
    Normalizes feedback structure for storage.
    """
    normalized = []
    for f in feedback:
        normalized.append({
            "rule_id": f.get("rule_id"),
            "cde": f.get("cde"),
            "old": f.get("old"),
            "new": f.get("new"),
            "decision": f.get("decision"),
        })
    return normalized
