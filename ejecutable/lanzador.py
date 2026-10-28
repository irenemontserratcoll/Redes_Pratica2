"""Ejecutable de la práctica 1 de Modbus TCP.

Al arrancar:
  1. Abre el simulador del laboratorio (servidor Modbus en el puerto 5020 e
     interfaz en el navegador), salvo que ya estuviera abierto.
  2. Muestra una consola en la que se escriben órdenes de modbus_cli.py
     (por ejemplo: leer-holding 1 3) y se ve su salida y su código de salida.
  3. Al salir, cierra el simulador si lo abrió él.

Se convierte en un único ejecutable con construir.sh (PyInstaller), que
mete dentro modbus_tcp.py, modbus_cli.py y el simulador.
"""

import os
import shlex
import socket
import subprocess
import sys
import tempfile
import time

# En desarrollo, modbus_cli y modbus_tcp están en ../practica1
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "practica1"))
import modbus_cli  # noqa: E402
import modbus_tcp  # noqa: E402

IP = "127.0.0.1"
PUERTO = 5020

AYUDA = f"""
Órdenes (se envían al simulador en {IP}:{PUERTO}):
  leer-coils DIR CANT          leer-entradas DIR CANT
  leer-holding DIR CANT        leer-input DIR CANT
  escribir-coil DIR 1|0        escribir-registro DIR VALOR
  escribir-coils DIR V...      escribir-registros DIR V...
  leer-escribir DIR_LECT CANT DIR_ESCR V...

Opciones (antes de la orden): --traza  --unidad U  --timeout S  --puerto P  --ip IP
  Ejemplo: --traza leer-holding 1 3

Otras:
  demo     ejecuta una demostración de todas las funciones y errores
  ayuda    muestra esta ayuda
  salir    cierra el programa (y el simulador, si lo abrió este programa)
"""


# --- simulador -----------------------------------------------------------

def ruta_simulador():
    """El simulador va dentro del ejecutable; en desarrollo, en ../"""
    if getattr(sys, "frozen", False):  # dentro del ejecutable de PyInstaller
        return os.path.join(sys._MEIPASS, "simulador_modbus")
    return os.path.join(AQUI, "..", "simulador_modbus")


def puerto_abierto():
    try:
        socket.create_connection((IP, PUERTO), timeout=0.5).close()
        return True
    except OSError:
        return False


def abrir_simulador():
    """Arranca el simulador y espera a que escuche. Devuelve el proceso, o
    None si ya había un simulador abierto."""
    if puerto_abierto():
        print(f"El simulador ya estaba abierto en el puerto {PUERTO}: "
              f"se usa ese.")
        return None

    ruta = ruta_simulador()
    os.chmod(ruta, 0o755)
    registro = tempfile.NamedTemporaryFile("w", prefix="simulador_",
                                           suffix=".log", delete=False)
    print("Abriendo el simulador (se abre también en el navegador)...")
    proceso = subprocess.Popen([ruta, "--puerto-modbus", str(PUERTO)],
                               stdout=registro, stderr=subprocess.STDOUT,
                               start_new_session=True)

    for _ in range(75):  # hasta 15 s
        if puerto_abierto():
            print(f"Simulador listo en {IP}:{PUERTO}. "
                  f"Interfaz: http://127.0.0.1:8080")
            return proceso
        if proceso.poll() is not None:  # el simulador ha terminado
            break
        time.sleep(0.2)

    print("No se ha podido arrancar el simulador. Esto es lo que ha dicho:")
    registro.close()
    with open(registro.name) as f:
        print(f.read())
    cerrar_simulador(proceso)
    sys.exit(1)


def cerrar_simulador(proceso):
    if proceso is not None and proceso.poll() is None:
        proceso.terminate()
        try:
            proceso.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proceso.kill()


# --- órdenes -------------------------------------------------------------

def ejecutar_orden(argumentos):
    """Ejecuta una orden de modbus_cli.py y devuelve su código de salida."""
    if "--puerto" not in argumentos:
        argumentos = ["--puerto", str(PUERTO)] + argumentos
    sys.argv = ["modbus_cli.py"] + argumentos
    try:
        modbus_cli.main()
        return 0
    except SystemExit as e:  # modbus_cli termina con sys.exit(codigo)
        return e.code if isinstance(e.code, int) else 0


DEMO = [
    ("Apartado 6 - FC05: encender la coil 172", "escribir-coil 172 on"),
    ("Apartado 3 - FC01: leer la coil 172", "leer-coils 172 1"),
    ("Apartado 9 - FC0F: escribir 10 coils desde la 19 (guion)",
     "--traza escribir-coils 19 1 0 1 1 0 0 1 1 1 0"),
    ("Apartado 3 - FC01: leerlas", "leer-coils 19 10"),
    ("Apartado 5 - FC06: escribir -5 en el registro 2",
     "--traza escribir-registro 2 -5"),
    ("Apartado 8 - FC10: escribir 10, 258 y -5 en los registros 1..3",
     "--traza escribir-registros 1 10 258 -5"),
    ("Apartado 1 - FC03: leerlos", "--traza leer-holding 1 3"),
    ("Apartado 8 - preparar los registros 3..8 del ejemplo de la FC17",
     "escribir-registros 3 0xFE 0xACD 1 3 0xD 0xFF"),
    ("Apartado 10 - FC17: leer 6 desde el 3 y escribir 0xFF en 14..16 (guion)",
     "--traza leer-escribir 3 6 14 0xFF 0xFF 0xFF"),
    ("Apartado 2 - FC04: leer el input register 8", "leer-input 8 1"),
    ("Apartado 4 - FC02: leer las entradas discretas 0..4",
     "leer-entradas 0 5"),
    ("Apartado 7 - ExcepcionModbus: leer fuera de la tabla",
     "--traza leer-holding 9999 2"),
    ("Apartado 7 - el cliente sigue funcionando tras la excepcion",
     "leer-holding 1 1"),
    ("Apartado 11 - argumento fuera de rango", "leer-holding 0 126"),
    ("Apartado 7 - ErrorConexion: puerto donde no escucha nadie",
     "--puerto 5999 leer-coils 0 1"),
]


def demo():
    for i, (titulo, orden) in enumerate(DEMO, 1):
        print(f"\n[{i}/{len(DEMO)}] {titulo}")
        print(f"modbus> {orden}")
        codigo = ejecutar_orden(shlex.split(orden))
        print(f"[codigo de salida {codigo}]")
    print("\nFalta el TIMEOUT (codigo 4): en el simulador, Comportamiento > "
          "atender solo al\nUnit ID 1 con la politica Descartar, Aplicar, y "
          "ejecutar: leer-coils 0 1")


def consola():
    print(AYUDA)
    while True:
        try:
            linea = input("modbus> ").strip()
        except (EOFError, KeyboardInterrupt):  # Ctrl+D o Ctrl+C
            print()
            return
        if not linea:
            continue
        if linea in ("salir", "exit", "quit"):
            return
        if linea in ("ayuda", "help", "?"):
            print(AYUDA)
            continue
        if linea == "demo":
            demo()
            continue
        try:
            argumentos = shlex.split(linea)
        except ValueError as e:
            print(f"ARGUMENTO INVALIDO: {e}")
            continue
        codigo = ejecutar_orden(argumentos)
        print(f"[codigo de salida {codigo}]")


def main():
    print("Practica 1 de Modbus TCP - cliente escrito a mano")
    print(f"Autora: {modbus_tcp.AUTOR}")
    simulador = abrir_simulador()
    try:
        consola()
    finally:
        if simulador is not None:
            print("Cerrando el simulador...")
        cerrar_simulador(simulador)


if __name__ == "__main__":
    main()
