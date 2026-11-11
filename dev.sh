
#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")"

MODE="${1:-start}"

if [[ $# -gt 1 ]]; then
  echo "Uso: ./dev.sh [--rebuild|--reset]"
  exit 1
fi

case "$MODE" in
  start|--rebuild|--reset) ;;
  *)
    echo "Uso: ./dev.sh [--rebuild|--reset]"
    exit 1
    ;;
esac

# Verificaciones iniciales
command -v docker >/dev/null || {
  echo "ERROR: Docker no está instalado."
  exit 1
}

docker info >/dev/null 2>&1 || {
  echo "ERROR: Docker no está funcionando."
  exit 1
}

for file in .env .env.openai.local; do
  if [[ ! -f "$file" ]]; then
    echo "ERROR: Falta el archivo $file"
    exit 1
  fi
done

# Evitar que otros usuarios puedan leer las credenciales
chmod 600 .env.openai.local

# Función que utiliza siempre ambos archivos de configuración
dc() {
  docker compose \
    --env-file .env \
    --env-file .env.openai.local \
    "$@"
}

# Servicios necesarios para utilizar Chill-Lang
# Playwright queda excluido del arranque habitual.
SERVICES=(db backend proxy adminer mailpit)

if [[ "$MODE" == "--reset" ]]; then
  echo
  echo "ATENCIÓN: Se eliminará la base de datos local."
  echo "Perderás usuarios, libros, vocabulario y progreso."
  read -r -p "Escribe BORRAR para continuar: " confirmation

  if [[ "$confirmation" != "BORRAR" ]]; then
    echo "Operación cancelada."
    exit 0
  fi

  echo "Eliminando contenedores y volúmenes..."
  dc down --volumes --remove-orphans --rmi local
fi

if [[ "$MODE" == "--rebuild" ]]; then
  echo "Deteniendo contenedores anteriores..."
  dc down --remove-orphans
fi

# Reconstruir únicamente la imagen necesaria.
# El Dockerfile del backend también compila React.
if [[ "$MODE" == "--rebuild" || "$MODE" == "--reset" ]]; then
  echo "Reconstruyendo sin caché..."
  dc build --no-cache --pull backend
else
  echo "Construyendo cambios si es necesario..."
  dc build backend
fi

echo "Iniciando PostgreSQL..."
dc up -d --wait db

echo "Aplicando migraciones..."
dc run --rm --no-deps backend alembic upgrade head

echo "Inicializando administrador..."
dc run --rm --no-deps backend python app/initial_data.py

echo "Arrancando Chill-Lang..."
dc up -d --no-build --wait "${SERVICES[@]}"

echo "Comprobando configuración de OpenAI..."
dc exec -T backend python -c '
from app.core.config import settings

key_present = bool(
    settings.OPENAI_API_KEY
    and settings.OPENAI_API_KEY.get_secret_value().strip()
)

print("OpenAI habilitado:", settings.OPENAI_ENABLED)
print("API key configurada:", key_present)
print("Modelo:", settings.OPENAI_MODEL)

if not settings.OPENAI_ENABLED or not key_present:
    raise SystemExit("ERROR: OpenAI no está configurado correctamente")
'

echo
echo "======================================"
echo " Chill-Lang iniciado correctamente"
echo "======================================"
echo "Aplicación: http://localhost"
echo "API:        http://localhost:8000/docs"
echo "Adminer:    http://localhost:8080"
echo "Mailpit:    http://localhost:8025"
echo
echo "Estado de contenedores:"
dc ps
