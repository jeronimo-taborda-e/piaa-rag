"""Embebe imágenes con CLIP y las guarda como Imagen en la base de datos.

Uso (desde la raíz del repo):
    python -m embeddings.load_images data/imagenes.jsonl --files-root data/images
    python -m embeddings.load_images data/imagenes.jsonl --files-root data/images --replace
"""
import argparse
import hashlib
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase
from PIL import Image, UnidentifiedImageError

from embeddings.contract import read_images
from embeddings.llm_models import CLIP_IMAGE_MODEL, EMBEDDING_VERSION, embed
from validation import ImagenIn

ROOT = Path(__file__).resolve().parents[1]

Q_FINGERPRINTS = """
UNWIND $ids AS id
MATCH (i:Imagen {id: id})
RETURN i.id AS id, i.hash_embedding AS fingerprint
"""

Q_WRITE = """
UNWIND $rows AS row
MATCH (s:Seccion {id: row.seccion_id})
MERGE (i:Imagen {id: row.id})
SET i += row.props
MERGE (s)-[:TIENE_IMAGEN]->(i)
RETURN count(i) AS written
"""

Q_RETIRE = """
UNWIND $groups AS g
MATCH (:Seccion {id: g.seccion_id})-[:TIENE_IMAGEN]->(i:Imagen)
WHERE NOT i.id IN g.ids
DETACH DELETE i
RETURN count(*) AS deleted
"""


def fingerprint(file_bytes: bytes) -> str:
    """Huella del archivo y del modelo: cambia si cambia la imagen o el modelo."""
    digest = hashlib.sha256(f"{CLIP_IMAGE_MODEL}|{EMBEDDING_VERSION}|".encode("utf-8"))
    digest.update(file_bytes)
    return "sha256:" + digest.hexdigest()


def open_rgb(path: Path) -> Image.Image:
    """Abre la imagen y la convierte a RGB; CLIP no acepta transparencias ni escala de grises."""
    with Image.open(path) as img:
        return img.convert("RGB")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", type=Path, help="imagenes.jsonl que cumple el contrato")
    parser.add_argument("--files-root", type=Path, default=ROOT,
                        help="carpeta desde la que se resuelven las ruta_archivo")
    parser.add_argument("--replace", action="store_true",
                        help="borra las imágenes viejas de las mismas secciones que no vienen en el archivo")
    parser.add_argument("--force", action="store_true", help="recalcula aunque la imagen no haya cambiado")
    parser.add_argument("--batch-size", type=int, default=16, help="imágenes por lote del modelo")
    args = parser.parse_args()

    # Paso 1: leer y validar el contrato
    images = read_images(args.file)
    print(f"{len(images)} imágenes leídas")

    # Paso 2: comprobar que los archivos existen y calcular su huella
    paths = {img.id: args.files_root / img.ruta_archivo for img in images}
    missing_files = [img.ruta_archivo for img in images if not paths[img.id].is_file()]
    if missing_files:
        sys.exit(f"No se encontraron {len(missing_files)} archivos en {args.files_root}. "
                 f"Ejemplos: {missing_files[:3]}. Revisa --files-root y ruta_archivo.")
    fingerprints = {img.id: fingerprint(paths[img.id].read_bytes()) for img in images}

    load_dotenv(ROOT / ".env")
    password = os.getenv("NEO4J_PASSWORD") or sys.exit("Falta NEO4J_PASSWORD en .env")
    with GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                              auth=(os.getenv("NEO4J_USER", "neo4j"), password)) as driver:
        driver.verify_connectivity()

        unchanged = set()
        if not args.force:
            records, _, _ = driver.execute_query(Q_FINGERPRINTS, ids=list(fingerprints))
            unchanged = {r["id"] for r in records if r["fingerprint"] == fingerprints[r["id"]]}
        pending = [img for img in images if img.id not in unchanged]
        print(f"{len(unchanged)} sin cambios · {len(pending)} por embeber")

        if pending:
            # Paso 3: abrir y embeber por lotes, para no tener todas las imágenes en memoria
            today, rows, unreadable = date.today(), [], []
            for start in range(0, len(pending), args.batch_size):
                batch, pil_images = [], []
                for img in pending[start:start + args.batch_size]:
                    try:
                        pil_images.append(open_rgb(paths[img.id]))
                        batch.append(img)
                    except (UnidentifiedImageError, OSError):
                        unreadable.append(img.ruta_archivo)
                if not batch:
                    continue
                vectors = embed(pil_images, CLIP_IMAGE_MODEL, args.batch_size)

                # Paso 4: validar con ImagenIn
                for img, vec in zip(batch, vectors):
                    image = ImagenIn(
                        **img.model_dump(), formato=img.file_format(), embedding_clip=vec,
                        modelo_embedding=CLIP_IMAGE_MODEL, version_embedding=EMBEDDING_VERSION,
                        fecha_ingesta=today, hash_embedding=fingerprints[img.id],
                    )
                    props = image.model_dump(exclude={"id", "seccion_id"}, exclude_none=True)
                    rows.append({"id": image.id, "seccion_id": image.seccion_id, "props": props})
            if unreadable:
                print(f"Aviso: {len(unreadable)} archivos no se pudieron abrir como imagen: {unreadable[:3]}")

            # Paso 5: escribir en Neo4j
            written = 0
            for i in range(0, len(rows), 500):
                records, _, _ = driver.execute_query(Q_WRITE, rows=rows[i:i + 500])
                written += records[0]["written"]
            print(f"{written} imágenes escritas")
            if written < len(rows):
                existing, _, _ = driver.execute_query(
                    "UNWIND $ids AS id MATCH (s:Seccion {id: id}) RETURN s.id AS id",
                    ids=list({r["seccion_id"] for r in rows}))
                missing = {r["seccion_id"] for r in rows} - {r["id"] for r in existing}
                print(f"Aviso: {len(rows) - written} imágenes no se guardaron; "
                      f"estas secciones no existen en Neo4j: {sorted(missing)[:5]}")

        if args.replace:
            groups = {}
            for img in images:
                groups.setdefault(img.seccion_id, []).append(img.id)
            records, _, _ = driver.execute_query(Q_RETIRE, groups=[
                {"seccion_id": s, "ids": ids} for s, ids in groups.items()])
            print(f"{records[0]['deleted'] if records else 0} imágenes viejas borradas")


if __name__ == "__main__":
    main()
