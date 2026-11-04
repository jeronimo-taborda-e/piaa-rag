# embeddings/contract.py
"""Lo que hace este archivo es leer y validar el archivo chunks.jsonl que entrega el chunking."""
import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ChunkIn(BaseModel):
    """Contrato del Paso 1. Cualquier chunker que produzca esto sirve."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(min_length=1)
    seccion_id: str = Field(min_length=1)
    chunk_index: int = Field(ge=0)
    estrategia_chunking: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    texto: str = Field(min_length=1)
    texto_con_contexto: str | None = None
    idioma: str = Field(default="es", min_length=2, max_length=5)
    parametros_chunking: dict = Field(default_factory=dict)

    def text_to_embed(self) -> str:
        return self.texto_con_contexto or self.texto


def read_chunks(path: Path) -> list[ChunkIn]:
    chunks, errors = [], []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                chunks.append(ChunkIn.model_validate_json(line))
            except ValidationError as e:
                fields = ", ".join(f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors())
                errors.append(f"  línea {line_no}: {fields}")

    ids = [c.id for c in chunks]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        errors.append(f"  ids repetidos: {sorted(duplicates)[:5]}")

    keys = [(c.seccion_id, c.estrategia_chunking, c.chunk_index) for c in chunks]
    if len(set(keys)) != len(keys):
        errors.append("  hay chunk_index repetidos para la misma sección y estrategia")

    if errors:
        sys.exit(f"{path} no cumple el contrato:\n" + "\n".join(errors[:20]))
    return chunks