from pathlib import Path

def leer_txt(ruta):
    ruta = Path(ruta)

    try:
        texto = ruta.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        texto = ruta.read_text(encoding="latin-1")

    return {
        "filename": ruta.name,
        "format": "txt",
        "content": {
            "full_text": texto,
            "sections": [],
            "tables": []
        }
    }