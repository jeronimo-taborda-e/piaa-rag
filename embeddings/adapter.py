import json
from pathlib import Path


"""Si el chunking devuelve objetos, este adaptador los convierte. Sirve para listas de strings"""
def write_contract(output: Path, section_id: str, strategy: str, pieces, context: str | None = None, params: dict | None = None) -> int:
    
    """pieces: lista de str o de objetos con .page_content. Agrega al archivo (modo 'a')."""
    
    output.parent.mkdir(parents=True, exist_ok=True)
    
    with output.open("a", encoding="utf-8") as f:
        for i, piece in enumerate(pieces):
            text = getattr(piece, "page_content", piece).strip()
            if not text:
                continue
            
            row = {
                "id": f"{section_id}-{strategy}-{i}",
                "seccion_id": section_id,
                "chunk_index": i,
                "estrategia_chunking": strategy,
                "texto": text,
                "parametros_chunking": params or {},
            }
            
            if context:
                row["texto_con_contexto"] = f"{context}. {text}"
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    return len(pieces)