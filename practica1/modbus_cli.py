"""Programa de línea de órdenes: ejecuta una sola petición Modbus TCP.

Uso:
    python3 modbus_cli.py [--ip IP] [--puerto P] [--unidad U] [--timeout S]
                          [--traza] ORDEN ARGUMENTOS

Órdenes:
    leer-coils, leer-entradas, leer-holding, leer-input   DIRECCION CANTIDAD
    escribir-coil, escribir-registro                      DIRECCION VALOR
    escribir-coils, escribir-registros                    DIRECCION VALOR...
    leer-escribir     DIR_LECTURA CANTIDAD DIR_ESCRITURA VALOR...

Los números pueden escribirse en decimal (255, -5) o en hexadecimal (0xFF).

Salida y código de salida:
    lectura de bits         "direccion valor" por línea              0
    lectura de registros    "direccion sin_signo con_signo 0xHHHH"   0
    escritura correcta      OK                                       0
    argumento fuera de rango    ARGUMENTO INVALIDO: <motivo>         2
    excepción Modbus            EXCEPCION 0xCC NOMBRE                3
    timeout                     TIMEOUT                              4
    error de conexión           ERROR DE CONEXION: <motivo>          5
    error de protocolo          ERROR DE PROTOCOLO: <motivo>         6
"""

import argparse
import sys

from modbus_tcp import (ClienteModbusTCP, ErrorConexion, ErrorProtocolo,
                        ErrorTimeout, ExcepcionModbus)


def salir(mensaje, codigo):
    print(mensaje)
    sys.exit(codigo)


class Parser(argparse.ArgumentParser):
    """ArgumentParser que informa de los errores con el formato pedido."""

    def error(self, message):
        salir(f"ARGUMENTO INVALIDO: {message}", 2)


# --- conversión de argumentos --------------------------------------------

def entero(texto):
    """Entero en decimal o hexadecimal (0x...), con o sin signo."""
    try:
        return int(texto, 0)  # base 0: entiende 0x.., 0b.., -5...
    except ValueError:
        pass
    try:
        return int(texto, 10)  # "007": base 0 no admite ceros a la izquierda
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{texto}' no es un numero entero")


def bit(texto):
    """Valor de una coil: 1/0, on/off, true/false."""
    valores = {"1": 1, "on": 1, "true": 1, "0": 0, "off": 0, "false": 0}
    try:
        return valores[texto.lower()]
    except KeyError:
        raise argparse.ArgumentTypeError(f"'{texto}' no es un valor de coil "
                                         f"(usar 1/0, on/off o true/false)")


# --- impresión de resultados ---------------------------------------------

def imprimir_bits(direccion, bits):
    for i, valor in enumerate(bits):
        print(f"{direccion + i} {valor}")


def imprimir_registros(direccion, registros):
    for i, valor in enumerate(registros):
        con_signo = valor - 0x10000 if valor >= 0x8000 else valor
        print(f"{direccion + i} {valor} {con_signo} 0x{valor:04X}")


def imprimir_ok(*_):
    print("OK")


# --- definición de las órdenes -------------------------------------------

def crear_parser():
    parser = Parser(prog="modbus_cli.py",
                    description="Ejecuta una sola peticion Modbus TCP.")
    parser.add_argument("--ip", default="127.0.0.1")
    parser.add_argument("--puerto", type=entero, default=502)
    parser.add_argument("--unidad", type=entero, default=0xFF,
                        help="Unit ID (0..255, por defecto 0xFF)")
    parser.add_argument("--timeout", type=float, default=3.0,
                        help="segundos de espera (por defecto 3)")
    parser.add_argument("--traza", action="store_true",
                        help="muestra las tramas TX/RX")
    ordenes = parser.add_subparsers(dest="orden", metavar="ORDEN",
                                    required=True)

    # Cada orden guarda en 'accion' una función (cliente, args) que hace la
    # petición e imprime el resultado.

    # Lecturas: DIRECCION CANTIDAD
    lecturas = [
        ("leer-coils", "leer_coils", imprimir_bits),
        ("leer-entradas", "leer_entradas_discretas", imprimir_bits),
        ("leer-holding", "leer_holding_registers", imprimir_registros),
        ("leer-input", "leer_input_registers", imprimir_registros),
    ]
    for nombre, metodo, imprimir in lecturas:
        orden = ordenes.add_parser(nombre)
        orden.add_argument("direccion", type=entero)
        orden.add_argument("cantidad", type=entero)
        # metodo=metodo, imprimir=imprimir: fija los valores de esta vuelta
        # del bucle (si no, todas las órdenes usarían los de la última)
        orden.set_defaults(accion=lambda c, a, metodo=metodo, imprimir=imprimir:
                           imprimir(a.direccion, getattr(c, metodo)(
                               a.direccion, a.cantidad)))

    # Escrituras de un elemento: DIRECCION VALOR
    orden = ordenes.add_parser("escribir-coil")
    orden.add_argument("direccion", type=entero)
    orden.add_argument("valor", type=bit)
    orden.set_defaults(accion=lambda c, a:
                       imprimir_ok(c.escribir_coil(a.direccion, a.valor)))

    orden = ordenes.add_parser("escribir-registro")
    orden.add_argument("direccion", type=entero)
    orden.add_argument("valor", type=entero)
    orden.set_defaults(accion=lambda c, a:
                       imprimir_ok(c.escribir_registro(a.direccion, a.valor)))

    # Escrituras de varios elementos: DIRECCION VALOR...
    orden = ordenes.add_parser("escribir-coils")
    orden.add_argument("direccion", type=entero)
    orden.add_argument("valores", type=bit, nargs="+")
    orden.set_defaults(accion=lambda c, a:
                       imprimir_ok(c.escribir_coils(a.direccion, a.valores)))

    orden = ordenes.add_parser("escribir-registros")
    orden.add_argument("direccion", type=entero)
    orden.add_argument("valores", type=entero, nargs="+")
    orden.set_defaults(accion=lambda c, a: imprimir_ok(
        c.escribir_registros(a.direccion, a.valores)))

    # Combinada: DIR_LECTURA CANTIDAD DIR_ESCRITURA VALOR...
    orden = ordenes.add_parser("leer-escribir")
    orden.add_argument("direccion_lectura", type=entero)
    orden.add_argument("cantidad", type=entero)
    orden.add_argument("direccion_escritura", type=entero)
    orden.add_argument("valores", type=entero, nargs="+")
    orden.set_defaults(accion=lambda c, a: imprimir_registros(
        a.direccion_lectura, c.leer_escribir_registros(
            a.direccion_lectura, a.cantidad, a.direccion_escritura,
            a.valores)))

    return parser


def main():
    args = crear_parser().parse_args()
    if not 0 <= args.unidad <= 255:
        salir("ARGUMENTO INVALIDO: la unidad debe estar entre 0 y 255", 2)
    if not 0 < args.puerto <= 65535:
        salir("ARGUMENTO INVALIDO: el puerto debe estar entre 1 y 65535", 2)
    if args.timeout <= 0:
        salir("ARGUMENTO INVALIDO: el timeout debe ser mayor que 0", 2)

    cliente = ClienteModbusTCP(args.ip, args.puerto, args.unidad,
                               args.timeout, args.traza)
    try:
        # Las peticiones validan sus argumentos al crearse, antes de conectar:
        # un argumento fuera de rango da ValueError sin tocar la red
        args.accion(cliente, args)
    except ValueError as e:
        salir(f"ARGUMENTO INVALIDO: {e}", 2)
    except ExcepcionModbus as e:
        salir(f"EXCEPCION 0x{e.codigo:02X} {e.nombre}", 3)
    except ErrorTimeout:
        salir("TIMEOUT", 4)
    except ErrorConexion as e:
        salir(f"ERROR DE CONEXION: {e}", 5)
    except ErrorProtocolo as e:
        salir(f"ERROR DE PROTOCOLO: {e}", 6)
    finally:
        cliente.cerrar()


if __name__ == "__main__":
    main()
