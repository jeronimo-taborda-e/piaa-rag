# piaa-rag-neo4j

Sistema RAG para consultar los PIAA (Programa Institucional de Actividad Académica) de la Universidad de Caldas. Lee los documentos, los divide en fragmentos, calcula embeddings de texto e imagen y los guarda en un grafo de **Neo4j 5 Community** para hacer búsqueda semántica.

## Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (en Windows, con WSL2)
- Git
- Python 3.10 o superior

## Puesta en marcha

1. Clonar el repositorio:

   ```bash
   git clone <URL-del-repositorio>
   cd piaa-rag-neo4j
   ```

2. Crear el archivo de variables y poner una contraseña propia (mínimo 8 caracteres):

   ```bash
   cp .env.example .env
   ```

3. Levantar Neo4j:

   ```bash
   docker compose up -d
   ```

4. Instalar las dependencias:

   ```bash
   pip install torch --index-url https://download.pytorch.org/whl/cpu
   pip install -r requirements.txt
   ```

5. Crear el esquema y los datos de ejemplo:

   ```bash
   python init.py
   ```

6. Abrir Neo4j Browser en <http://localhost:7474> con el usuario `neo4j` y la contraseña del `.env`.

## Uso

```bash
python -m src.reader.process_documents                              # leer documentos de data/raw
python -m embeddings.load_fragments data/chunks/<estrategia>.jsonl  # calcular y guardar embeddings
python -m embeddings.search "<pregunta>"                            # buscar
```

## Encender y apagar

```bash
docker compose start
docker compose stop
```

No uses `docker compose down -v`: borra todos los datos de la base.
