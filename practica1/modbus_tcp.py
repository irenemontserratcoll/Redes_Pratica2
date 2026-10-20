"""Biblioteca cliente Modbus TCP escrita a mano (solo biblioteca estándar).

Estructura:
    CabeceraMBAP       -> los 7 bytes que preceden a cada PDU en Modbus TCP.
    Peticion           -> clase base de todas las funciones Modbus. Cada
                          subclase sabe construir su PDU y procesar la respuesta.
    ClienteModbusTCP   -> abre el socket, envía peticiones y recibe respuestas.

Uso rápido:
    >>> from modbus_tcp import ClienteModbusTCP
    >>> with ClienteModbusTCP("127.0.0.1", 5020, traza=True) as c:
    ...     c.leer_holding_registers(107, 3)
"""

import socket
import struct

AUTOR = "Irene Montserrat"


# ---------------------------------------------------------------------------
# Errores
# ---------------------------------------------------------------------------

class ErrorModbus(Exception):
    """Clase base de todos los errores de esta biblioteca."""


class ErrorProtocolo(ErrorModbus):
    """La respuesta recibida no respeta el protocolo (campos incoherentes)."""


# ---------------------------------------------------------------------------
# Cabecera MBAP
# ---------------------------------------------------------------------------

class CabeceraMBAP:
    """Cabecera MBAP de 7 bytes: Transaction ID, Protocol ID, Length, Unit ID.

    Todos los campos van en big-endian. En struct eso es '>':
        H = entero sin signo de 2 bytes, B = entero sin signo de 1 byte.
    """

    FORMATO = ">HHHB"
    TAMANO = 7  # struct.calcsize(FORMATO)

    def __init__(self, transaction_id, length, unit_id, protocol_id=0):
        self.transaction_id = transaction_id
        self.protocol_id = protocol_id
        self.length = length
        self.unit_id = unit_id

    def empaquetar(self):
        """Devuelve los 7 bytes de la cabecera."""
        return struct.pack(self.FORMATO, self.transaction_id,
                           self.protocol_id, self.length, self.unit_id)

    @classmethod
    def desempaquetar(cls, datos):
        """Construye una CabeceraMBAP a partir de 7 bytes recibidos."""
        tid, pid, length, uid = struct.unpack(cls.FORMATO, datos)
        return cls(tid, length, uid, protocol_id=pid)

    def __repr__(self):
        return (f"CabeceraMBAP(tid={self.transaction_id}, "
                f"pid={self.protocol_id}, len={self.length}, "
                f"uid={self.unit_id})")


# ---------------------------------------------------------------------------
# Peticiones (una clase por función Modbus)
# ---------------------------------------------------------------------------

class Peticion:
    """Clase base de una petición Modbus.

    Cada subclase define:
        CODIGO                       código de función (1 byte)
        datos()                      bytes que van detrás del código de función
        procesar(datos_respuesta)    interpreta los datos de la respuesta
                                     (lo que va detrás del código de función)
    """

    CODIGO = None

    def datos(self):
        raise NotImplementedError

    def pdu(self):
        """PDU completa = código de función + datos."""
        return bytes([self.CODIGO]) + self.datos()

    def procesar(self, datos_respuesta):
        raise NotImplementedError


def _comprobar_rango(nombre, valor, minimo, maximo):
    """Lanza ValueError si valor no está en [minimo, maximo]."""
    if not isinstance(valor, int) or not minimo <= valor <= maximo:
        raise ValueError(f"{nombre} debe estar entre {minimo} y {maximo} "
                         f"(se ha recibido {valor!r})")


def _desempaquetar_bits(datos, cantidad):
    """Convierte bytes con bits empaquetados en una lista de 0/1.

    El primer bit va en el bit 0 (el de menos peso) del primer byte, el
    noveno en el bit 0 del segundo byte, etc.  Ejemplo: 4D 03 con
    cantidad 10 -> [1,0,1,1,0,0,1,0, 1,1].
    """
    # Bit i: byte número i // 8, posición i % 8 dentro de ese byte
    return [(datos[i // 8] >> (i % 8)) & 1 for i in range(cantidad)]


class LeerBits(Peticion):
    """Base común de las funciones 01 y 02: leer elementos de 1 bit.

    Las dos tienen la misma trama; solo cambia el código de función
    (y por tanto la tabla del servidor que se lee).

    Petición: dirección (2 B) + cantidad (2 B)
    Respuesta: número de bytes N (1 B) + N bytes con los bits empaquetados
    """

    def __init__(self, direccion, cantidad):
        _comprobar_rango("direccion", direccion, 0, 0xFFFF)
        _comprobar_rango("cantidad", cantidad, 1, 2000)
        self.direccion = direccion
        self.cantidad = cantidad

    def datos(self):
        return struct.pack(">HH", self.direccion, self.cantidad)

    def procesar(self, datos_respuesta):
        n = datos_respuesta[0]
        esperado = (self.cantidad + 7) // 8  # ceil(cantidad / 8)
        if n != esperado or len(datos_respuesta) != 1 + n:
            raise ErrorProtocolo(f"numero de bytes {n}, se esperaba "
                                 f"{esperado}")
        return _desempaquetar_bits(datos_respuesta[1:], self.cantidad)


class LeerCoils(LeerBits):
    """Función 01: leer coils (tabla 0x, lectura/escritura)."""

    CODIGO = 0x01


class LeerEntradasDiscretas(LeerBits):
    """Función 02: leer discrete inputs (tabla 1x, solo lectura)."""

    CODIGO = 0x02


class LeerRegistros(Peticion):
    """Base común de las funciones 03 y 04: leer registros de 16 bits.

    Las dos tienen la misma trama; solo cambia el código de función
    (y por tanto la tabla del servidor que se lee).

    Petición: dirección (2 B) + cantidad (2 B)
    Respuesta: número de bytes N (1 B) + N bytes (2 por registro)
    """

    def __init__(self, direccion, cantidad):
        _comprobar_rango("direccion", direccion, 0, 0xFFFF)
        _comprobar_rango("cantidad", cantidad, 1, 125)
        self.direccion = direccion
        self.cantidad = cantidad

    def datos(self):
        return struct.pack(">HH", self.direccion, self.cantidad)

    def procesar(self, datos_respuesta):
        n = datos_respuesta[0]
        esperado = 2 * self.cantidad
        if n != esperado or len(datos_respuesta) != 1 + n:
            raise ErrorProtocolo(f"numero de bytes {n}, se esperaba "
                                 f"{esperado}")
        # '>' + 'H' repetido 'cantidad' veces: un entero de 16 bits por registro
        return list(struct.unpack(f">{self.cantidad}H", datos_respuesta[1:]))


class LeerHoldingRegisters(LeerRegistros):
    """Función 03: leer holding registers (tabla 4x, lectura/escritura)."""

    CODIGO = 0x03


class LeerInputRegisters(LeerRegistros):
    """Función 04: leer input registers (tabla 3x, solo lectura)."""

    CODIGO = 0x04


# ---------------------------------------------------------------------------
# Cliente
# ---------------------------------------------------------------------------

class ClienteModbusTCP:
    """Cliente Modbus TCP.

    ip, puerto  dirección del servidor (el simulador usa el 5020)
    unidad      Unit ID que se pone en la cabecera (recomendado 0xFF)
    timeout     segundos que se espera una respuesta
    traza       si es True, imprime cada trama enviada (TX) y recibida (RX)
    """

    def __init__(self, ip="127.0.0.1", puerto=502, unidad=0xFF,
                 timeout=3.0, traza=False):
        self.ip = ip
        self.puerto = puerto
        self.unidad = unidad
        self.timeout = timeout
        self.traza = traza
        self._socket = None
        self._transaction_id = 0

    # --- conexión --------------------------------------------------------

    def conectar(self):
        """Abre la conexión TCP con el servidor."""
        self._socket = socket.create_connection((self.ip, self.puerto),
                                                timeout=self.timeout)

    def cerrar(self):
        """Cierra la conexión (no falla si ya estaba cerrada)."""
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    # Permite usar el cliente con 'with': conecta al entrar y cierra al salir
    def __enter__(self):
        self.conectar()
        return self

    def __exit__(self, *exc):
        self.cerrar()

    # --- envío y recepción -------------------------------------------------

    def _siguiente_transaction_id(self):
        """Devuelve un Transaction ID nuevo (1, 2, ..., 65535, 0, 1, ...)."""
        self._transaction_id = (self._transaction_id + 1) & 0xFFFF
        return self._transaction_id

    def _recibir_exacto(self, n):
        """Lee exactamente n bytes del socket.

        TCP es un flujo: un recv() puede devolver menos bytes de los pedidos,
        así que se repite hasta tenerlos todos.
        """
        datos = b""
        while len(datos) < n:
            trozo = self._socket.recv(n - len(datos))
            if not trozo:  # el servidor ha cerrado la conexión
                raise ErrorProtocolo("el servidor ha cerrado la conexion")
            datos += trozo
        return datos

    def _imprimir(self, prefijo, trama):
        if self.traza:
            print(f"{prefijo}: {trama.hex(' ').upper()}")

    def ejecutar(self, peticion):
        """Envía una petición, espera su respuesta y devuelve el resultado."""
        if self._socket is None:
            self.conectar()

        # 1. Construir la trama: MBAP + PDU
        pdu = peticion.pdu()
        tid = self._siguiente_transaction_id()
        cabecera = CabeceraMBAP(tid, 1 + len(pdu), self.unidad)
        trama = cabecera.empaquetar() + pdu

        # 2. Enviarla
        self._imprimir("TX", trama)
        self._socket.sendall(trama)

        # 3. Recibir la respuesta: 7 bytes de cabecera y luego Length - 1
        bruto_cab = self._recibir_exacto(CabeceraMBAP.TAMANO)
        cab = CabeceraMBAP.desempaquetar(bruto_cab)
        if cab.length < 2:
            raise ErrorProtocolo(f"Length imposible: {cab.length}")
        pdu_resp = self._recibir_exacto(cab.length - 1)
        self._imprimir("RX", bruto_cab + pdu_resp)

        # 4. Comprobar que la cabecera corresponde a nuestra petición
        if cab.transaction_id != tid:
            raise ErrorProtocolo(f"Transaction ID {cab.transaction_id}, "
                                 f"se esperaba {tid}")
        if cab.protocol_id != 0:
            raise ErrorProtocolo(f"Protocol ID {cab.protocol_id}, "
                                 f"se esperaba 0")
        if pdu_resp[0] != peticion.CODIGO:
            raise ErrorProtocolo(f"codigo de funcion 0x{pdu_resp[0]:02X}, "
                                 f"se esperaba 0x{peticion.CODIGO:02X}")

        # 5. La propia petición interpreta sus datos
        return peticion.procesar(pdu_resp[1:])

    # --- atajos ------------------------------------------------------------

    def leer_coils(self, direccion, cantidad):
        """FC01. Devuelve una lista de 0/1, una posición por coil."""
        return self.ejecutar(LeerCoils(direccion, cantidad))

    def leer_entradas_discretas(self, direccion, cantidad):
        """FC02. Devuelve una lista de 0/1, una posición por entrada."""
        return self.ejecutar(LeerEntradasDiscretas(direccion, cantidad))

    def leer_holding_registers(self, direccion, cantidad):
        """FC03. Devuelve una lista de enteros sin signo (0..65535)."""
        return self.ejecutar(LeerHoldingRegisters(direccion, cantidad))

    def leer_input_registers(self, direccion, cantidad):
        """FC04. Devuelve una lista de enteros sin signo (0..65535)."""
        return self.ejecutar(LeerInputRegisters(direccion, cantidad))
