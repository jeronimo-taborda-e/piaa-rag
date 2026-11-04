# embeddings/load_fragments.py
"""Embebe un chunks.jsonl (cualquier estrategia) y lo guarda como Fragmento en la base de datos.

Uso (tenemos que estar en la raiz del repo):
    python -m embeddings.load_fragments data/chunks/semantic.jsonl
    python -m embeddings.load_fragments data/chunks/semantic.jsonl --with-clip --replace
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

from embeddings.contract import read_chunks
from embeddings.llm_models import (CLIP_TEXT_MODEL, EMBEDDING_VERSION, TEXT_MODEL,
                               embed, find_long_chunks)
from validation import FragmentoIn

ROOT = Path(__file__).resolve().parents[1]

Q_FINGERPRINTS = """
UNWIND $ids AS id
MATCH (f:Fragmento {id: id})
RETURN f.id AS id, f.hash_embedding AS fingerprint
"""

Q_WRITE = """
UNWIND $rows AS row
MATCH (s:Seccion {id: row.seccion_id})
MERGE (f:Fragmento {id: row.id})
SET f += row.props
MERGE (s)-[:TIENE_FRAGMENTO]->(f)
RETURN count(f) AS written
"""

Q_RETIRE = """
UNWIND $groups AS g
MATCH (:Seccion {id: g.seccion_id})-[:TIENE_FRAGMENTO]->(f:Fragmento {estrategia_chunking: g.strategy})
WHERE NOT f.id IN g.ids
OPTIONAL MATCH (f)<-[link:RESPONDIDA_CON|EN]-()
WITH f, count(link) AS links
SET f.obsoleto = links > 0
WITH f WHERE NOT f.obsoleto
DETACH DELETE f
RETURN count(*) AS deleted
"""


def fingerprint(text: str, with_clip: bool) -> str:
    base = f"{TEXT_MODEL}|{EMBEDDING_VERSION}|clip={with_clip}|{text}"
    return "sha256:" + hashlib.sha256(base.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", type=Path, help="chunks.jsonl que cumple el contrato")
    parser.add_argument("--with-clip", action="store_true", help="calcula también embedding_clip del texto")
    parser.add_argument("--replace", action="store_true",
                        help="retira los fragmentos viejos de las mismas secciones y estrategia")
    parser.add_argument("--force", action="store_true", help="recalcula aunque el texto no haya cambiado")
    parser.add_argument("--batch-size", type=int, default=32, help="textos por lote del modelo")
    args = parser.parse_args()

    #leer y validar el contrato
    chunks = read_chunks(args.file)
    strategies = sorted({c.estrategia_chunking for c in chunks})
    print(f"{len(chunks)} chunks leídos · estrategias: {', '.join(strategies)}")

    # armar el texto a embeber y avisar de los que se truncarán
    texts = [c.text_to_embed() for c in chunks]
    limit, long_ones = find_long_chunks(texts, TEXT_MODEL)
    if long_ones:
        print(f"Aviso: {len(long_ones)} chunks pasan de {limit} tokens y MiniLM los truncará. "
              f"Ejemplos: {[chunks[i].id for i in long_ones[:3]]}")
    fingerprints = {c.id: fingerprint(t, args.with_clip) for c, t in zip(chunks, texts)}

    load_dotenv(ROOT / ".env")
    password = os.getenv("NEO4J_PASSWORD") or sys.exit("Falta NEO4J_PASSWORD en .env")
    with GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                              auth=(os.getenv("NEO4J_USER", "neo4j"), password)) as driver:
        driver.verify_connectivity()

        unchanged = set()
        if not args.force:
            records, _, _ = driver.execute_query(Q_FINGERPRINTS, ids=list(fingerprints))
            unchanged = {r["id"] for r in records if r["fingerprint"] == fingerprints[r["id"]]}
        pending = [(c, t) for c, t in zip(chunks, texts) if c.id not in unchanged]
        print(f"{len(unchanged)} sin cambios · {len(pending)} por embeber")

        if pending:
            #calcular los vectores en lotes
            pending_texts = [t for _, t in pending]
            vectors = embed(pending_texts, TEXT_MODEL, args.batch_size)
            clip_vectors = (embed(pending_texts, CLIP_TEXT_MODEL, args.batch_size) if args.with_clip else [None] * len(pending))

            #validar con FragmentoIn y escribir en Neo4j
            today, rows = date.today(), []
            for (c, t), vec, clip_vec in zip(pending, vectors, clip_vectors):
                fragment = FragmentoIn(
                    id=c.id, seccion_id=c.seccion_id, chunk_index=c.chunk_index,
                    estrategia_chunking=c.estrategia_chunking, texto=c.texto,
                    texto_con_contexto=t, idioma=c.idioma, fecha_ingesta=today,
                    embedding=vec, modelo_embedding=TEXT_MODEL, version_embedding=EMBEDDING_VERSION,
                    embedding_clip=clip_vec, modelo_embedding_clip=CLIP_TEXT_MODEL if clip_vec else None,
                    parametros_chunking=(json.dumps(c.parametros_chunking, ensure_ascii=False, sort_keys=True)
                                         if c.parametros_chunking else None),
                    hash_embedding=fingerprints[c.id],
                )
                props = fragment.model_dump(exclude={"id", "seccion_id"}, exclude_none=True)
                rows.append({"id": fragment.id, "seccion_id": fragment.seccion_id, "props": props})

            written = 0
            for i in range(0, len(rows), 500):
                records, _, _ = driver.execute_query(Q_WRITE, rows=rows[i:i + 500])
                written += records[0]["written"]
            print(f"{written} fragmentos escritos")
            if written < len(rows):
                existing, _, _ = driver.execute_query(
                    "UNWIND $ids AS id MATCH (s:Seccion {id: id}) RETURN s.id AS id",
                    ids=list({r["seccion_id"] for r in rows}))
                missing = {r["seccion_id"] for r in rows} - {r["id"] for r in existing}
                print(f"Aviso: {len(rows) - written} chunks no se guardaron; "
                      f"estas secciones no existen en Neo4j: {sorted(missing)[:5]}")

        if args.replace:
            groups = {}
            for c in chunks:
                groups.setdefault((c.seccion_id, c.estrategia_chunking), []).append(c.id)
            records, _, _ = driver.execute_query(Q_RETIRE, groups=[
                {"seccion_id": s, "strategy": st, "ids": ids} for (s, st), ids in groups.items()])
            print(f"{records[0]['deleted'] if records else 0} fragmentos viejos borrados "
                  "(los citados por Consulta o Hallazgo quedan con obsoleto = true)")


if __name__ == "__main__":
    main()