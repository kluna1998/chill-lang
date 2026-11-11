# Contribuir a Chill-Lang

Lee [AGENTS.md](AGENTS.md) antes de modificar el proyecto. Conserva el monolito
modular y reutiliza los servicios, controles y cliente API existentes.

Las dependencias, cambios importantes de comportamiento y nuevas herramientas
requieren aprobación previa del propietario. Esta regla no se implementa cerrando
PRs automáticamente por pertenencia a la organización de una plantilla.

## Cambios

1. Describe el problema y el resultado esperado antes de introducir una solución.
2. Mantén cada cambio acotado y conserva autenticación, permisos y contratos.
3. Añade pruebas relevantes sin debilitar las existentes.
4. Usa Alembic para cambios de esquema; no borres revisiones históricas.
5. Explica qué cambió, por qué y cómo lo verificaste.

Consulta [development.md](development.md) y los README de
[backend](backend/README.md) y [frontend](frontend/README.md). Las pruebas se ejecutan
sobre datos desechables, con IA simulada o desactivada. No subas archivos privados
`.env`, claves, informes con datos reales ni documentos personales.

## Antes de entregar

Ejecuta pytest, calidad y tipos de Python, tipos y build de React y los E2E
correspondientes. Declara los comandos realmente ejecutados y las limitaciones del
entorno. La CI comprueba cambios; no hace commits automáticos sobre una PR.

La regeneración del SDK conserva una incompatibilidad conocida con TypeScript 7:
no cambies versiones ni el contrato generado silenciosamente para resolverla.
