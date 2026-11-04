"""Carga los modelos una sola vez y calcula vectores normalizados."""
from functools import lru_cache

from sentence_transformers import SentenceTransformer

TEXT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"    # 384 dims
CLIP_TEXT_MODEL = "clip-ViT-B-32-multilingual-v1"       # 512 dims, espacio de CLIP
CLIP_IMAGE_MODEL = "clip-ViT-B-32"                      # 512 dims
EMBEDDING_VERSION = 1                                   # súbelo si cambias de modelo


@lru_cache(maxsize=None)
def load_model(name: str) -> SentenceTransformer:
    return SentenceTransformer(name)


def embed(inputs: list, model_name: str, batch_size: int = 32) -> list[list[float]]:
    """inputs: textos (str) o imágenes PIL. Devuelve listas de float de norma 1."""
    vectors = load_model(model_name).encode(
        inputs,
        batch_size=batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=len(inputs) > batch_size,
    )
    return vectors.astype(float).tolist()


def find_long_chunks(texts: list[str], model_name: str) -> tuple[int, list[int]]:
    """Índices de los textos que el modelo va a truncar."""
    model = load_model(model_name)
    limit = model.max_seq_length
    long_ones = [i for i, t in enumerate(texts) if len(model.tokenizer(t)["input_ids"]) > limit]
    return limit, long_ones