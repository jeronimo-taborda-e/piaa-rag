from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

DIM_MINILM = 384  # paraphrase-multilingual-MiniLM-L12-v2
DIM_CLIP = 512    # clip-ViT-B-32

VectorMiniLM = Annotated[list[float], Field(min_length=DIM_MINILM, max_length=DIM_MINILM)]
VectorClip = Annotated[list[float], Field(min_length=DIM_CLIP, max_length=DIM_CLIP)]

EstrategiaChunking = Annotated[str, Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]

TipoSeccion = Literal[
    "objetivo_general", "objetivos_especificos", "contenidos",
    "metodologia", "evaluacion", "bibliografia", "desempenos", "otra",
]


class Strict(BaseModel):
    """Rechaza campos no declarados (como validationLevel: strict)."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PIAAIn(Strict):
    codigo: str = Field(min_length=1)
    estado: Literal["VIGENTE", "BORRADOR", "HISTORICO"]
    origen: Literal["migracion", "flujo"]
    completitud: float = Field(ge=0, le=1)
    actividad_codigo: str = Field(min_length=1) 


class VersionIn(Strict):
    id: str = Field(min_length=1)
    piaa_codigo: str = Field(min_length=1)      
    numero: int = Field(ge=1)
    estado: Literal["VIGENTE", "BORRADOR", "HISTORICO"]
    es_publica: bool
    fecha: date
    idioma: str = Field(default="es", min_length=2, max_length=5)
    creada_en: date
    aprobada_en: date | None = None
    fuente: str = Field(min_length=1)
    hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class SeccionIn(Strict):
    id: str = Field(min_length=1)
    version_id: str = Field(min_length=1)       
    tipo: TipoSeccion
    titulo_original: str = Field(min_length=1)
    orden: int = Field(ge=0)
    texto: str = Field(min_length=1)


class FragmentoIn(Strict):
    id: str = Field(min_length=1)
    seccion_id: str = Field(min_length=1)      
    chunk_index: int = Field(ge=0)
    estrategia_chunking: EstrategiaChunking
    texto: str = Field(min_length=1)
    texto_con_contexto: str = Field(min_length=1)
    embedding: VectorMiniLM
    modelo_embedding: str = Field(min_length=1)
    version_embedding: int = Field(ge=1)
    embedding_clip: VectorClip | None = None
    modelo_embedding_clip: str | None = None
    idioma: str = Field(default="es", min_length=2, max_length=5)
    fecha_ingesta: date
    parametros_chunking: str | None = None  
    hash_embedding: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    obsoleto: bool = False                  


class ImagenIn(Strict):
    id: str = Field(min_length=1)
    seccion_id: str = Field(min_length=1)      
    ruta_archivo: str = Field(min_length=1)
    formato: Literal["png", "jpg", "jpeg"]
    descripcion: str = Field(min_length=1)
    etiquetas: list[str] = Field(default_factory=list)
    requirio_ocr: bool = False
    embedding_clip: VectorClip
    modelo_embedding: str = Field(min_length=1)
    version_embedding: int = Field(ge=1)
    fecha_ingesta: date
    hash_embedding: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")


class ConsultaIn(Strict):
    id: str = Field(min_length=1)
    chat_id: str = Field(min_length=1)         
    pregunta: str = Field(min_length=1)
    fecha: date
    fragmentos_usados: list[str] = Field(default_factory=list) 
