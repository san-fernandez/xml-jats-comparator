from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from normalizer import StructNode

@dataclass
class Difference:
    type: str  # TAG_MISMATCH, MISSING_TAG, UNEXPECTED_TAG, ORDER_MISMATCH, CARDINALITY_MISMATCH, STRUCTURE_MISMATCH, ATTR_MISMATCH
    path: str
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    details: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert Difference to a clean dictionary suitable for JSON serialization."""
        d = {
            "type": self.type,
            "path": self.path,
        }
        if self.expected is not None:
            d["expected"] = self.expected
        if self.actual is not None:
            d["actual"] = self.actual
        if self.details is not None:
            d["details"] = self.details
        return d


def compare_nodes(node_a: StructNode, node_b: StructNode, path: str = "", compare_attrs: bool = False) -> List[Difference]:
    """
    Recursively compares two structural XML representations.
    
    If path is empty, it will be initialized to /<tag_name>.
    """
    if not path:
        path = f"/{node_a.tag}"

    diffs: List[Difference] = []

    # 1. Compare root tags
    if node_a.tag != node_b.tag:
        diffs.append(Difference(
            type="TAG_MISMATCH",
            path=path,
            expected=node_a.tag,
            actual=node_b.tag
        ))
        return diffs

    # 2. Compare attributes (if enabled)
    if compare_attrs:
        if node_a.attributes != node_b.attributes:
            diffs.append(Difference(
                type="ATTR_MISMATCH",
                path=path,
                expected=node_a.attributes,
                actual=node_b.attributes,
                details=f"Expected attributes {node_a.attributes}, found {node_b.attributes}"
            ))

    # 3. Compare repetition/cardinality
    if node_a.count != node_b.count:
        diffs.append(Difference(
            type="CARDINALITY_MISMATCH",
            path=path,
            expected=node_a.count,
            actual=node_b.count
        ))

    # 4. Compare children
    children_a = node_a.children
    children_b = node_b.children

    # Group child indices by tag name to pair them stably
    from collections import defaultdict
    indices_a = defaultdict(list)
    for idx, child in enumerate(children_a):
        indices_a[child.tag].append(idx)

    indices_b = defaultdict(list)
    for idx, child in enumerate(children_b):
        indices_b[child.tag].append(idx)

    pairs: List[tuple] = []
    missing_indices: List[int] = []
    unexpected_indices: List[int] = []

    # Keep track of matched B indices
    matched_b_indices = set()

    for idx_a, child_a in enumerate(children_a):
        tag = child_a.tag
        # Find first unmatched child in B with the same tag
        avail_b = [ib for ib in indices_b[tag] if ib not in matched_b_indices]
        if avail_b:
            idx_b = avail_b[0]
            pairs.append((idx_a, idx_b))
            matched_b_indices.add(idx_b)
        else:
            missing_indices.append(idx_a)

    # Any index in B that wasn't matched is unexpected
    for idx_b in range(len(children_b)):
        if idx_b not in matched_b_indices:
            unexpected_indices.append(idx_b)

    # Determine structural mismatches vs missing/unexpected tags
    if missing_indices and unexpected_indices:
        missing_tags = [children_a[idx].tag for idx in missing_indices]
        unexpected_tags = [children_b[idx].tag for idx in unexpected_indices]
        diffs.append(Difference(
            type="STRUCTURE_MISMATCH",
            path=path,
            expected=missing_tags,
            actual=unexpected_tags,
            details=f"Missing tags: {missing_tags}. Unexpected tags: {unexpected_tags}."
        ))
    else:
        # Report individual missing tags
        for idx in missing_indices:
            child = children_a[idx]
            child_path = f"{path}/{child.tag}" if path != "/" else f"/{child.tag}"
            diffs.append(Difference(
                type="MISSING_TAG",
                path=child_path
            ))
        # Report individual unexpected tags
        for idx in unexpected_indices:
            child = children_b[idx]
            child_path = f"{path}/{child.tag}" if path != "/" else f"/{child.tag}"
            diffs.append(Difference(
                type="UNEXPECTED_TAG",
                path=child_path
            ))

    # Check for order mismatches among the paired nodes
    if pairs:
        # Sort pairs based on their original order in A
        pairs_sorted = sorted(pairs, key=lambda x: x[0])
        b_sequence = [p[1] for p in pairs_sorted]
        # Check if the B index sequence is monotonically increasing
        is_order_correct = all(b_sequence[i] < b_sequence[i+1] for i in range(len(b_sequence) - 1))
        if not is_order_correct:
            diffs.append(Difference(
                type="ORDER_MISMATCH",
                path=path,
                details=f"Order mismatch under '{path}'"
            ))

    # Recursively compare matched pairs
    for idx_a, idx_b in pairs:
        child_a = children_a[idx_a]
        child_b = children_b[idx_b]
        child_path = f"{path}/{child_a.tag}" if path != "/" else f"/{child_a.tag}"
        child_diffs = compare_nodes(child_a, child_b, child_path, compare_attrs)
        diffs.extend(child_diffs)

    return diffs
