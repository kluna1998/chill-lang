# Chill-Lang — Desarrollo

La arquitectura y requisitos del MVP están en [README.md](README.md). Se mantiene
FastAPI/SQLModel/Alembic, React/Vite/Bun, spaCy y el SDK de OpenAI; esta limpieza no
modifica endpoints, modelos ni reglas de negocio.

## Stack habitual

Configura los archivos privados a partir de los ejemplos, sin sobrescribir archivos
existentes. Desde la raíz:

```bash
bash dev.sh
```

El script carga siempre `.env` y `.env.openai.local`, construye el backend (que
compila React), espera PostgreSQL, aplica Alembic, inicializa el administrador y
arranca `db`, `backend`, `proxy`, `adminer` y `mailpit`. Playwright queda fuera.

- `bash dev.sh --rebuild`: detiene y reconstruye sin borrar los volúmenes.
- `bash dev.sh --reset`: exige escribir `BORRAR` y elimina datos, volúmenes e imágenes locales.

Se conserva su comprobación final: exige IA habilitada y una clave no vacía, pero
no llama al proveedor. La aplicación permite leer y guardar vocabulario sin IA;
el criterio adicional del lanzador no se ha modificado.

## Arranque manual y ejecución sin IA

Para no utilizar IA, conserva `OPENAI_ENABLED=false` y arranca los servicios
explícitamente desde la raíz:

```bash
docker compose --env-file .env --env-file .env.openai.local up -d db mailpit
docker compose --env-file .env --env-file .env.openai.local build backend
docker compose --env-file .env --env-file .env.openai.local run --rm backend bash scripts/prestart.sh
docker compose --env-file .env --env-file .env.openai.local up -d backend proxy adminer mailpit
```

El arranque del servidor por sí solo no aplica migraciones. `prestart.sh` contiene
las migraciones y la inicialización que el lanzador también ejecuta explícitamente.

## Python y Vite fuera de Docker

No ejecutes simultáneamente el backend local y el de Compose en el puerto 8000.
Desde la raíz instala solo las versiones fijadas:

```bash
uv sync --frozen --package app
bun install --frozen-lockfile
docker compose up -d db mailpit
```

Desde `backend/`:

```bash
uv run --frozen bash scripts/prestart.sh
uv run --frozen fastapi dev
```

Desde `frontend/`, en otra terminal:

```bash
VITE_API_URL=http://localhost:8000 bun run dev
```

La aplicación de Vite está en <http://localhost:5173>; la API en
<http://localhost:8000/docs>. Para servir React con FastAPI, compila desde `frontend/`
con `VITE_API_URL= bun run build`. Esa variable se fija al compilar, no al arrancar
un bundle ya generado.

## Compose

- `compose.yml`: servicios compartidos y volumen persistente de PostgreSQL.
- `compose.override.yml`: desarrollo, puertos locales, Mailpit y sincronización con `watch`.
- `compose.deploy.yml`: HTTPS y reinicios para un servidor remoto.
- `.github/compose.ci.yml`: solo CI Linux; navegador en red host con URLs localhost (contexto seguro de WebCrypto), correo de pruebas e informes del navegador.

Compose carga los dos primeros archivos por defecto. El overlay de CI solo se
carga al indicarlo explícitamente; el lanzador no lo utiliza. No ejecutes comandos
de limpieza de volúmenes de la CI sobre tu proyecto de desarrollo.

## Calidad y pruebas

Consulta los comandos y la preparación de una base aislada en el
[README](README.md#verificación). La fixture de pytest elimina usuarios: tu base
habitual no es una base de pruebas. Los E2E también crean usuarios y modifican datos.

Se mantienen los hooks locales de `.pre-commit-config.yaml`, que pueden formatear
archivos. El workflow `pre-commit` de CI ejecuta comprobaciones de solo lectura:
no hace commits automáticos ni requiere aplicaciones de GitHub para publicar cambios.
El hook del generador SDK sigue pendiente de resolver su incompatibilidad con
TypeScript 7; no se ejecuta automáticamente en CI ni se han cambiado sus dependencias.

Las pruebas utilizan OpenAI simulado o desactivado. No deben necesitar tu clave ni
consumir facturación. Mailpit captura el correo de pruebas en <http://localhost:8025>.
