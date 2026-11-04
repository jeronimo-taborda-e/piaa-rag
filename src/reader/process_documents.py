import json
from pathlib import Path
from .document_reader import leer_documento

CARPETA_ENTRADA = Path("data/raw")
CARPETA_SALIDA = Path("data/processed/documents")

def procesar_documentos():
    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    for archivo in CARPETA_ENTRADA.rglob("*"):
        if not archivo.is_file():
            continue
        try:
            resultado = leer_documento(archivo)
            resultado["document_id"] = archivo.stem
            salida = CARPETA_SALIDA / f"{archivo.stem}.json"
            with salida.open("w", encoding="utf-8") as json_file:
                json.dump(
                    resultado,
                    json_file,
                    ensure_ascii=False,
                    indent=4
                )
            print(f"[OK] {archivo.name}")
        except Exception as error:
            print(f"[ERROR] {archivo.name}: {error}")


if __name__ == "__main__":
    procesar_documentos()