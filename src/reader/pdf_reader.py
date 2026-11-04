from pathlib import Path
import fitz


def leer_pdf(ruta):
    ruta = Path(ruta)
    documento = fitz.open(ruta)

    paginas = []

    for numero, pagina in enumerate(documento, start=1):
        texto = pagina.get_text("text")

        paginas.append({
            "section_id": f"PAGE-{numero:04d}",
            "title": f"Página {numero}",
            "text": texto
        })

    documento.close()

    return {
        "filename": ruta.name,
        "format": "pdf",
        "extraction": {
            "total_pages": len(paginas),
            "extracted_pages": sum(
                1 for pagina in paginas if pagina["text"].strip()
            )
        },
        "content": {
            "full_text": "\n".join(p["text"] for p in paginas),
            "sections": paginas,
            "tables": []
        }
    }