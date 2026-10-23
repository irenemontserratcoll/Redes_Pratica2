"""Pruebas de la biblioteca modbus_tcp, apartado por apartado.

Cada apartado se comprueba de dos formas:
  1. Sin red: la PDU generada y la respuesta procesada deben coincidir con
     las tramas de ejemplo del guion.
  2. Contra el simulador (127.0.0.1:5020): se ejecuta la función de verdad.

Uso (desde la carpeta Irene_Redes, con el simulador arrancado):
    python3 pruebas.py            todos los apartados, con pausa entre ellos
    python3 pruebas.py 3          solo el apartado 3
    python3 pruebas.py 1 2 5      los apartados 1, 2 y 5
    python3 pruebas.py -s         todos, sin pausas

Ojo: las pruebas de escritura cambian la memoria del simulador
(holding registers 1, 2, 3, 10 y 11, y la coil 172).
"""

import os
import socket
import sys

# modbus_tcp.py está en la carpeta practica1
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "practica1"))
from modbus_tcp import (  # noqa: E402
    CabeceraMBAP, ClienteModbusTCP, EscribirCoil, EscribirRegistro,
    ErrorConexion, ErrorModbus, ErrorTimeout, ExcepcionModbus, LeerCoils,
    LeerEntradasDiscretas, LeerHoldingRegisters, LeerInputRegisters)

IP = "127.0.0.1"
PUERTO = 5020

fallos = 0
hay_simulador = True  # se comprueba al empezar, en main()


class SinSimulador(Exception):
    """Se lanza para saltar la parte de una prueba que necesita simulador."""


def comprobar(descripcion, obtenido, esperado):
    """Imprime OK o FALLO según si obtenido == esperado."""
    global fallos
    if obtenido == esperado:
        print(f"  [OK]    {descripcion}: {obtenido}")
    else:
        fallos += 1
        print(f"  [FALLO] {descripcion}: se obtuvo {obtenido}, "
              f"se esperaba {esperado}")


def hexa(datos):
    return datos.hex(" ").upper()


def titulo(texto):
    print("\n" + "=" * 70)
    print(texto)
    print("=" * 70)


def nuevo_cliente():
    if not hay_simulador:
        raise SinSimulador
    return ClienteModbusTCP(IP, PUERTO, traza=True)


# ---------------------------------------------------------------------------

def apartado_1():
    titulo("Apartado 1 - Cabecera MBAP y FC03 Read Holding Registers")
    print("Sin red (ejemplo del guion, pagina 4):")
    p = LeerHoldingRegisters(107, 3)
    comprobar("PDU", hexa(p.pdu()), "03 00 6B 00 03")
    comprobar("Cabecera MBAP", hexa(CabeceraMBAP(3, 6, 1).empaquetar()),
              "00 03 00 00 00 06 01")
    comprobar("Respuesta procesada",
              p.procesar(bytes.fromhex("06 02 2B 00 00 00 64")), [555, 0, 100])

    print("Contra el simulador (escribe 555, 0, 100 en los registros 1..3 "
          "con la 06 y los lee con la 03):")
    with nuevo_cliente() as c:
        for i, v in enumerate([555, 0, 100]):
            c.escribir_registro(1 + i, v)
        comprobar("leer_holding_registers(1, 3)",
                  c.leer_holding_registers(1, 3), [555, 0, 100])


def apartado_2():
    titulo("Apartado 2 - FC04 Read Input Registers")
    print("Sin red (ejemplo del guion, pagina 4):")
    p = LeerInputRegisters(8, 1)
    comprobar("PDU", hexa(p.pdu()), "04 00 08 00 01")
    comprobar("Respuesta procesada", p.procesar(bytes.fromhex("02 00 0A")),
              [10])

    print("Contra el simulador (los input registers no se pueden escribir "
          "desde el cliente:\n  compara con la pestana Servidor y memoria):")
    with nuevo_cliente() as c:
        valores = c.leer_input_registers(8, 1)
        print(f"  input register 8 = {valores[0]}")


def apartado_3():
    titulo("Apartado 3 - FC01 Read Coils")
    print("Sin red (ejemplo del guion, paginas 3 y 4):")
    p = LeerCoils(20, 10)
    comprobar("PDU", hexa(p.pdu()), "01 00 14 00 0A")
    comprobar("Respuesta procesada", p.procesar(bytes.fromhex("02 4D 03")),
              [1, 0, 1, 1, 0, 0, 1, 0, 1, 1])

    print("Contra el simulador (enciende la coil 172 con la 05 y la lee):")
    with nuevo_cliente() as c:
        c.escribir_coil(172, True)
        comprobar("leer_coils(172, 1)", c.leer_coils(172, 1), [1])


def apartado_4():
    titulo("Apartado 4 - FC02 Read Discrete Inputs")
    print("Sin red (ejemplo del guion, pagina 4):")
    p = LeerEntradasDiscretas(0, 5)
    comprobar("PDU", hexa(p.pdu()), "02 00 00 00 05")
    comprobar("Respuesta procesada", p.procesar(bytes.fromhex("01 13")),
              [1, 1, 0, 0, 1])

    print("Contra el simulador (las entradas discretas no se pueden escribir "
          "desde el cliente:\n  compara con la pestana Servidor y memoria):")
    with nuevo_cliente() as c:
        valores = c.leer_entradas_discretas(0, 5)
        print(f"  entradas discretas 0..4 = {valores}")


def apartado_5():
    titulo("Apartado 5 - FC06 Write Single Register")
    print("Sin red (ejemplo del guion, pagina 5, y un negativo):")
    comprobar("PDU escribir 3 en el 1", hexa(EscribirRegistro(1, 3).pdu()),
              "06 00 01 00 03")
    comprobar("PDU escribir -5 en el 2", hexa(EscribirRegistro(2, -5).pdu()),
              "06 00 02 FF FB")

    print("Contra el simulador (escribe 1234 y -1 en los registros 10 y 11 "
          "y los lee):")
    with nuevo_cliente() as c:
        c.escribir_registro(10, 1234)
        c.escribir_registro(11, -1)
        comprobar("leer_holding_registers(10, 2)",
                  c.leer_holding_registers(10, 2), [1234, 65535])


def apartado_6():
    titulo("Apartado 6 - FC05 Write Single Coil")
    print("Sin red (ejemplo del guion, pagina 5):")
    comprobar("PDU coil 172 ON", hexa(EscribirCoil(172, True).pdu()),
              "05 00 AC FF 00")
    comprobar("PDU coil 172 OFF", hexa(EscribirCoil(172, False).pdu()),
              "05 00 AC 00 00")

    print("Contra el simulador (enciende y apaga la coil 172):")
    with nuevo_cliente() as c:
        c.escribir_coil(172, True)
        comprobar("tras ON, leer_coils(172, 1)", c.leer_coils(172, 1), [1])
        c.escribir_coil(172, False)
        comprobar("tras OFF, leer_coils(172, 1)", c.leer_coils(172, 1), [0])


def apartado_7():
    titulo("Apartado 7 - Errores")

    print("ErrorConexion (puerto en el que no escucha nadie):")
    libre = socket.socket()
    libre.bind((IP, 0))           # el sistema elige un puerto libre...
    puerto_libre = libre.getsockname()[1]
    libre.close()                 # ...y se cierra para que nadie escuche
    try:
        ClienteModbusTCP(IP, puerto_libre).leer_coils(0, 1)
        comprobar("ErrorConexion", "no se lanzo", "ErrorConexion")
    except ErrorConexion as e:
        comprobar("ErrorConexion", type(e).__name__, "ErrorConexion")
        print(f"          mensaje: {e}")

    print("ErrorTimeout (servidor de prueba que acepta pero nunca responde):")
    mudo = socket.socket()
    mudo.bind((IP, 0))
    mudo.listen()
    try:
        ClienteModbusTCP(IP, mudo.getsockname()[1], timeout=1).leer_coils(0, 1)
        comprobar("ErrorTimeout", "no se lanzo", "ErrorTimeout")
    except ErrorTimeout as e:
        comprobar("ErrorTimeout", type(e).__name__, "ErrorTimeout")
        print(f"          mensaje: {e}")
    finally:
        mudo.close()
    print("  (Para probarlo con el simulador: Comportamiento > atender solo al "
          "Unit ID 1\n   con la politica Descartar; nuestro Unit ID es 0xFF.)")

    # La excepción va al final porque es la única que necesita el simulador
    print("ExcepcionModbus (leer 2 registros desde el 9999):")
    with nuevo_cliente() as c:
        try:
            c.leer_holding_registers(9999, 2)
            comprobar("ExcepcionModbus", "no se lanzo", "ExcepcionModbus")
        except ExcepcionModbus as e:
            comprobar("ExcepcionModbus", str(e), "0x02 ILLEGAL DATA ADDRESS")
        # Después de una excepción el cliente debe seguir funcionando
        comprobar("el cliente sigue funcionando",
                  len(c.leer_holding_registers(0, 1)), 1)


APARTADOS = [apartado_1, apartado_2, apartado_3, apartado_4,
             apartado_5, apartado_6, apartado_7]


def main():
    global fallos, hay_simulador
    args = sys.argv[1:]
    pausa = "-s" not in args
    numeros = [int(a) for a in args if a.isdigit()]
    elegidos = ([APARTADOS[n - 1] for n in numeros] if numeros
                else APARTADOS)

    try:
        prueba = ClienteModbusTCP(IP, PUERTO)
        prueba.conectar()
        prueba.cerrar()
    except ErrorConexion:
        hay_simulador = False
        print(f"AVISO: no hay nada escuchando en {IP}:{PUERTO}. Arranca el "
              f"simulador\n(./simulador_modbus) para las pruebas con red; "
              f"ahora solo se hacen las de sin red.")

    for i, apartado in enumerate(elegidos):
        try:
            apartado()
        except SinSimulador:
            print("  [SALTADO] el simulador no esta arrancado")
        except ErrorModbus as e:
            fallos += 1
            print(f"  [FALLO] error inesperado: {type(e).__name__}: {e}")
        if pausa and len(elegidos) > 1 and i < len(elegidos) - 1:
            input("\nPulsa Enter para seguir con el siguiente apartado...")

    titulo("TODO CORRECTO" if fallos == 0 else f"{fallos} FALLO(S)")
    sys.exit(0 if fallos == 0 else 1)


if __name__ == "__main__":
    main()
