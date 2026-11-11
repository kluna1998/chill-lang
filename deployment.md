# Chill-Lang — Despliegue

El despliegue del MVP utiliza Docker Compose. Para el entorno local, el lanzador
existente es `bash dev.sh`; su configuración y comportamiento se mantienen.
Consulta [development.md](development.md) para sus modos y el arranque sin IA.

Para un servidor remoto existe [deployment-docker-compose.md](deployment-docker-compose.md)
y el overlay `compose.deploy.yml`. El workflow manual
`.github/workflows/deploy-docker-compose.yml` se conserva en revisión: requiere
confirmar runner, variables y secretos reales antes de utilizarlo.

Se retiran las instrucciones y automatizaciones de FastAPI Cloud heredadas de la
plantilla. La limpieza no migra servidores, cambia endpoints ni ejecuta despliegues.

La CI se describe en [README.md](README.md#ci-del-mvp). No es un despliegue:
utiliza configuración pública de pruebas, datos desechables y OpenAI desactivado.
Los detalles de esta limpieza están en [docs/cleanup.md](docs/cleanup.md).
