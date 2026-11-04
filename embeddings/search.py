# embeddings/search.py
"""Búsqueda semántica sobre los fragmentos, con filtro opcional por estrategia.

Se puede realizar una pregunta al modelo desde la terminal para testear:
    python -m embeddings.search "¿Qué temas se ven en el PIAA de Bases de Datos?"
"""
import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

from embeddings.llm_models import CLIP_TEXT_MODEL, TEXT_MODEL, embed

ROOT = Path(__file__).resolve().parents[1]

Q_FRAGMENTS = """
CALL db.index.vector.queryNodes('fragmento_emb_minilm_v1', $candidates, $vector)
YIELD node AS f, score
WHERE coalesce(f.obsoleto, false) = false
  AND ($strategy IS NULL OR f.estrategia_chunking = $strategy)
MATCH (v:Version)-[:TIENE_SECCION]->(s:Seccion)-[:TIENE_FRAGMENTO]->(f)
RETURN f.id AS id, f.estrategia_chunking AS strategy, v.id AS version, s.tipo AS section,
       f.texto AS text, score
ORDER BY score DESC
LIMIT $k
"""

Q_IMAGES = """
CALL db.index.vector.queryNodes('imagen_emb_clip_v1', $k, $vector)
YIELD node AS i, score
RETURN i.id AS id, i.ruta_archivo AS path, i.descripcion AS text, score
"""


def search(driver, question: str, k: int = 5, strategy: str | None = None) -> list[dict]:
    vector = embed([question], TEXT_MODEL)[0]
    # El filtro va después del índice, así que se piden más candidatos de los que se devuelven.
    records, _, _ = driver.execute_query(Q_FRAGMENTS, vector=vector, k=k, candidates=k * 10,
                                         strategy=strategy)
    return [dict(r) for r in records]


def search_images(driver, question: str, k: int = 5) -> list[dict]:
    vector = embed([question], CLIP_TEXT_MODEL)[0]
    records, _, _ = driver.execute_query(Q_IMAGES, vector=vector, k=k)
    return [dict(r) for r in records]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("-k", type=int, default=5)
    parser.add_argument("--strategy", default=None)
    parser.add_argument("--images", action="store_true")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    password = os.getenv("NEO4J_PASSWORD") or sys.exit("Falta NEO4J_PASSWORD en .env")
    with GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                              auth=(os.getenv("NEO4J_USER", "neo4j"), password)) as driver:
        results = (search_images(driver, args.question, args.k) if args.images
                   else search(driver, args.question, args.k, args.strategy))
    for r in results:
        label = r.get("strategy") or r.get("path")
        print(f"{r['score']:.3f}  {r['id']}  [{label}]\n       {r['text'][:120]}")


if __name__ == "__main__":
    main()