from pathlib import Path
import csv


def leer_csv(ruta):
    ruta = Path(ruta)

    with ruta.open("r", encoding="utf-8-sig", newline="") as archivo:
        contenido = list(csv.DictReader(archivo))

    return {
        "filename": ruta.name,
        "format": "csv",
        "content": {
            "full_text": "",
            "sections": [],
            "tables": [
                {
                    "name": ruta.stem,
                    "rows": contenido
                }
            ]
        }
    }