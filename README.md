# Motor de Comparación Estructural de XML con Score de Similitud

Este motor permite determinar el grado de similitud estructural entre dos documentos XML sin considerar su contenido textual o valores internos. Valida si siguen una estructura equivalente o compatible, manejando diferencias de cardinalidad (repeticiones consecutivas), ausencia de etiquetas, variaciones en la jerarquía y alteración del orden de etiquetas.

## 🛠️ Arquitectura

El sistema está diseñado en capas completamente desacopladas de acuerdo con la especificación:

1. **`parser.py`**: Parsea archivos XML usando la API segura de `xml.etree.ElementTree`.
2. **`normalizer.py`**: Transforma el XML en una representación intermedia estructurada, agrupando nodos repetidos consecutivos y eliminando contenido de texto.
3. **`comparator.py`**: Algoritmo recursivo que compara nodos, realiza alineación posicional de los hijos, detecta orden y diferencias estructurales internas.
4. **`scorer.py`**: Aplica penalizaciones según el modo de tolerancia y clasifica la compatibilidad.
5. **`reporter.py`**: Formatea las diferencias detectadas en formato amigable de consola o JSON.
6. **`compare_xml.py`**: Interfaz de línea de comandos (CLI) que orquesta las capas anteriores.
7. **`bulk_compare.py`**: Script de procesamiento masivo paralelo para comparar múltiples XMLs simultáneamente.

---

## 🚀 Uso del CLI (Individual)

Puedes ejecutar el motor pasando las rutas del XML esperado (referencia) y el candidato:

```bash
python compare_xml.py expected.xml candidate.xml
```

### Opciones de comando:

* `--mode {strict,balanced,relaxed}`: Establece el nivel de tolerancia (por defecto: `balanced`).
* `--json`: Devuelve la salida estructurada en formato JSON válido en lugar de texto amigable.
* `--compare-attrs`: Habilita la comparación de existencia y valores de los atributos.

### Ejemplo de Salida Consola (Balanced)

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

## 📂 Procesamiento Masivo (Carga Masiva)

Para procesar múltiples comparaciones de manera concurrente (aprovechando todos los núcleos de CPU), utiliza `bulk_compare.py`.

### 1. Comparar una carpeta de candidatos contra una ÚNICA referencia:

```bash
python bulk_compare.py -r expected.xml -d /ruta/a/candidatos --format table
```

### 2. Comparar carpetas aparejando por nombre de archivo:
Si tienes una carpeta de referencia y otra de candidatos con nombres de archivo idénticos (ej. `doc1.xml`, `doc2.xml`):

```bash
python bulk_compare.py --ref-dir /ruta/a/referencias -d /ruta/a/candidatos --format table
```

### Opciones del Procesador Masivo:

* `--mode {strict,balanced,relaxed}`: Modo de comparación (por defecto: `balanced`).
* `--format {table,csv,json}`: Formato de reporte de salida (por defecto: `table`).
* `--output -o <path>`: Guarda el reporte generado en el archivo indicado.
* `--workers -w <int>`: Número de procesos paralelos concurrentes (por defecto: número total de CPUs del sistema).
* `--compare-attrs`: Activa comparación de atributos.

### Ejemplo de Reporte en Consola (`table`)

```text
Expected File   | Candidate File  | Score  | Status                 | Compatible | Diff Summary                     
----------------+-----------------+--------+------------------------+------------+----------------------------------
expected.xml    | candidate_1.xml | 75.0%  | PARTIAL_MATCH          | No         | CARDINALITY_MISMATCH, MISSING_TAG
expected.xml    | candidate_2.xml | 100.0% | EXACT_MATCH            | Yes        | None                             
```

---

## 📈 Modos de Comparación y Penalizaciones

| Tipo de Diferencia | STRICT | BALANCED (Default) | RELAXED |
| :--- | :---: | :---: | :---: |
| **`TAG_MISMATCH`** | -30 | -30 | -30 |
| **`STRUCTURE_MISMATCH`** | -25 | -25 | -20 |
| **`MISSING_TAG`** | -20 | -20 | -15 |
| **`UNEXPECTED_TAG`** | -20 | -20 | -10 |
| **`ORDER_MISMATCH`** | -15 | -10 | -5 |
| **`CARDINALITY_MISMATCH`** | -10 | -5 | -2 |
| **`ATTR_MISMATCH`** | -10 | -5 | -2 |

---

## 🧪 Pruebas Unitarias

El suite incluye pruebas unitarias cubriendo los 7 casos obligatorios de la especificación y pruebas de comparación de atributos. Para ejecutarlas:

```bash
python test_compare_xml.py
```
