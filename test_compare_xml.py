import unittest
from parser import parse_xml
from normalizer import normalize_element
from comparator import compare_nodes
from scorer import calculate_score

class TestXMLComparisonEngine(unittest.TestCase):

    def run_comparison(self, xml_expected: str, xml_candidate: str, mode: str = "balanced", compare_attrs: bool = False):
        node_a = normalize_element(parse_xml(xml_expected), compare_attrs=compare_attrs)
        node_b = normalize_element(parse_xml(xml_candidate), compare_attrs=compare_attrs)
        diffs = compare_nodes(node_a, node_b, compare_attrs=compare_attrs)
        score, status, compatible = calculate_score(diffs, mode=mode)
        return score, status, compatible, diffs

    def test_case_1_same_xml(self):
        """Caso 1: Mismo XML -> 100%"""
        xml_a = """<libro>
            <titulo>abc</titulo>
            <autor>
                <nombre>Juan</nombre>
            </autor>
        </libro>"""
        xml_b = xml_a
        score, status, compatible, diffs = self.run_comparison(xml_a, xml_b)
        
        self.assertEqual(score, 100.0)
        self.assertEqual(status, "EXACT_MATCH")
        self.assertTrue(compatible)
        self.assertEqual(len(diffs), 0)

    def test_case_2_same_xml_different_content(self):
        """Caso 2: Mismo XML, distinto contenido -> 100% (text content is ignored)"""
        xml_a = """<libro>
            <titulo>abc</titulo>
            <autor>
                <nombre>Juan</nombre>
            </autor>
        </libro>"""
        xml_b = """<libro>
            <titulo>xyz</titulo>
            <autor>
                <nombre>Pedro</nombre>
            </autor>
        </libro>"""
        score, status, compatible, diffs = self.run_comparison(xml_a, xml_b)
        
        self.assertEqual(score, 100.0)
        self.assertEqual(status, "EXACT_MATCH")
        self.assertTrue(compatible)
        self.assertEqual(len(diffs), 0)

    def test_case_3_missing_tag(self):
        """Caso 3: Etiqueta faltante -> MISSING_TAG"""
        xml_expected = """<libro>
            <titulo/>
            <isbn/>
        </libro>"""
        xml_candidate = """<libro>
            <titulo/>
        </libro>"""
        score, status, compatible, diffs = self.run_comparison(xml_expected, xml_candidate)
        
        self.assertTrue(any(d.type == "MISSING_TAG" and d.path == "/libro/isbn" for d in diffs))
        self.assertLess(score, 100.0)
        self.assertEqual(status, "STRUCTURE_COMPATIBLE")  # Score 80.0 is compatible

    def test_case_4_different_order(self):
        """Caso 4: Orden distinto -> ORDER_MISMATCH"""
        xml_expected = """<persona>
            <nombre/>
            <apellido/>
        </persona>"""
        xml_candidate = """<persona>
            <apellido/>
            <nombre/>
        </persona>"""
        score, status, compatible, diffs = self.run_comparison(xml_expected, xml_candidate)
        
        self.assertTrue(any(d.type == "ORDER_MISMATCH" and d.path == "/persona" for d in diffs))
        self.assertLess(score, 100.0)

    def test_case_5_cardinality_difference(self):
        """Caso 5: 4 autores vs 1 autor -> CARDINALITY_MISMATCH y Similarity alta (>85%)"""
        xml_expected = """<autores>
            <autor/>
            <autor/>
            <autor/>
            <autor/>
        </autores>"""
        xml_candidate = """<autores>
            <autor/>
        </autores>"""
        score, status, compatible, diffs = self.run_comparison(xml_expected, xml_candidate, mode="balanced")
        
        self.assertTrue(any(d.type == "CARDINALITY_MISMATCH" and d.path == "/autores/autor" and d.expected == 4 and d.actual == 1 for d in diffs))
        self.assertGreater(score, 85.0)
        self.assertEqual(status, "STRUCTURE_COMPATIBLE")

    def test_case_6_different_internal_structure(self):
        """Caso 6: Estructura interna distinta -> STRUCTURE_MISMATCH"""
        xml_expected = """<autor>
            <nombre/>
            <apellido/>
        </autor>"""
        xml_candidate = """<autor>
            <nombre/>
            <edad/>
        </autor>"""
        score, status, compatible, diffs = self.run_comparison(xml_expected, xml_candidate)
        
        # Should detect STRUCTURE_MISMATCH at /autor with missing=apellido and unexpected=edad
        struct_diff = [d for d in diffs if d.type == "STRUCTURE_MISMATCH" and d.path == "/autor"]
        self.assertEqual(len(struct_diff), 1)
        self.assertIn("apellido", struct_diff[0].expected)
        self.assertIn("edad", struct_diff[0].actual)

    def test_case_7_unexpected_tag(self):
        """Caso 7: Nodo inesperado -> UNEXPECTED_TAG"""
        xml_expected = """<libro>
            <titulo/>
            <isbn/>
        </libro>"""
        xml_candidate = """<libro>
            <titulo/>
            <isbn/>
            <editor/>
        </libro>"""
        score, status, compatible, diffs = self.run_comparison(xml_expected, xml_candidate)
        
        self.assertTrue(any(d.type == "UNEXPECTED_TAG" and d.path == "/libro/editor" for d in diffs))
        self.assertLess(score, 100.0)

    def test_attribute_comparison(self):
        """Test optional attribute comparison"""
        xml_expected = """<libro id="123" lang="es">
            <titulo/>
        </libro>"""
        xml_candidate = """<libro id="123" lang="en">
            <titulo/>
        </libro>"""
        
        # Default: ignore attributes
        score, status, _, diffs = self.run_comparison(xml_expected, xml_candidate, compare_attrs=False)
        self.assertEqual(score, 100.0)
        self.assertEqual(len(diffs), 0)
        
        # Enabled: catch ATTR_MISMATCH
        score, status, _, diffs = self.run_comparison(xml_expected, xml_candidate, compare_attrs=True)
        self.assertTrue(any(d.type == "ATTR_MISMATCH" and d.path == "/libro" for d in diffs))
        self.assertLess(score, 100.0)

if __name__ == "__main__":
    unittest.main()
