# Chill-Lang

Chill-Lang es un MVP para leer libros en francés con ayuda contextual en español.
Cada usuario tiene una biblioteca privada, vocabulario personal y progreso de lectura.

## Funcionalidades

- Registro, inicio/cierre de sesión, cuenta personal y administración de usuarios.
- Importación de libros TXT y EPUB a metadatos y capítulos de texto plano.
- Índice de capítulos, navegación anterior/siguiente y preferencias de lectura.
- Selección de palabras o expresiones conservando texto, contexto y offsets UTF-16.
- Análisis de lemas, categorías y morfología con spaCy y `fr_core_news_sm`.
- Traducción contextual con OpenAI, solicitada expresamente por el lector.
  Las explicaciones son opcionales y se muestran cuando aportan valor pedagógico.
- Guardado de vocabulario reutilizando la traducción ya obtenida, sin otra llamada
  a la IA; listado paginado y eliminación de entradas propias.
- Progreso por usuario y libro, recuperación de posición y «Continuar leyendo».
  Utiliza offsets del texto, debounce, huella del contenido y control de versiones.

La importación no conserva el archivo original ni reproduce la maquetación de EPUB.
No incluye OCR, PDF, flashcards, SRS, gamificación, diccionarios ni orquestadores.
El backend de demostración de Items permanece por compatibilidad, fuera de la interfaz.

## Arquitectura y requisitos

Monolito modular: FastAPI, SQLModel, Pydantic, PostgreSQL y Alembic en el backend;
React, TypeScript, TanStack Router y React Query en el frontend. El cliente API se
obtiene de OpenAPI. La lógica de importación, NLP, IA y persistencia está en
`backend/app/services/`. El MVP utiliza el SDK oficial de OpenAI directamente;
DSPy está pospuesto.

Para Docker necesitas Docker Engine y Compose v2. La imagen construye también el
frontend, que FastAPI sirve en el mismo origen que la API.

Para desarrollar y ejecutar las pruebas fuera de Docker necesitas Python 3.14,
`uv`, Bun 1 y Node.js compatible con Vite 8 (22.12 o posterior). Para los E2E
necesitas además Chromium de Playwright y sus bibliotecas del sistema. Las versiones
Python y JavaScript están fijadas en `uv.lock` y `bun.lock`.

## Configuración inicial

En un clon nuevo, desde la raíz:

```bash
cp .env.example .env
cp .env.openai.local.example .env.openai.local
```

Si esos archivos ya existen, edítalos sin sobrescribirlos. Configura en `.env`
`PROJECT_NAME`, `SECRET_KEY`, `FIRST_SUPERUSER`, `FIRST_SUPERUSER_PASSWORD`,
`POSTGRES_PASSWORD` y `DATABASE_URL`. Utiliza secretos propios en lugar de
`changethis`. En desarrollo local, PostgreSQL se publica en `localhost:5432` y
Mailpit en los puertos SMTP 1025 y web 8025.

Reserva `.env.openai.local`, ignorado por Git, para la clave de OpenAI. El `.env`
histórico del proyecto sigue versionado: no guardes allí esa clave ni la expongas
mediante variables `VITE_`. Los archivos de ejemplo no contienen credenciales reales.

### Ejecutar con Docker Compose

Desde la raíz, después de configurar los archivos:

```bash
docker compose --env-file .env --env-file .env.openai.local up -d db mailpit
docker compose --env-file .env --env-file .env.openai.local build backend
docker compose --env-file .env --env-file .env.openai.local run --rm backend bash scripts/prestart.sh
docker compose --env-file .env --env-file .env.openai.local up -d backend
```

`prestart.sh` aplica Alembic y crea el administrador inicial si no existe. El
arranque habitual del backend no ejecuta ese script automáticamente.

- Aplicación y API: <http://localhost:8000>
- Documentación interactiva: <http://localhost:8000/docs>
- Mailpit: <http://localhost:8025>

Después de cambiar código que se copia a la imagen, reconstruye el backend. Para
comprobar y aplicar nuevas migraciones:

```bash
docker compose exec backend alembic heads
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current
```

No es necesario eliminar volúmenes para actualizar el esquema.

### Desarrollo local con recarga

Desde la raíz:

```bash
uv sync --frozen --package app
bun install --frozen-lockfile
docker compose up -d db mailpit
cd backend
uv run --frozen bash scripts/prestart.sh
uv run --frozen fastapi dev --host 127.0.0.1
```

En otra terminal:

```bash
cd frontend
VITE_API_URL=http://localhost:8000 bun run dev
```

Abre <http://localhost:5173>. Ejecuta los comandos del backend desde `backend/`,
porque la configuración carga `../.env` y después `../.env.openai.local`. Las
variables del proceso tienen prioridad sobre ambos archivos.

## Importar y leer

El TXT debe estar codificado en UTF-8 y seguir este formato (máximo 5 MiB):

```text
TITLE: Une aventure
AUTHOR: Une autrice

=== CHAPTER: Le départ ===
Après un repos, on est remontés à cheval.

=== CHAPTER: La rencontre ===
La maison était grande.
```

`AUTHOR` es opcional. Los EPUB tienen un límite de 20 MiB y controles de tamaño
expandido, rutas y entidades XML. Se extraen capítulos siguiendo el spine; las
portadas y la navegación no se convierten en capítulos de lectura. Un error de
persistencia revierte el libro y todos sus capítulos.

En el lector, selecciona texto para analizarlo o solicitar su traducción. Después
de obtenerla puedes pulsar «Guardar palabra». El contexto se verifica contra el
capítulo persistido y los dobles clics no crean entradas duplicadas para el mismo
rango. Eliminar un libro, capítulo o cuenta elimina por cascada sus datos asociados.

## Activar OpenAI de forma deliberada

La IA está desactivada por defecto; importar, leer y analizar con spaCy no requieren
una clave. Cuando tengas configuradas la clave y la facturación de API, establece
en `.env.openai.local`:

```dotenv
OPENAI_API_KEY=tu-clave-de-proyecto
OPENAI_MODEL=gpt-5.4-mini
OPENAI_ENABLED=true
OPENAI_TIMEOUT_SECONDS=20
OPENAI_MAX_OUTPUT_TOKENS=600
OPENAI_REQUESTS_PER_MINUTE=6
```

Reinicia el backend; con Compose utiliza ambos `--env-file` al recrearlo. El backend
comprueba el acceso al modelo antes de la primera generación de cada worker y
valida la respuesta con Pydantic. No sustituye silenciosamente un modelo sin acceso.
Hay un único intento por petición, contexto limitado y control de frecuencia por
usuario y worker. Estos controles no equivalen a un presupuesto monetario global;
configura también los límites del proyecto en el proveedor.

Las pruebas automatizadas simulan OpenAI: no acreditan acceso de una cuenta,
facturación ni calidad pedagógica real. Las predicciones de spaCy y las respuestas
de IA pueden contener errores.

## Verificación

### Backend

**Utiliza una base exclusiva de pruebas.** La limpieza de `tests/conftest.py`
elimina usuarios; no ejecutes la suite contra tu biblioteca de desarrollo.
Ejemplo con el PostgreSQL de Compose, desde la raíz:

```bash
docker compose exec db createdb -U postgres chill_lang_test
cd backend
export DATABASE_URL='postgresql://postgres:TU_PASSWORD@localhost:5432/chill_lang_test'
export OPENAI_ENABLED=false
uv run --frozen alembic upgrade head
uv run --frozen pytest tests -q
uv run --frozen mypy app
uv run --frozen ty check app
uv run --frozen ruff check app tests
uv run --frozen ruff format app tests --check
```

Sustituye `TU_PASSWORD` por la contraseña configurada. Al terminar, cierra esa
terminal o elimina la variable `DATABASE_URL` antes de volver a usar tu base habitual.
Puedes borrar la base de pruebas desde la raíz:

```bash
docker compose exec db dropdb -U postgres chill_lang_test
```

Las pruebas de rollback interceptan la sesión real de la petición y comprueban
que un fallo de commit o una restricción de PostgreSQL no dejan datos parciales.
La suite también conserva casos `xfail` de limitaciones conocidas del modelo NLP;
no se consideran pruebas de exactitud lingüística superadas.

### Frontend y E2E

Desde `frontend/`:

```bash
VITE_API_URL= bun run build
bunx tsc --noEmit -p tsconfig.json
bunx biome check src tests
```

La compilación anterior usa API relativa al mismo origen. `VITE_API_URL` se fija
al compilar: cambiar solo las variables de Playwright no cambia un bundle ya
generado. Para Vite en desarrollo usa la URL explícita indicada más arriba.

Con una instancia de pruebas del backend ya migrada, su frontend compilado, un
administrador inicial y Mailpit disponibles, ejecuta:

```bash
PLAYWRIGHT_BASE_URL=http://localhost:8000 \
VITE_API_URL=http://localhost:8000 \
MAILPIT_HOST=http://localhost:8025 \
bun run test --workers=1
```

Esa instancia debe apuntar también a una base de pruebas y tener OpenAI desactivado.
Los E2E crean usuarios y cambian datos. Las credenciales `FIRST_SUPERUSER` y
`FIRST_SUPERUSER_PASSWORD` deben coincidir con las de esa instancia. Los helpers de
creación de usuarios requieren `FASTAPI_ENV=development`.

Hay pruebas de interfaz con APIs simuladas para carga, errores, permisos y
respuestas tardías. `mvp-integration.spec.ts` utiliza API, PostgreSQL y spaCy reales;
solo intercepta la explicación de IA. Las pruebas de rangos DOM cargan el mismo
`selection.ts` transpilado por Vite mediante una ruta interceptada exclusivamente
en el test, conservando sus aserciones también con el frontend compilado.
La prueba backend de integración recorre
TXT y EPUB y simula únicamente el proveedor OpenAI.

Más detalles: [backend](backend/README.md), [frontend](frontend/README.md) y
[desarrollo](development.md).

Basado en Full Stack FastAPI Template. Licencia MIT; consulta [LICENSE](LICENSE).
