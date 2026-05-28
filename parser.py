import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Union

def parse_xml(source: Union[str, Path]) -> ET.Element:
    """
    Parses an XML source (file path, Path object, or raw XML string)
    and returns the root element.
    
    Raises:
        ValueError: If the XML is malformed or the file cannot be read.
    """
    if isinstance(source, Path):
        source = str(source)
        
    # Check if source is a file path
    if isinstance(source, str) and not source.strip().startswith("<"):
        try:
            tree = ET.parse(source)
            return tree.getroot()
        except ET.ParseError as e:
            raise ValueError(f"XML parse error in file '{source}': {e}")
        except FileNotFoundError:
            raise ValueError(f"XML file not found: '{source}'")
        except PermissionError:
            raise ValueError(f"Permission denied reading file: '{source}'")
        except Exception as e:
            raise ValueError(f"Error reading file '{source}': {e}")
    else:
        # Assume it is a raw XML string
        try:
            return ET.fromstring(source)
        except ET.ParseError as e:
            raise ValueError(f"XML parse error in string: {e}")
