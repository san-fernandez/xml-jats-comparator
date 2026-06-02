# Motor de Comparación Estructural de XML JATS

Sistema para comparar la estructura de documentos XML JATS sin considerar contenido textual. Permite tanto la comparación individual entre dos archivos como la **comparación masiva cruzada** entre corpus completos desde archivos comprimidos (.tar.gz, .zip).

## 🛠️ Arquitectura

| Módulo | Responsabilidad |
|--------|----------------|
| `parser.py` | Parsea XML desde archivos o strings usando `xml.etree.ElementTree` |
| `normalizer.py` | Transforma el XML en `StructNode`, agrupando nodos repetidos consecutivos |
| `comparator.py` | Comparación recursiva de dos árboles estructurales con detección de diferencias |
| `scorer.py` | Scoring proporcional al tamaño del árbol, con pesos por tipo de diferencia |
| `reporter.py` | Formateo de resultados en texto o JSON |
| `compare_xml.py` | CLI para comparación individual (2 archivos) |
| `bulk_compare.py` | CLI para comparación masiva con soporte de archivos comprimidos |

---

## 🚀 Comparación Individual

```bash
python compare_xml.py expected.xml candidate.xml
```

### Opciones:

| Flag | Descripción |
|------|-------------|
| `--mode {strict,balanced,relaxed}` | Nivel de tolerancia (default: `balanced`) |
| `--json` | Salida en JSON |
| `--compare-attrs` | Comparar atributos XML |

### Ejemplo:

```text
Similarity: 75.0%

Status:
PARTIAL_MATCH

Differences:
- MISSING_TAG /libro/editorial

- CARDINALITY_MISMATCH /libro/autor
  expected=4 actual=1
```

---

## 📂 Comparación Masiva

`bulk_compare.py` permite comparar corpus completos de XMLs, leyendo directamente desde archivos comprimidos y ejecutando las comparaciones en paralelo.

### Fuentes soportadas:

- Directorio con archivos `.xml` sueltos
- Archivo `.tar.gz` (incluyendo `.zip` internos con XMLs)
- Directorio con archivos `.zip` (extrae todos los XMLs)

### Modos de emparejamiento:

| Modo | Descripción |
|------|-------------|
| Por nombre (default) | Empareja archivos de referencia y candidato que tengan el mismo nombre |
| `--cross` | Comparación cruzada: cada candidato contra cada referencia (todos vs todos) |

### Ejemplos:

**Comparación cruzada SUMARC vs Redalyc (todos los archivos):**

```bash
python bulk_compare.py \
  -r redalyc-xml/ \
  -c sumarc-xml/XMLEnriquecidos.tar.gz \
  --cross \
  --mode relaxed \
  -f csv \
  -o resultado_completo.csv
```

**Con muestra aleatoria de referencia (más rápido):**

```bash
python bulk_compare.py \
  -r redalyc-xml/ \
  -c sumarc-xml/XMLEnriquecidos.tar.gz \
  --cross \
  --sample 10 \
  --mode relaxed
```

**Emparejamiento por nombre entre dos directorios:**

```bash
python bulk_compare.py -r /ruta/a/referencias -c /ruta/a/candidatos
```

### Opciones completas:

| Flag | Descripción |
|------|-------------|
| `--ref, -r` | Referencia: directorio, `.tar.gz`, o directorio de `.zip` |
| `--candidate, -c` | Candidato: directorio, `.tar.gz`, o directorio de `.zip` |
| `--cross` | Comparación cruzada todos vs todos |
| `--sample, -s N` | Tomar N archivos de referencia al azar (0 = todos) |
| `--mode {strict,balanced,relaxed}` | Modo de comparación (default: `balanced`) |
| `--compare-attrs` | Comparar atributos |
| `--format, -f {table,csv,json}` | Formato de salida (default: `table`) |
| `--output, -o` | Guardar resultado en archivo |
| `--workers, -w N` | Procesos paralelos (default: todos los CPUs) |

### Ejemplo de salida (tabla):

```text
Referencia           | Candidato                    | Score  | Status               | Compat. | Diferencias
---------------------+------------------------------+--------+----------------------+---------+---------------------------
10745321006.xml      | Artículo_PEZZANO-enriched.xml | 91.3%  | STRUCTURE_COMPATIBLE | Si      | CARDINALITY_MISMATCH, ...
10745321013.xml      | Rossi-enriched.xml            | 91.2%  | STRUCTURE_COMPATIBLE | Si      | MISSING_TAG, ...
```

---

## 📈 Sistema de Scoring

El score es **proporcional al tamaño del árbol comparado**:

```
score = 100 × (1 − Σ pesos / nodos_totales_estimados)
```

Cada tipo de diferencia tiene un peso de 0.0 a 1.0 según el modo:

| Tipo de Diferencia | STRICT | BALANCED | RELAXED |
|:---|:---:|:---:|:---:|
| `TAG_MISMATCH` | 1.0 | 1.0 | 1.0 |
| `STRUCTURE_MISMATCH` | 0.8 | 0.6 | 0.4 |
| `MISSING_TAG` | 0.7 | 0.5 | 0.3 |
| `UNEXPECTED_TAG` | 0.7 | 0.4 | 0.2 |
| `ORDER_MISMATCH` | 0.5 | 0.2 | 0.1 |
| `CARDINALITY_MISMATCH` | 0.4 | 0.15 | 0.05 |
| `ATTR_MISMATCH` | 0.4 | 0.15 | 0.05 |

### Clasificación:

| Score | Status |
|-------|--------|
| 100% | `EXACT_MATCH` |
| ≥ 80% | `STRUCTURE_COMPATIBLE` |
| ≥ 50% | `PARTIAL_MATCH` |
| ≥ 20% | `LOW_MATCH` |
| < 20% | `INCOMPATIBLE` |

---

## 🧪 Tests

```bash
python test_compare_xml.py
```
