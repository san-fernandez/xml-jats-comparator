#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

from parser import parse_xml
from normalizer import normalize_element
from comparator import compare_nodes
from scorer import calculate_score
from reporter import format_text, format_json

def main():
    parser = argparse.ArgumentParser(
        description="XML Structural Comparison Engine with Similarity Scoring."
    )
    parser.add_argument("expected", help="Path to the expected (reference) XML file.")
    parser.add_argument("candidate", help="Path to the candidate XML file to compare.")
    parser.add_argument(
        "--mode", 
        choices=["strict", "balanced", "relaxed"], 
        default="balanced",
        help="Comparison mode (default: balanced). Strict penalizes order and cardinality heavily. Relaxed is tolerant."
    )
    parser.add_argument(
        "--json", 
        action="store_true", 
        help="Output the result in JSON format instead of human-readable text."
    )
    parser.add_argument(
        "--compare-attrs", 
        action="store_true", 
        help="Enable attribute existence and value comparison."
    )

    args = parser.parse_args()

    try:
        # 1. Parse XML files
        xml_expected = parse_xml(Path(args.expected))
        xml_candidate = parse_xml(Path(args.candidate))
        
        # 2. Normalize trees to StructNode
        struct_expected = normalize_element(xml_expected, compare_attrs=args.compare_attrs)
        struct_candidate = normalize_element(xml_candidate, compare_attrs=args.compare_attrs)
        
        # 3. Compare structures
        differences = compare_nodes(struct_expected, struct_candidate, compare_attrs=args.compare_attrs)
        
        # 4. Score comparison
        similarity, status, compatible_structure = calculate_score(differences, mode=args.mode)
        
        # 5. Report results
        if args.json:
            output = format_json(similarity, status, compatible_structure, differences)
        else:
            output = format_text(similarity, status, differences)
            
        print(output)
        sys.exit(0)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
