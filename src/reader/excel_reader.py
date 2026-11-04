from pathlib import Path
from openpyxl import load_workbook
import xlrd


def leer_excel(ruta):
    ruta = Path(ruta)
    tablas = []

    if ruta.suffix.lower() == ".xlsx":
        libro = load_workbook(ruta, data_only=True, read_only=True)

        for hoja in libro.worksheets:
            filas = list(hoja.iter_rows(values_only=True))
            tablas.append({
                "name": hoja.title,
                "rows": [
                    [str(valor) if valor is not None else "" for valor in fila]
                    for fila in filas
                ]
            })

        libro.close()

    elif ruta.suffix.lower() == ".xls":
        libro = xlrd.open_workbook(ruta)

        for hoja in libro.sheets():
            filas = [
                [str(valor) for valor in hoja.row_values(i)]
                for i in range(hoja.nrows)
            ]
            tablas.append({
                "name": hoja.name,
                "rows": filas
            })

    return {
        "filename": ruta.name,
        "format": ruta.suffix.lower().replace(".", ""),
        "content": {
            "full_text": "",
            "sections": [],
            "tables": tablas
        }
    }