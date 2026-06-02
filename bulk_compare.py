#!/usr/bin/env python3
"""
Motor de Comparación Estructural XML — Procesamiento Masivo.

Soporta directorios planos, .tar.gz y directorios de .zip.
Con --cross compara todos contra todos (sin requerir nombres iguales).
"""
import os
import sys
import argparse
import csv
import io
import json
import random
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import List, Dict, Any, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed

from parser import parse_xml
from normalizer import normalize_element
from comparator import compare_nodes
from scorer import calculate_score


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------

def compare_pair_worker(args_tuple: Tuple[str, str, str, bool]) -> Dict[str, Any]:
    """Compara un par de XMLs en un proceso separado."""
    expected_path, candidate_path, mode, compare_attrs = args_tuple
    result = {
        "expected_file": Path(expected_path).name,
        "candidate_file": Path(candidate_path).name,
        "similarity": None,
        "status": "ERROR",
        "compatible_structure": False,
        "differences": [],
    }
    try:
        struct_exp = normalize_element(
            parse_xml(Path(expected_path)), compare_attrs=compare_attrs
        )
        struct_cand = normalize_element(
            parse_xml(Path(candidate_path)), compare_attrs=compare_attrs
        )
        diffs = compare_nodes(struct_exp, struct_cand, compare_attrs=compare_attrs)
        similarity, status, compatible = calculate_score(diffs, mode=mode)
        result.update(
            similarity=similarity,
            status=status,
            compatible_structure=compatible,
            differences=[d.to_dict() for d in diffs],
        )
    except Exception as e:
        result["differences"] = [
            {"type": "PROCESSING_ERROR", "path": "", "details": str(e)}
        ]
    return result


# ---------------------------------------------------------------------------
# Extracción de archivos comprimidos
# ---------------------------------------------------------------------------

def resolve_xml_dir(source: Path, label: str) -> Tuple[Path, bool]:
    """
    Dado un path (directorio, .tar.gz, o directorio con .zip),
    devuelve un directorio con XMLs planos.
    Retorna (xml_dir, es_temporal).
    """
    if source.is_dir() and not list(source.glob("*.zip")):
        return source, False

    tmp = Path(tempfile.mkdtemp(prefix=f"xmlcmp_{label}_"))

    if source.is_file() and source.name.endswith(".tar.gz"):
        _extract_tar_gz(source, tmp)
    elif source.is_dir():
        _extract_zip_dir(source, tmp)
    elif source.is_file() and source.name.endswith(".zip"):
        _extract_single_zip(source, tmp)
    else:
        shutil.rmtree(tmp, ignore_errors=True)
        raise ValueError(f"Formato no soportado: {source}")

    return tmp, True


def _extract_tar_gz(tar_path: Path, dest: Path):
    with tarfile.open(tar_path, "r:gz") as tar:
        for member in tar.getmembers():
            if member.name.endswith(".xml"):
                f = tar.extractfile(member)
                if f:
                    (dest / Path(member.name).name).write_bytes(f.read())
            elif member.name.endswith(".zip"):
                f = tar.extractfile(member)
                if f:
                    with zipfile.ZipFile(io.BytesIO(f.read())) as zf:
                        for n in zf.namelist():
                            if n.endswith(".xml"):
                                (dest / n).write_bytes(zf.read(n))


def _extract_zip_dir(zip_dir: Path, dest: Path):
    for zp in sorted(zip_dir.glob("*.zip")):
        with zipfile.ZipFile(zp) as zf:
            for n in zf.namelist():
                if n.endswith(".xml"):
                    (dest / n).write_bytes(zf.read(n))


def _extract_single_zip(zip_path: Path, dest: Path):
    with zipfile.ZipFile(zip_path) as zf:
        for n in zf.namelist():
            if n.endswith(".xml"):
                (dest / n).write_bytes(zf.read(n))


# ---------------------------------------------------------------------------
# Tabla ASCII
# ---------------------------------------------------------------------------

def format_console_table(results: List[Dict[str, Any]]) -> str:
    headers = ["Referencia", "Candidato", "Score", "Status", "Compat.", "Diferencias"]
    col_widths = [20, 20, 6, 22, 7, 40]

    for r in results:
        col_widths[0] = max(col_widths[0], len(r["expected_file"]))
        col_widths[1] = max(col_widths[1], len(r["candidate_file"]))
        diff_types = [d["type"] for d in r["differences"]]
        summary = ", ".join(sorted(set(diff_types))) if diff_types else "—"
        if len(summary) > 50:
            summary = summary[:47] + "..."
        r["_diff_summary"] = summary
        col_widths[5] = max(col_widths[5], min(len(summary), 60))

    row_fmt = " | ".join(f"{{:<{w}}}" for w in col_widths)
    sep = "-+-".join("-" * w for w in col_widths)

    lines = [row_fmt.format(*headers), sep]
    for r in results:
        score = f"{r['similarity']}%" if r["similarity"] is not None else "N/A"
        compat = "Si" if r["compatible_structure"] else "No"
        if r["status"] == "ERROR":
            compat = "Err"
        lines.append(
            row_fmt.format(
                r["expected_file"],
                r["candidate_file"],
                score,
                r["status"],
                compat,
                r["_diff_summary"],
            )
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Comparacion masiva de XMLs JATS. Soporta .tar.gz, .zip y directorios."
    )
    ap.add_argument(
        "--ref", "-r", required=True,
        help="Referencia: directorio de XMLs, .tar.gz, o directorio de .zip.",
    )
    ap.add_argument(
        "--candidate", "-c", required=True,
        help="Candidato: directorio de XMLs, .tar.gz, o directorio de .zip.",
    )
    ap.add_argument(
        "--cross", action="store_true",
        help="Comparacion cruzada (todos vs todos). Sin esto, empareja por nombre.",
    )
    ap.add_argument(
        "--sample", "-s", type=int, default=0,
        help="Tomar N archivos de referencia al azar (0 = todos).",
    )
    ap.add_argument(
        "--mode", choices=["strict", "balanced", "relaxed"], default="balanced",
    )
    ap.add_argument("--compare-attrs", action="store_true")
    ap.add_argument(
        "--format", "-f", choices=["table", "csv", "json"], default="table",
    )
    ap.add_argument("--output", "-o", help="Guardar resultado en archivo.")
    ap.add_argument("--workers", "-w", type=int, default=os.cpu_count())
    args = ap.parse_args()

    tmps: List[Tuple[Path, bool]] = []
    try:
        ref_dir, ref_tmp = resolve_xml_dir(Path(args.ref), "ref")
        tmps.append((ref_dir, ref_tmp))
        cand_dir, cand_tmp = resolve_xml_dir(Path(args.candidate), "cand")
        tmps.append((cand_dir, cand_tmp))

        ref_files = sorted(ref_dir.glob("*.xml"))
        cand_files = sorted(cand_dir.glob("*.xml"))

        if not ref_files:
            sys.exit(f"Error: sin XMLs de referencia en '{args.ref}'.")
        if not cand_files:
            sys.exit(f"Error: sin XMLs candidatos en '{args.candidate}'.")

        if args.sample and args.sample < len(ref_files):
            ref_files = sorted(random.sample(ref_files, args.sample))

        # Armar pares
        if args.cross:
            pairs = [(str(r), str(c)) for c in cand_files for r in ref_files]
        else:
            ref_map = {f.name: f for f in ref_files}
            pairs = []
            for c in cand_files:
                if c.name in ref_map:
                    pairs.append((str(ref_map[c.name]), str(c)))
                else:
                    print(
                        f"Sin referencia para '{c.name}', omitido.",
                        file=sys.stderr,
                    )

        if not pairs:
            sys.exit(
                "Sin pares para comparar. Usa --cross si los nombres no coinciden."
            )

        print(
            f">> {len(pairs)} pares ({len(cand_files)} cand x {len(ref_files)} ref), "
            f"{args.workers} workers\n",
            file=sys.stderr,
        )

        # Ejecutar comparaciones en paralelo
        tasks = [(p[0], p[1], args.mode, args.compare_attrs) for p in pairs]
        results: List[Dict[str, Any]] = []
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futs = {pool.submit(compare_pair_worker, t): t for t in tasks}
            for i, fut in enumerate(as_completed(futs), 1):
                results.append(fut.result())
                if i % 200 == 0:
                    print(f"  {i}/{len(pairs)}...", file=sys.stderr)

        results.sort(key=lambda x: (x["candidate_file"], x["expected_file"]))

        # Formatear salida
        if args.format == "json":
            out = json.dumps(results, indent=2, ensure_ascii=False)
        elif args.format == "csv":
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["ref", "candidate", "similarity", "status", "compatible", "diffs"])
            for r in results:
                dt = ", ".join(sorted(set(d["type"] for d in r["differences"]))) or "None"
                w.writerow([
                    r["expected_file"],
                    r["candidate_file"],
                    r["similarity"] if r["similarity"] is not None else "N/A",
                    r["status"],
                    r["compatible_structure"],
                    dt,
                ])
            out = buf.getvalue()
        else:
            out = format_console_table(results)

        if args.output:
            Path(args.output).write_text(out, encoding="utf-8")
            print(f"\nReporte guardado en '{args.output}'", file=sys.stderr)
        else:
            print(out)

    finally:
        for d, is_tmp in tmps:
            if is_tmp and d.exists():
                shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    main()
