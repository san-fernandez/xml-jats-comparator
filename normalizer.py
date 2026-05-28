from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET

@dataclass
class StructNode:
    tag: str
    count: int = 1
    children: List['StructNode'] = field(default_factory=list)
    attributes: Dict[str, str] = field(default_factory=dict)

    def to_dict(self, include_attrs: bool = False) -> Dict[str, Any]:
        """
        Serializes the StructNode to a dictionary.
        Leaves have children list empty. We match the structure of the spec.
        """
        d: Dict[str, Any] = {
            "tag": self.tag,
            "count": self.count,
        }
        if include_attrs and self.attributes:
            d["attributes"] = self.attributes
        
        # Consistent with Section 6, children is always a list.
        # But we could omit it if we want, but keeping children = [] is cleaner.
        d["children"] = [child.to_dict(include_attrs) for child in self.children]
        return d


def _strip_namespace(tag: str) -> str:
    """Helper to remove URI namespace from a tag if present."""
    if tag.startswith("{") and "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def normalize_element(element: ET.Element, compare_attrs: bool = False) -> StructNode:
    """
    Recursively converts an xml.etree.ElementTree.Element to a StructNode.
    It groups consecutive elements of the same tag.
    """
    cleaned_tag = _strip_namespace(element.tag)
    
    attributes = {}
    if compare_attrs:
        for k, v in element.attrib.items():
            cleaned_attr_name = _strip_namespace(k)
            attributes[cleaned_attr_name] = v

    normalized_children: List[StructNode] = []
    raw_children = list(element)
    
    i = 0
    while i < len(raw_children):
        child = raw_children[i]
        child_tag = _strip_namespace(child.tag)
        
        # Count consecutive identical tags
        count = 1
        j = i + 1
        while j < len(raw_children):
            next_child_tag = _strip_namespace(raw_children[j].tag)
            if next_child_tag == child_tag:
                count += 1
                j += 1
            else:
                break
        
        # Recursively normalize the first element as the representative
        rep_node = normalize_element(child, compare_attrs)
        rep_node.count = count
        normalized_children.append(rep_node)
        
        # Skip the grouped siblings
        i = j
        
    return StructNode(
        tag=cleaned_tag,
        count=1,  # Root element defaults to count 1
        children=normalized_children,
        attributes=attributes
    )
