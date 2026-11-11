# Chill-Lang — Frontend

React y TypeScript con Vite, TanStack Router, React Query, Tailwind y componentes
shadcn/ui. Se conservan autenticación, cuenta, administración, biblioteca, lector,
vocabulario y progreso; no hay navegación de demostración de Items.

## Desarrollo

Requisitos: Bun 1, Node compatible con Vite 8 y un backend preparado. Desde la raíz:

```bash
bun install --frozen-lockfile
```

Desde `frontend/`:

```bash
VITE_API_URL=http://localhost:8000 bun run dev
```

Abre <http://localhost:5173>. Para el despliegue habitual con Docker y el frontend
servido por FastAPI utiliza `bash dev.sh`; consulta [desarrollo](../development.md).

## Build y calidad

Desde `frontend/`:

```bash
VITE_API_URL= bun run build
bunx --no-install tsc --noEmit -p tsconfig.json
bunx --no-install biome check src tests
```

El build se escribe en `backend/app/frontend/`. Con `VITE_API_URL` vacío usa la API
del mismo origen; cambiar variables del servidor no cambia la URL de un bundle ya
compilado. El build comprueba la aplicación; el comando de TypeScript adicional
incluye también las pruebas.

## Cliente API

`src/client/` se genera desde OpenAPI y permanece versionado. Se conserva
`scripts/generate-client.sh`, pero el generador instalado utiliza una API de
compilador que TypeScript 7 no exporta. Su compatibilidad está pendiente de revisión;
esta limpieza no instala otra versión ni regenera el SDK en CI.

Los cambios futuros del contrato deben actualizar el cliente con una combinación
compatible y autorizada. No crees otro cliente HTTP ni edites los archivos generados
como solución permanente. Conservamos la autenticación, errores y caché existentes.

## E2E

Utiliza Chromium de Playwright, backend de pruebas, base desechable y Mailpit.
Desde `frontend/`, con credenciales de administrador de esa instancia:

```bash
PLAYWRIGHT_BASE_URL=http://localhost:8000 \
VITE_API_URL=http://localhost:8000 \
MAILPIT_HOST=http://localhost:8025 \
bun run test --workers=1
```

No ejecutes estas pruebas contra tu biblioteca habitual. Se conservan todos los
tests activos. Los casos de carga, errores y respuestas obsoletas usan APIs
simuladas; el recorrido de `mvp-integration.spec.ts` usa API, PostgreSQL y spaCy
reales y simula únicamente la explicación de IA.

La imagen `Dockerfile.playwright` se alinea con la versión `1.64.1` de
`@playwright/test` del lockfile. CI ejecuta un solo conjunto de navegador y guarda
HTML y trazas como artefactos. No instala ni llama a un modelo de IA remoto.

## Organización

- `src/routes/`: biblioteca, libro, lectura, vocabulario, cuenta y autenticación.
- `src/components/Books/`, `Chapters/`, `Reader/`: importación y lectura.
- `src/hooks/`: consultas, mutaciones, autenticación y progreso.
- `src/client/`: cliente generado; `src/components/ui/`: controles compartidos.
- `tests/`: pruebas de interfaz e integración.

Las fuentes de correo en `packages/react-email/` se conservan porque generan los
HTML que el backend utiliza para recuperar contraseñas y crear cuentas.
