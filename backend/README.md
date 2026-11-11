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
