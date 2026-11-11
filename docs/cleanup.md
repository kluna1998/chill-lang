# Limpieza controlada del template

Esta implementación corresponde a la Fase B aprobada tras la auditoría. No cambia
la lógica de libros, capítulos, NLP, IA, vocabulario, progreso, autenticación ni
permisos. No añade dependencias, cambia versiones de paquetes o regenera lockfiles.

## Workflows retirados

| Archivo en `.github/workflows/` | Función anterior | Motivo y consecuencia |
| --- | --- | --- |
| `add-to-project.yml` | Añadir asuntos al proyecto de la organización FastAPI | Era específico de la organización upstream; no afecta a Chill-Lang. |
| `bump-pre-commit-hooks.yml` | Crear PRs automáticas de actualización de hooks | Solo se ejecutaba para el propietario `fastapi` y dependía de PR Submit. Se conserva la actualización manual de herramientas existentes. |
| `create-draft-release.yml` | Crear borradores de release | Consumía el historial de versiones del template; no publica versiones de Chill-Lang. |
| `prepare-release.yml` | Editar el historial y abrir una PR de release | Se retira junto a los scripts e historial que utilizaba. |
| `issue-manager.yml` | Gestionar asuntos y PRs de FastAPI | Estaba condicionado al propietario `fastapi`. |
| `detect-conflicts.yml` | Etiquetar y comentar conflictos | Automatización accesoria retirada; no se alteran las reglas de merge de GitHub. |
| `guard-dependencies.yml` | Cerrar PRs de autores externos que modificaran ciertos manifiestos | Era una política de organización, no un análisis de vulnerabilidades. La aprobación de dependencias sigue en AGENTS.md. |
| `smokeshow.yml` | Publicar cobertura en un servicio externo | Se sustituye la publicación por el artefacto `coverage-html`; se mantiene el umbral del 90 %. |
| `deploy.yml` | Migrar y desplegar automáticamente a FastAPI Cloud | Se retira el destino aprobado; el despliegue Docker permanece. |

## Otros archivos retirados

| Archivo | Función anterior | Motivo y comprobación |
| --- | --- | --- |
| `hooks/post_gen_project.py` | Convertir finales de línea al generar un proyecto | No se encontró ninguna invocación en el proyecto actual. El lanzador no lo usa. |
| `scripts/prepare_release.py` | Preparar y extraer notas de versión | Solo lo consumían los workflows de release retirados. |
| `scripts/add_latest_release_date.py` | Añadir fecha a una release | Se retira también su hook en `.pre-commit-config.yaml`. |
| `release-notes.md` | Historial del template FastAPI | Describía versiones y PRs upstream, no el MVP. Se conserva LICENSE y la atribución al origen. |
| `.github/pr-push.yml` | Configurar la aplicación de autopush | La CI de calidad ya no publica commits en PRs. |
| `.github/pr-submit.yml` | Configurar creación automática de PRs | Solo quedaban consumidores en la cadena de releases y actualización de hooks retirada. |
| `.github/latest-changes.yml` | Etiquetas para notas de versión automáticas | Configuración del historial retirado. No se han desinstalado aplicaciones de GitHub remotamente. |
| `.fastapicloudignore` | Seleccionar archivos para FastAPI Cloud | Ya no hay despliegue a ese destino; Compose no lo utiliza. |
| `scripts/test.sh` | Construir el stack y ejecutar tests dentro del backend | Duplicaba las tareas de CI y eliminaba volúmenes. La imagen normal no copia los tests. Se conserva el script distinto `backend/scripts/test.sh`. |
| `scripts/test-local.sh` | Variante antigua con `docker-compose`, sudo y limpieza global de cachés | No tenía consumidores encontrados y no lo usa `dev.sh`. |
| `frontend/src/components/Pending/PendingItems.tsx` | Skeleton de la demostración Items | No tenía imports. Se conserva `PendingUsers.tsx`, utilizado por administración. |
| `frontend/src/components/Common/Footer.tsx` | Footer del template y redes de FastAPI | No tenía consumidores. No se retira el paquete de iconos en esta limpieza. |
| `frontend/src/hooks/useCopyToClipboard.ts` | Helper de portapapeles | No tenía consumidores encontrados en los componentes activos. |

Las siguientes imágenes de `img/` eran recursos de documentación heredada sin
referencias activas: `dashboard-items.png`, `github-social-preview.png`, `docs.png`,
`dashboard.png`, `react-email.png`, `dashboard-dark.png`, `login.png`, `mailpit.png`
y `github-social-preview.svg`. Se retira también la exclusión huérfana de `img/`
en la configuración de typos de `pyproject.toml`.

Se retiran cuatro SVG sin referencias en `frontend/public/assets/images/`:
`fastapi-logo.svg`, `fastapi-logo-light.svg`, `fastapi-icon.svg` y
`fastapi-icon-light.svg`. El favicon PNG referenciado por HTML se conserva.

## Archivos modificados o añadidos

| Archivo | Cambio y efecto |
| --- | --- |
| `.github/workflows/test-backend.yml` | Configuración pública de pruebas, instalación congelada, pytest/cobertura, artefacto y limpieza con `always()`. No depende de archivos privados. |
| `.github/workflows/pre-commit.yml` | Ruff, mypy, ty, Biome, TypeScript y build de solo lectura. Sin autopush, generación de SDK ni permisos de escritura. Conserva `pre-commit-alls-green`. |
| `.github/workflows/playwright.yml` | Un build de aplicación/navegador y un conjunto de tests, con health checks HTTP que fallan ante errores, artefactos y limpieza. Filtros incluyen manifiestos, locks y scripts. Conserva `alls-green-playwright` y comprueba también el resultado del filtro. |
| `.github/workflows/test-docker-compose.yml` | Valida los tres modos de configuración y sintaxis shell. El build y arranque real se concentran en Playwright. Conserva su nombre de check. |
| `.github/compose.ci.yml` | Overlay exclusivo de CI Linux: navegador en red host y URLs localhost para disponer del contexto seguro que necesita WebCrypto, IA apagada y volumen del informe HTML. No lo carga `dev.sh`. |
| `frontend/Dockerfile.playwright` | Alinea la imagen de navegador de 1.65.0 a 1.64.1, la versión ya fijada del paquete Playwright. No cambia el paquete ni el lockfile. |
| `.pre-commit-config.yaml` | Retira únicamente el hook de fecha de releases. Conserva los demás hooks locales, incluido el generador pendiente de revisión. |
| `pyproject.toml` | Retira únicamente la exclusión de imágenes eliminadas. Las dependencias permanecen. |
| `frontend/index.html` | Título Chill-Lang, idioma español y eliminación del enlace inexistente `/vite.svg`. Mantiene el favicon PNG activo. |
| `README.md` | Documenta el lanzador y CI actuales y corrige afirmaciones obsoletas sobre Items y `.env` versionado. |
| `development.md` | Describe los modos reales de `dev.sh`, el arranque manual sin IA y la separación entre Compose local, remoto y CI. |
| `backend/README.md` | Conserva los detalles del MVP y de React Email, elimina instrucciones para borrar migraciones y corrige los comandos y ubicación de tests. |
| `frontend/README.md` | Describe las rutas y flujo de lectura existentes. Retira las instrucciones para desmantelar el frontend y hace explícita la limitación del generador. |
| `CONTRIBUTING.md` | Sustituye políticas y enlaces de contribución de FastAPI por el flujo y requisitos de aprobación de Chill-Lang. |
| `deployment.md` | Sustituye las instrucciones de FastAPI Cloud por las referencias al despliegue Docker existente. |
| `deployment-docker-compose.md` | Actualiza ejemplos y nombre del proyecto, dejando explícito que el workflow remoto conservado requiere revisar su configuración real y las variables de IA. |
| `backend/app/api/routes/users.py` | Retira un import `delete` sin uso que ya fallaba Ruff tras una limpieza anterior. No cambia funciones ni endpoints. |
| `backend/app/crud.py` | Retira un import `uuid` sin uso que ya fallaba Ruff. No cambia funciones. |
| `backend/app/models.py` | Añade una línea en blanco exigida por Ruff. No cambia modelos ni esquema. |
| `frontend/tests/utils/random.ts` | Recupera desde Git los helpers de email y contraseña que aún importaban seis suites. Se conserva su implementación y no se reintroducen helpers de Items sin consumidores. |
| `frontend/src/routes/_layout/items.tsx` | Recupera la redirección a la biblioteca que seguía registrada en el árbol generado y comprobada por un E2E activo. No recupera el CRUD de demostración. |
| `frontend/tests/mvp-integration.spec.ts` | Espera la respuesta real de análisis y exige HTTP 200 antes de comprobar el lema. Evita confundir la carga inicial de spaCy con un fallo por superar cinco segundos de espera visual; conserva todas las aserciones y el timeout total. |
| `docs/cleanup.md` | Registro por archivo del alcance y límites de la limpieza aprobada. |

## Conservado y pendiente de revisar

- `dev.sh` conserva exactamente el contenido local existente al iniciar esta tarea,
  incluidos servicios, orden de migración/inicialización y comprobación de OpenAI.
- Se conservan todos los tests activos y las migraciones históricas, endpoints,
  servicios de negocio, modelos y persistencia. Los tres cambios Python indicados
  arriba son exclusivamente imports sin uso y formato.
- Se conservan `compose.yml`, `compose.override.yml` y `compose.deploy.yml`.
- Se conserva `.github/workflows/deploy-docker-compose.yml`: no se han verificado
  ni modificado runners, secretos, permisos o servidores remotos.
- Se conservan Zizmor y Dependabot. No se presume que las aplicaciones o ajustes
  remotos de seguridad y protección de ramas estén configurados: debe comprobarlo
  el administrador del repositorio.
- Se conservan React Email y los HTML usados en recuperación de contraseña, alta
  de cuentas y correo de pruebas.
- El generador OpenAPI, TypeScript y los manifiestos/lockfiles siguen en revisión.
  El cliente versionado se usa en CI; no se presenta como resuelta la incompatibilidad.
- Las dependencias exclusivas de herramientas retiradas permanecen para una
  revisión separada. No se modifica ningún secreto ni archivo `.env` privado.

## Validación reproducible

Los comandos están en los README y en los workflows. Se deben usar datos de
pruebas, nunca los volúmenes de desarrollo. La CI configura credenciales de prueba
válidas y OpenAI apagado; no necesita la clave del usuario.

La comprobación de `dev.sh` combina sintaxis y simulación en un directorio temporal
con Docker/chmod sustituidos, para verificar modos, cancelación y orden de comandos
sin tocar los archivos privados ni iniciar o eliminar el stack real. No equivale
a ejecutar un despliegue sobre el entorno personal.

## Resultados de la validación local

- Backend sobre una base temporal con todas las migraciones: **303 passed,
  3 xfailed**, cobertura **92 %**; supera el umbral conservado del 90 %.
- Ruff (lint y formato), mypy y ty: correctos. Biome sobre `src tests`, TypeScript
  completo y build del frontend: correctos. Biome informa de una diferencia previa
  entre la versión del esquema de configuración y la herramienta; no impide los checks.
- Se construyeron las imágenes Docker de aplicación y Playwright. La versión del
  navegador coincide con el paquete 1.64.1 ya fijado.
- Configuración Compose local, CI y despliegue: válida. Sintaxis shell, enlaces
  locales de los ocho documentos y referencias a componentes retirados: correctos.
- Zizmor offline: sin hallazgos nuevos (16 supresiones existentes).
- `dev.sh`: siete casos simulados correctos; hash original conservado. Manifiestos,
  lockfiles, migraciones y workflow remoto protegidos sin cambios.

La primera ejecución del backend heredaba credenciales locales que no cumplían la
validación; se repitió con credenciales públicas válidas de CI, sin editar `.env`.
La primera ejecución Docker de E2E detectó la falta de contexto seguro WebCrypto
al usar un hostname interno HTTP y la ausencia de la redirección `/items` que
comprobaba un test activo. Se corrigieron el entorno de CI y el archivo perdido,
sin cambiar la lógica de progreso ni eliminar o reducir aserciones.

Las ejecuciones de Biome deben apuntar a `src tests`, como hace CI; una ejecución
sobre todo el directorio también encuentra artefactos locales generados
(`openapi.json` y almacenamiento de autenticación), ajenos al código versionado.
La regeneración del árbol de rutas se realizó con Vite al recuperar la ruta; el
árbol resultante coincide con el que ya estaba versionado.

No se ha ejecutado GitHub Actions remotamente ni un despliegue en el servidor.
Las comprobaciones de Compose y la simulación del lanzador no equivalen a probar
el despliegue del usuario. Los cambios locales preexistentes de `dev.sh` y los
cambios concurrentes de `.env.example` se han respetado.

La ejecución completa con localhost detectó además un caso inestable en el primer
análisis real: spaCy seguía cargándose cuando vencía la espera visual de cinco
segundos. El reintento pasaba. La prueba de integración espera ahora la respuesta
del endpoint, exige HTTP 200 y mantiene la aserción del lema y el timeout total.
No se ha calentado artificialmente el servicio ni sustituido spaCy por un mock.

La repetición final, con base nueva y backend frío, terminó con **101 E2E passed
(2,4 minutos)**, sin fallos ni reintentos y con `--fail-on-flaky-tests` activo.
Incluye importación, spaCy real, vocabulario y progreso; solo la generación IA se
simula. El stack temporal y su volumen se eliminaron al terminar. Informes locales:
`/tmp/chill-cleanup-compose-uy1xcq9n/html/index.html`; registro:
`/tmp/chill-cleanup-e2e-final.log`.
