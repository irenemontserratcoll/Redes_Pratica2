#!/bin/bash
# Genera el ejecutable practica1_modbus en esta carpeta.
# Necesita PyInstaller:  python3 -m pip install pyinstaller
# (o indicar otro intérprete:  PYTHON=/ruta/a/python3 ./construir.sh)
set -e
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3}"
"$PYTHON" -m PyInstaller --onefile --clean --noconfirm \
    --name practica1_modbus \
    --paths "$(pwd)/../practica1" \
    --add-binary "$(pwd)/../simulador_modbus:." \
    --distpath . --workpath build --specpath build \
    lanzador.py
rm -rf build
echo "Listo: $(pwd)/practica1_modbus"
