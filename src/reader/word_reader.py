from pathlib import Path
from docx import Document


def leer_word(ruta):
    ruta = Path(ruta)
    documento = Document(ruta)

    parrafos = [
        p.text for p in documento.paragraphs if p.text.strip()
    ]

    tablas = []

    for tabla in documento.tables:
        filas = [
            [celda.text for celda in fila.cells]
            for fila in tabla.rows
        ]
        tablas.append({"rows": filas})

    return {
        "filename": ruta.name,
        "format": "docx",
        "content": {
            "full_text": "\n".join(parrafos),
            "sections": [],
            "tables": tablas
        }
    }