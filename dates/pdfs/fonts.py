import tempfile
from pathlib import Path
from urllib.request import urlopen

_fonts_paths: dict[str, str] = {}

def get_montserrat_font(style: str):
    if style in _fonts_paths and _fonts_paths[style].exists():
        return _fonts_paths[style]
    styles = {
        "": "Regular",
        "B": "Bold",
        "I": "Italic",
        "BI": "BoldItalic",
    }
    real_style = styles.get(str(style).upper(), "Regular")
    BASE_URL = "https://raw.githubusercontent.com/JulietaUla/Montserrat/master/fonts/ttf"
    with urlopen(f"{BASE_URL}/Montserrat-{real_style}.ttf") as f:
        data = f.read()
    with tempfile.NamedTemporaryFile(suffix=".ttf", delete=False) as f:
        f.write(data)
        file = Path(f.name)
        _fonts_paths[style] = file
        return file
