import json
from typing import List, Dict, Any
from comparator import Difference

def format_json(similarity: float, status: str, compatible_structure: bool, differences: List[Difference]) -> str:
    """Formats the results as a JSON string."""
    result = {
        "similarity": similarity,
        "status": status,
        "compatible_structure": compatible_structure,
        "differences": [diff.to_dict() for diff in differences]
    }
    return json.dumps(result, indent=2, ensure_ascii=False)

def format_text(similarity: float, status: str, differences: List[Difference]) -> str:
    """Formats the results as a human-readable text block."""
    lines = []
    lines.append(f"Similarity: {similarity}%")
    lines.append("")
    lines.append("Status:")
    lines.append(status)
    lines.append("")
    
    if not differences:
        lines.append("Differences: None")
    else:
        lines.append("Differences:")
        for diff in differences:
            lines.append(f"- {diff.type} {diff.path}")
            
            # Formatting details per difference type
            details_list = []
            if diff.type == "CARDINALITY_MISMATCH":
                details_list.append(f"expected={diff.expected} actual={diff.actual}")
            elif diff.type == "TAG_MISMATCH":
                details_list.append(f"expected={diff.expected} actual={diff.actual}")
            elif diff.type == "STRUCTURE_MISMATCH":
                # Clean lists of tags to a comma-separated format
                missing_str = ",".join(diff.expected) if isinstance(diff.expected, list) else str(diff.expected)
                unexpected_str = ",".join(diff.actual) if isinstance(diff.actual, list) else str(diff.actual)
                details_list.append(f"missing={missing_str} unexpected={unexpected_str}")
            elif diff.type == "ATTR_MISMATCH":
                details_list.append(f"expected={diff.expected} actual={diff.actual}")
                
            if diff.details and diff.type not in ("STRUCTURE_MISMATCH", "ATTR_MISMATCH"):
                details_list.append(f"details={diff.details}")
                
            if details_list:
                lines.append(f"  {' '.join(details_list)}")
                
            lines.append("")  # Empty line between differences
            
    # Clean up trailing empty lines
    while lines and lines[-1] == "":
        lines.pop()
        
    return "\n".join(lines)
