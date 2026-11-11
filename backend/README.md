# FastAPI Project - Backend

## Requirements

* [Docker](https://www.docker.com/).
* [uv](https://docs.astral.sh/uv/) for Python package and environment management.

## Local Development

Run the backend locally and connect it to PostgreSQL in Docker Compose.

From the project root, start PostgreSQL and Mailpit:

```console
$ docker compose up -d db mailpit
```

Then, from `./backend/`, install the dependencies, prepare the database, and start the development server:

```console
$ uv sync
$ uv run bash scripts/prestart.sh
$ uv run fastapi dev
```

The API is available at `http://localhost:8000`, with automatic interactive docs at `http://localhost:8000/docs`.

## General Workflow

Run backend commands from `./backend/` with `uv run`. Make sure your editor uses the Python interpreter at `.venv/bin/python` in the project root.

Modify or add SQLModel models for data and SQL tables in `./backend/app/models.py`, API endpoints in `./backend/app/api/`, CRUD (Create, Read, Update, Delete) utils in `./backend/app/crud.py`.

## VS Code

There are already configurations in place to run the backend through the VS Code debugger, so that you can use breakpoints, pause and explore variables, etc.

The setup is also already configured so you can run the tests through the VS Code Python tests tab.

## Full Stack with Docker Compose

To run the backend and built frontend in Docker Compose:

```console
$ docker compose run --rm backend bash scripts/prestart.sh
$ docker compose watch
```

The application is available at `http://localhost:8000`.

### Docker Compose Override

The `compose.override.yml` file contains local settings for published ports, source synchronization, automatic image rebuilds, and backend reloads. Docker Compose applies it automatically when you run `docker compose` without an explicit file list.

To open a shell in the backend container:

```console
$ docker compose exec backend bash
```

## Backend Tests

To test the backend from the `backend` directory, run:

```console
$ uv run bash scripts/test.sh
```

The tests run with Pytest. Modify existing tests or add new ones in `./backend/tests/`.

If you use GitHub Actions, the tests will run automatically.

### Test a Running Stack

If your stack is already up and you just want to run the tests, you can use:

```bash
docker compose exec backend bash scripts/tests-start.sh
```

The `/app/backend/scripts/tests-start.sh` script calls `pytest`. If you need to pass extra arguments to `pytest`, you can pass them to that command and they will be forwarded.

For example, to stop on first error:

```bash
docker compose exec backend bash scripts/tests-start.sh -x
```

### Test Coverage

When the tests run, they generate `htmlcov/index.html`. Open it in your browser to inspect the test coverage.

## Migrations

Make sure you create a revision of your models and upgrade the database with that revision every time you change them. From the `backend` directory, use `uv` to run Alembic against the PostgreSQL container:

* Alembic is already configured to import your SQLModel models from `./backend/app/models.py`.

* After changing a model (for example, adding a column), create a revision:

```console
$ uv run alembic revision --autogenerate -m "Add column last_name to User model"
```

* Commit to the git repository the files generated in the alembic directory.

* After creating the revision, run the migration in the database (this is what will actually change the database):

```console
$ uv run alembic upgrade head
```

If you don't want to use migrations at all, uncomment the lines in the file at `./backend/app/core/db.py` that end in:

```python
SQLModel.metadata.create_all(engine)
```

and comment the line in the file `scripts/prestart.sh` that contains:

```console
$ alembic upgrade head
```

If you don't want to start with the default models and want to remove them / modify them, from the beginning, without having any previous revision, you can remove the revision files (`.py` Python files) under `./backend/app/alembic/versions/`. And then create a first migration as described above.

## Email Templates

The email templates are written with [React Email](https://react.email) in `./packages/react-email/`. The `emails` directory holds one component per email and the `ui` directory holds the shared components (layout, heading, button, link, callout).

The rendered HTML in `./backend/app/email-templates/` is generated from those components. It is what the application sends and should not be edited by hand.

To preview the emails while editing them, start the dev server from the root of the project:

```console
$ bun run email:dev
```

Values coming from the backend are declared as Jinja placeholders in the component props, for example `username = "{{ username }}"`. The context for each email is built in `generate_*_email()` in `./backend/app/utils.py`, so a new placeholder needs to be added there too.

Once you are done, regenerate the templates used by the application:

```console
$ bun run email:export
```

## Importación TXT de Chill-Lang

Desde **Mi biblioteca → Importar TXT**, selecciona un archivo `.txt` UTF-8
(máximo **5 MiB = 5 242 880 bytes**). También se admite UTF-8 con BOM.
El archivo se procesa en memoria y no se almacena como documento.

```text
TITLE: Une aventure à Paris
AUTHOR: Chill-Lang

=== CHAPTER: Le départ ===

Camille se réveille très tôt.
Elle regarde par la fenêtre.

=== CHAPTER: La rencontre ===

Camille arrive à la gare.
Elle rencontre Sophie.
```

- `TITLE:` es obligatorio y `AUTHOR:` opcional; no se permiten cabeceras repetidas
  ni texto libre antes del primer capítulo.
- Los títulos del libro y los capítulos y el autor tienen un máximo de 255 caracteres.
- Cada capítulo empieza con `=== CHAPTER: Nombre ===`, en una línea propia,
  y debe contener texto. Debe existir al menos un capítulo.
- El orden determina `position` desde 1. No se deducen capítulos automáticamente.
- Se conservan párrafos, espacios y líneas en blanco del contenido, incluso junto
  a las cabeceras. CRLF y CR se normalizan a LF.
- Se rechazan archivos vacíos, cabeceras malformadas, UTF-8 inválido y caracteres nulos.

`POST /api/v1/books/import-txt` requiere un token y un archivo multipart en el campo
`file`. Devuelve `201` con `BookPublic`; `413` si supera el límite; `422` para un
archivo inválido o ausente. El propietario procede de la sesión autenticada.
El libro y todos sus capítulos se guardan en una única transacción; un fallo de
persistencia ejecuta rollback. No se necesitan tablas ni migraciones adicionales.

## Importación EPUB (fase 1)

**Mi biblioteca → Importar libro** admite TXT y EPUB. La extensión selecciona el
endpoint generado: `POST /api/v1/books/import-epub` recibe multipart `file` y
responde `201` con `BookPublic`. El endpoint TXT y su límite de 5 MiB se conservan.

El parser EPUB usa EbookLib 0.21 y lxml 6.1.3 (verificados en Python 3.14):

- Extrae título, autores e idioma. El idioma solo forma parte del resultado del
  parser; no se añade una columna al modelo.
- Recorre el spine y utiliza el índice y los encabezados para separar secciones.
  Una continuación sin encabezado se une solo si su título de documento coincide
  con el capítulo anterior identificado por encabezado o índice. Si no hay señales
  suficientes, conserva secciones del spine con su título de origen o nombre de
  recurso; no intenta adivinar capítulos mediante el nombre del archivo.
- Conserva texto plano, párrafos y diálogos; omite navegación, portadas explícitas,
  scripts, estilos e imágenes. No conserva estilos, tablas complejas ni imágenes.
- No extrae el ZIP al disco ni conserva el archivo original. Rechaza rutas
  externas, recorridos `..`, entradas duplicadas y ZIP cifrados. El XML se valida
  sin red ni carga de DTD y se vuelve a serializar sin DTD antes de usar EbookLib.
  Las entidades de caracteres XHTML estándar se convierten de forma local;
  las declaraciones de entidades personalizadas se rechazan.
- Límite de subida: **20 MiB**; total descomprimido: **100 MiB**; recurso individual:
  **10 MiB**; máximo **2000 entradas**, con relación de compresión máxima **200:1**.
  Los límites de ZIP incluyen todos los recursos, aunque no se utilicen como texto.
- No admite DRM, maquetación fija ni contenedores con múltiples versiones del libro.
  Se permite la ofuscación estándar de fuentes, que no se utiliza para la lectura.
  EPUB malformados se rechazan; no se garantiza reconstruir la división editorial
  de capítulos de todos los libros.

TXT y EPUB comparten `persist_imported_book`: libro y capítulos se insertan en una
única transacción con rollback ante errores. El propietario siempre es el usuario
autenticado. Ambos formatos utilizan el mismo detalle, índice y lector React.
No se crean tablas ni migraciones.

## Motor lingüístico francés (fase 3)

`POST /api/v1/books/{book_id}/chapters/{chapter_id}/analyze` requiere autenticación.
El endpoint reutiliza la comprobación de propietario y pertenencia del capítulo;
los recursos ajenos o inexistentes devuelven 404. El cuerpo es:

```json
{"start_offset": 8, "end_offset": 15, "offset_unit": "utf-16"}
```

Los índices son **globales al contenido persistido del capítulo**, con intervalo
semiabierto `[inicio, fin)`. Para `😀 Elle aperçut un homme.` seleccionan `aperçut`.
No se envía texto para analizar: el backend obtiene el original de PostgreSQL.

El servicio convierte las unidades UTF-16 de JavaScript a índices de puntos de
código de Python; rechaza posiciones fuera del capítulo, intervalos vacíos,
selecciones de solo espacios y extremos que parten un par sustituto. La selección
se limita a 512 unidades UTF-16. spaCy recibe una ventana de como máximo 4096
caracteres Python, no el capítulo completo. La búsqueda de la posición recorre
el prefijo original una vez; las conversiones inversas se calculan dentro de la
ventana acotada.

La respuesta conserva la selección exacta y añade tokens que la solapan. Una
selección parcial no se amplía silenciosamente: `selection_covers_full_tokens`
indica si incluye completos los tokens devueltos. Sus posiciones y las de sus
núcleos sintácticos vuelven a ser offsets UTF-16 globales del capítulo.
Se devuelven las oraciones que se solapan con la selección y su contexto literal.
`context_truncated`/`is_truncated` señalan oraciones que podrían estar incompletas
al tocar un borde de la ventana. Si no hay límites oracionales disponibles, se
utiliza el fragmento original de la ventana sin inventar una oración.

`None` indica una anotación ausente; un diccionario morfológico vacío indica que
el pipeline no asignó rasgos a ese token. No se fabrica una dependencia o un lema.
Los errores de selección producen 422 y un modelo no disponible produce 503.

### Componentes y despliegue

- `services/french_nlp.py`: carga protegida por lock, reutilizada una vez por
  proceso, conversión Unicode, contexto y análisis. No utiliza SQL ni FastAPI.
- `models.py`: contratos `SelectionAnalysisRequest`, `AnalyzedToken`,
  `AnalyzedSentence` y `SelectionAnalysis`, sin nuevas tablas.
- `api/routes/books.py`: autorización, lectura del capítulo y adaptación HTTP.
- El cliente OpenAPI generado y `useAnalyzeSelection` conservan la autenticación
  y el manejo de errores actuales. El panel solicita el análisis explícitamente;
  cambiar la selección o el capítulo descarta resultados anteriores. Si la
  selección devuelta difiere del texto que muestra el lector, se pide reabrir el
  capítulo en lugar de presentar anotaciones sobre otro texto.

Se fijan **spaCy 3.8.18** y **fr_core_news_sm 3.8.0**. El wheel del modelo se
referencia en `[tool.uv.sources]` y se bloquea con sus hashes en `uv.lock`.
`uv sync --frozen --package app` instala ambas dependencias también en Docker;
no hay descargas de modelos durante las peticiones. El componente NER se excluye
porque esta fase no solicita reconocimiento de entidades.

Medición orientativa en este entorno con Python 3.14.3: importar spaCy tomó
0,59 s; cargar el modelo, 1,58 s; analizar 4096 caracteres, entre 21,8 y 26,3 ms
(cinco ejecuciones); pico RSS del proceso, 307,5 MiB. No es una garantía de producción.
El Docker actual tiene cuatro workers y cada uno carga su propio pipeline. La
primera petición de cada proceso paga el coste de carga; las siguientes lo reutilizan.

### Conceptos de spaCy

1. **Pipeline NLP:** secuencia de operaciones que transforma texto en un documento
   anotado. Este modelo utiliza `tok2vec`, `morphologizer`, `parser`,
   `attribute_ruler` y `lemmatizer`.
2. **Tokenizer y componentes entrenados:** el tokenizer francés divide caracteres
   en tokens mediante convenciones y excepciones; los componentes entrenados
   predicen anotaciones según el contexto. Tokenizar no equivale a entender la frase.
3. **Doc, Token y Span:** `Doc` contiene los tokens y anotaciones del texto analizado;
   `Token` representa un token con su posición (`idx`); `Span` es una secuencia
   contigua de tokens, como una oración de `doc.sents`.
4. **Lematización:** propone una forma base, por ejemplo `aperçut → apercevoir`.
   El lematizador francés utiliza el análisis y recursos del pipeline; no es una
   traducción ni un diccionario infalible.
5. **POS, morfología y dependencias:** POS clasifica un token (`VERB`, `NOUN`, etc.).
   Morfología contiene atributos como `Person=3`, `Number=Sing` o `Tense=Past`.
   Las dependencias describen vínculos con un núcleo, por ejemplo `nsubj` u `obj`.
   `ROOT` señala el núcleo de la oración, cuya cabeza es él mismo.
6. **Modelo elegido:** `sm` está optimizado para CPU y no incorpora los vectores
   estáticos de `md`/`lg` ni un transformer. Permite comenzar con menos recursos.
   Su entrenamiento es principalmente periodístico: una novela puede diferir.
7. **Offsets:** `Token.idx` es relativo a la ventana Python; el servicio suma el
   origen de esa ventana y convierte explícitamente a UTF-16 para el lector.
   La selección del DOM ya se verifica contra el contenido completo, no contra
   el texto visible de un párrafo. Emoji y caracteres combinados no se normalizan.
8. **Límites:** las predicciones pueden ser erróneas; el texto largo se acota y
   una oración truncada puede reducir su calidad. No se reconocen locuciones
   idiomáticas como unidades semánticas: `se rendit compte` sigue siendo varios
   tokens. No se infiere el tiempo global de una perífrasis a partir de un token.
9. **Ejemplo aislado**, después de instalar el entorno autorizado:

```console
cd backend
../.venv/bin/python - <<'PY'
import spacy
nlp = spacy.load("fr_core_news_sm", exclude=["ner"])
doc = nlp("Elle aperçut un homme.")
for token in doc:
    print(token.text, token.idx, token.lemma_, token.pos_, token.morph, token.dep_, token.head.text)
print([sentence.text for sentence in doc.sents])
PY
```

### Limitaciones observadas y pruebas

Con las versiones fijadas se han observado estos fallos, que **no corregimos con
reglas específicas ni ocultamos en la interfaz**:

| Ejemplo | Objetivo lingüístico | Predicción incorrecta |
| --- | --- | --- |
| `Elle aperçut un homme.` | `aperçut`: passé simple, `Tense=Past` | `Tense=Pres`; lema `apercevoir` y POS `VERB` sí correctos |
| `Je mange une pomme.` | `mange`: primera persona | `Person=3` |
| `Nous nous promenions dans la rue.` | `promenions`: imparfait, `Tense=Imp` | `Tense=Pres` |

Los tests de esos tres objetivos llevan `xfail(strict=True)` con una explicación.
Un cambio de modelo que los resuelva producirá XPASS y exigirá revisar el marcador.
El resto comprueba lemas/POS representativos, morfología disponible, texto y
posiciones exactas, Unicode, ventanas acotadas, anotaciones ausentes y aislamiento
entre usuarios. La API incluye las versiones del modelo y de spaCy para reproducir
un resultado. No se persisten los análisis.
