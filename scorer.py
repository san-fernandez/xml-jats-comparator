from typing import List, Dict, Tuple
from comparator import Difference

# Penalties for each comparison mode
PENALTIES: Dict[str, Dict[str, float]] = {
    "strict": {
        "TAG_MISMATCH": 30.0,
        "STRUCTURE_MISMATCH": 25.0,
        "MISSING_TAG": 20.0,
        "UNEXPECTED_TAG": 20.0,
        "ORDER_MISMATCH": 15.0,
        "CARDINALITY_MISMATCH": 10.0,
        "ATTR_MISMATCH": 10.0,
    },
    "balanced": {
        "TAG_MISMATCH": 30.0,
        "STRUCTURE_MISMATCH": 25.0,
        "MISSING_TAG": 20.0,
        "UNEXPECTED_TAG": 20.0,
        "ORDER_MISMATCH": 10.0,
        "CARDINALITY_MISMATCH": 5.0,
        "ATTR_MISMATCH": 5.0,
    },
    "relaxed": {
        "TAG_MISMATCH": 30.0,
        "STRUCTURE_MISMATCH": 20.0,
        "MISSING_TAG": 15.0,
        "UNEXPECTED_TAG": 10.0,
        "ORDER_MISMATCH": 5.0,
        "CARDINALITY_MISMATCH": 2.0,
        "ATTR_MISMATCH": 2.0,
    }
}

def calculate_score(differences: List[Difference], mode: str = "balanced") -> Tuple[float, str, bool]:
    """
    Calculates the similarity score (0.0 to 100.0) based on differences and mode.
    
    Returns:
        tuple: (similarity_score, status, compatible_structure)
    """
    mode = mode.lower()
    if mode not in PENALTIES:
        mode = "balanced"
        
    mode_penalties = PENALTIES[mode]
    
    total_penalty = 0.0
    for diff in differences:
        penalty = mode_penalties.get(diff.type, 10.0)  # Default penalty to 10 if unknown type
        total_penalty += penalty
        
    similarity = max(0.0, 100.0 - total_penalty)
    
    # Classification logic
    if not differences and similarity >= 100.0:
        status = "EXACT_MATCH"
    elif similarity >= 80.0:
        status = "STRUCTURE_COMPATIBLE"
    elif similarity >= 50.0:
        status = "PARTIAL_MATCH"
    else:
        status = "INCOMPATIBLE"
        
    compatible_structure = status in ("EXACT_MATCH", "STRUCTURE_COMPATIBLE")
    
    return round(similarity, 1), status, compatible_structure
