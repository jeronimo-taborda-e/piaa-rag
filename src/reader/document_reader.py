from pathlib import Path
from .pdf_reader import leer_pdf
from .word_reader import leer_word
from .excel_reader import leer_excel
from .csv_reader import leer_csv
from .txt_reader import leer_txt

LECTORES = {
    ".pdf": leer_pdf,
    ".docx": leer_word,
    ".xlsx": leer_excel,
    ".xls": leer_excel,
    ".csv": leer_csv,
    ".txt": leer_txt
}

def leer_documento(ruta):
    ruta = Path(ruta)

    if not ruta.exists() or not ruta.is_file():
        raise FileNotFoundError(f"No existe el archivo: {ruta}")

    lector = LECTORES.get(ruta.suffix.lower())

    if lector is None:
        raise ValueError(f"Formato no compatible: {ruta.suffix}")

    return lector(ruta)