#!/usr/bin/env python3
import os
import sys
import argparse
import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed

from parser import parse_xml
from normalizer import normalize_element
from comparator import compare_nodes
from scorer import calculate_score

def compare_pair_worker(args_tuple: Tuple[str, str, str, bool]) -> Dict[str, Any]:
    """
    Worker function to compare a single pair of expected and candidate XML files.
    Runs in a separate process.
    """
    expected_path, candidate_path, mode, compare_attrs = args_tuple
    result = {
        "expected_file": Path(expected_path).name,
        "candidate_file": Path(candidate_path).name,
        "similarity": None,
        "status": "ERROR",
        "compatible_structure": False,
        "differences": []
    }
    
    try:
        xml_expected = parse_xml(Path(expected_path))
        xml_candidate = parse_xml(Path(candidate_path))
        
        struct_expected = normalize_element(xml_expected, compare_attrs=compare_attrs)
        struct_candidate = normalize_element(xml_candidate, compare_attrs=compare_attrs)
        
        differences = compare_nodes(struct_expected, struct_candidate, compare_attrs=compare_attrs)
        
        similarity, status, compatible = calculate_score(differences, mode=mode)
        
        result["similarity"] = similarity
        result["status"] = status
        result["compatible_structure"] = compatible
        result["differences"] = [d.to_dict() for d in differences]
        
    except Exception as e:
        result["differences"] = [{"type": "PROCESSING_ERROR", "path": "", "details": str(e)}]
        
    return result

def format_console_table(results: List[Dict[str, Any]]) -> str:
    """Formats the results as an ASCII table."""
    headers = ["Expected File", "Candidate File", "Score", "Status", "Compatible", "Diff Summary"]
    col_widths = [15, 15, 6, 22, 10, 30]
    
    # Calculate dynamic column widths if needed, using minimum values
    for r in results:
        col_widths[0] = max(col_widths[0], len(r["expected_file"]))
        col_widths[1] = max(col_widths[1], len(r["candidate_file"]))
        col_widths[3] = max(col_widths[3], len(r["status"]))
        
        # Build a short diff summary
        diff_types = [d["type"] for d in r["differences"]]
        summary = ", ".join(set(diff_types)) if diff_types else "None"
        if len(summary) > 40:
            summary = summary[:37] + "..."
        r["_diff_summary"] = summary
        col_widths[5] = max(col_widths[5], len(summary))

    # Format helpers
    row_fmt = " | ".join(f"{{:<{w}}}" for w in col_widths)
    separator = "-+-".join("-" * w for w in col_widths)
    
    lines = []
    lines.append(row_fmt.format(*headers))
    lines.append(separator)
    
    for r in results:
        comp_str = "Yes" if r["compatible_structure"] else "No"
        if r["status"] == "ERROR":
            comp_str = "Error"
        score_str = f"{r['similarity']}%" if r["similarity"] is not None else "N/A"
        lines.append(row_fmt.format(
            r["expected_file"],
            r["candidate_file"],
            score_str,
            r["status"],
            comp_str,
            r["_diff_summary"]
        ))
        
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(
        description="Motor de Comparación Estructural XML - Procesamiento Masivo"
    )
    
    # Matching inputs
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--ref", "-r",
        help="Archivo XML de referencia único contra el cual comparar todos los candidatos."
    )
    group.add_argument(
        "--ref-dir",
        help="Directorio de XMLs de referencia. Se compararán archivos con el mismo nombre."
    )
    
    parser.add_argument(
        "--candidate-dir", "-d",
        required=True,
        help="Directorio que contiene los archivos XML candidatos a comparar."
    )
    parser.add_argument(
        "--mode",
        choices=["strict", "balanced", "relaxed"],
        default="balanced",
        help="Modo de comparación (por defecto: balanced)."
    )
    parser.add_argument(
        "--compare-attrs",
        action="store_true",
        help="Habilitar comparación de atributos."
    )
    parser.add_argument(
        "--format", "-f",
        choices=["table", "csv", "json"],
        default="table",
        help="Formato de la salida (por defecto: table)."
    )
    parser.add_argument(
        "--output", "-o",
        help="Ruta de archivo para guardar el reporte (CSV o JSON)."
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=os.cpu_count(),
        help="Número de procesos trabajadores concurrentes (por defecto: número de CPUs)."
    )

    args = parser.parse_args()

    cand_dir = Path(args.candidate_dir)
    if not cand_dir.is_dir():
        print(f"Error: El directorio de candidatos '{args.candidate_dir}' no existe o no es un directorio.", file=sys.stderr)
        sys.exit(1)

    # Find XML files in candidate directory
    candidate_files = sorted(list(cand_dir.glob("*.xml")))
    if not candidate_files:
        print(f"No se encontraron archivos XML en '{args.candidate_dir}'.", file=sys.stderr)
        sys.exit(0)

    # Build pairs of (expected_file_path, candidate_file_path)
    pairs: List[Tuple[str, str]] = []
    
    if args.ref:
        ref_path = Path(args.ref)
        if not ref_path.is_file():
            print(f"Error: El archivo de referencia '{args.ref}' no existe.", file=sys.stderr)
            sys.exit(1)
        for cand in candidate_files:
            pairs.append((str(ref_path), str(cand)))
    else:
        ref_dir = Path(args.ref_dir)
        if not ref_dir.is_dir():
            print(f"Error: El directorio de referencia '{args.ref_dir}' no existe.", file=sys.stderr)
            sys.exit(1)
            
        for cand in candidate_files:
            matching_ref = ref_dir / cand.name
            if matching_ref.is_file():
                pairs.append((str(matching_ref), str(cand)))
            else:
                print(f"Advertencia: No se encontró referencia correspondiente para '{cand.name}' en '{args.ref_dir}'. Se omitirá.", file=sys.stderr)

    if not pairs:
        print("No hay archivos emparejados para comparar.", file=sys.stderr)
        sys.exit(0)

    print(f"Iniciando comparación masiva de {len(pairs)} pares usando {args.workers} trabajadores concurrentes...\n", file=sys.stderr)

    # Run comparisons in parallel using ProcessPoolExecutor
    worker_tasks = [(p[0], p[1], args.mode, args.compare_attrs) for p in pairs]
    results = []
    
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(compare_pair_worker, task): task for task in worker_tasks}
        
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            
    # Sort results by candidate file name for stability
    results.sort(key=lambda x: x["candidate_file"])

    # Output formatting
    if args.format == "json":
        output_data = json.dumps(results, indent=2, ensure_ascii=False)
    elif args.format == "csv":
        import io
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["expected_file", "candidate_file", "similarity", "status", "compatible_structure", "diff_summary"])
        for r in results:
            diff_types = [d["type"] for d in r["differences"]]
            diff_summary = ", ".join(set(diff_types)) if diff_types else "None"
            writer.writerow([
                r["expected_file"],
                r["candidate_file"],
                r["similarity"] if r["similarity"] is not None else "N/A",
                r["status"],
                r["compatible_structure"],
                diff_summary
            ])
        output_data = csv_buffer.getvalue()
    else:
        output_data = format_console_table(results)

    # Write output or print to stdout
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_data)
            print(f"Reporte guardado exitosamente en '{args.output}'", file=sys.stderr)
        except Exception as e:
            print(f"Error escribiendo el reporte en '{args.output}': {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output_data)

if __name__ == "__main__":
    main()
