from typing import List, Dict, Tuple
from comparator import Difference

# Weights per difference type (0.0–1.0): how "severe" each kind of diff is.
# The score formula is:  100 × (1 − Σ weights / estimated_total_nodes)
WEIGHTS: Dict[str, Dict[str, float]] = {
    "strict": {
        "TAG_MISMATCH":        1.0,
        "STRUCTURE_MISMATCH":  0.8,
        "MISSING_TAG":         0.7,
        "UNEXPECTED_TAG":      0.7,
        "ORDER_MISMATCH":      0.5,
        "CARDINALITY_MISMATCH": 0.4,
        "ATTR_MISMATCH":       0.4,
    },
    "balanced": {
        "TAG_MISMATCH":        1.0,
        "STRUCTURE_MISMATCH":  0.6,
        "MISSING_TAG":         0.5,
        "UNEXPECTED_TAG":      0.4,
        "ORDER_MISMATCH":      0.2,
        "CARDINALITY_MISMATCH": 0.15,
        "ATTR_MISMATCH":       0.15,
    },
    "relaxed": {
        "TAG_MISMATCH":        1.0,
        "STRUCTURE_MISMATCH":  0.4,
        "MISSING_TAG":         0.3,
        "UNEXPECTED_TAG":      0.2,
        "ORDER_MISMATCH":      0.1,
        "CARDINALITY_MISMATCH": 0.05,
        "ATTR_MISMATCH":       0.05,
    },
}


def _estimate_total_nodes(differences: List[Difference]) -> int:
    """
    Estimate how many nodes were involved in the comparison.

    Every difference implies at least one node was examined; matched nodes
    that produced no diff are invisible here, so we use a baseline that
    grows with the number of diffs to keep scores proportional.
    The minimum (20) represents a minimal JATS article skeleton.
    """
    # Count unique paths mentioned in differences as a proxy for tree size
    unique_paths = {d.path for d in differences}
    return max(len(unique_paths) + len(differences), 20)


def calculate_score(
    differences: List[Difference], mode: str = "balanced"
) -> Tuple[float, str, bool]:
    """
    Calculates the similarity score (0.0 to 100.0) based on differences and mode.

    The score is proportional: many small diffs in a large tree still yield
    a meaningful (non-zero) score.

    Returns:
        tuple: (similarity_score, status, compatible_structure)
    """
    mode = mode.lower()
    if mode not in WEIGHTS:
        mode = "balanced"

    mode_weights = WEIGHTS[mode]

    if not differences:
        return 100.0, "EXACT_MATCH", True

    total_weight = sum(
        mode_weights.get(d.type, 0.3) for d in differences
    )
    total_nodes = _estimate_total_nodes(differences)

    # Ratio of "bad weight" to total nodes, capped at 1.0
    penalty_ratio = min(total_weight / total_nodes, 1.0)
    similarity = max(0.0, round((1.0 - penalty_ratio) * 100, 1))

    # Classification
    if similarity >= 80.0:
        status = "STRUCTURE_COMPATIBLE"
    elif similarity >= 50.0:
        status = "PARTIAL_MATCH"
    elif similarity >= 20.0:
        status = "LOW_MATCH"
    else:
        status = "INCOMPATIBLE"

    compatible_structure = status in ("EXACT_MATCH", "STRUCTURE_COMPATIBLE")

    return similarity, status, compatible_structure
