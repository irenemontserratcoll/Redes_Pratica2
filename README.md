# Práctica 1 de Modbus TCP: un cliente escrito a mano

Cliente Modbus TCP escrito en Python byte a byte, sin bibliotecas Modbus
(solo la biblioteca estándar), y probado contra el simulador del laboratorio.

**Autora:** Irene Montserrat · Redes de Comunicación Industriales

## Contenido

| Archivo | Qué es |
|---|---|
| `practica1/modbus_tcp.py` | La biblioteca: cabecera MBAP, cliente y una clase por función Modbus |
| `practica1/modbus_cli.py` | Programa de línea de órdenes que ejecuta una petición con la biblioteca |
| `ejecutable/` | Ejecutable `practica1_modbus` (abre el simulador y una consola de órdenes) y su README con la demostración |
| `Practica1_ModbusTCP.pdf` | Guion de la práctica |

La carpeta `practica1` es la entrega.

## Estado

| Nivel | Apartado | Función | Estado |
|---|---|---|---|
| Básico | 1 | Cabecera MBAP, cliente y 03 Read Holding Registers | ✅ |
| Básico | 2 | 04 Read Input Registers | ✅ |
| Básico | 3 | 01 Read Coils | ✅ |
| Básico | 4 | 02 Read Discrete Inputs | ✅ |
| Básico | 5 | 06 Write Single Register | ✅ |
| Básico | 6 | 05 Write Single Coil | ✅ |
| Básico | 7 | Errores: `ExcepcionModbus`, `ErrorTimeout`, `ErrorConexion` | ✅ |
| Avanzado | 8 | 10 Write Multiple Registers | ✅ |
| Avanzado | 9 | 0F Write Multiple Coils | ✅ |
| Avanzado | 10 | 17 Read/Write Multiple Registers | ✅ |
| Avanzado | 11 | `modbus_cli.py` | ✅ |

## Puesta en marcha

Hacen falta dos terminales.

**Terminal 1: el simulador (servidor).** Déjala abierta todo el rato.

```bash
cd ~/Irene/Irene_Redes
./simulador_modbus
```

Se abre la interfaz en el navegador (http://127.0.0.1:8080). En Linux, un
usuario normal no puede abrir el puerto 502, así que el simulador escucha en
el **5020**.

**Terminal 2: el cliente.**

```bash
cd ~/Irene/Irene_Redes/practica1
```

## Uso de la biblioteca (consola de Python)

```bash
python3
```

```python
from modbus_tcp import *
c = ClienteModbusTCP("127.0.0.1", 5020, traza=True)   # traza: muestra TX/RX

# Lecturas
c.leer_coils(20, 10)                  # 01 -> [1, 0, 1, 1, 0, 0, 1, 0, 1, 1]
c.leer_entradas_discretas(0, 5)       # 02 -> [1, 1, 0, 0, 1]
c.leer_holding_registers(107, 3)      # 03 -> [555, 0, 100]
c.leer_input_registers(8, 1)          # 04 -> [10]

# Escrituras de un elemento
c.escribir_coil(172, True)            # 05: ON se envía como FF 00
c.escribir_registro(1, -5)            # 06: los negativos van en complemento a 2

# Escrituras de varios elementos
c.escribir_coils(19, [1, 0, 1, 1, 0, 0, 1, 1, 1, 0])   # 0F
c.escribir_registros(1, [0x000A, 0x0102])               # 10

# Combinada: escribe primero y lee después, en una sola transacción
c.leer_escribir_registros(3, 6, 14, [0xFF, 0xFF, 0xFF]) # 17

c.cerrar()
```

Los valores entre comentarios son los de los ejemplos del guion. Para
obtenerlos hay que poner antes esos valores en la pestaña *Servidor y memoria*
del simulador.

Después de cambiar `modbus_tcp.py` hay que salir de Python (`exit()`) y volver
a entrar: Python solo lee el módulo la primera vez que se importa.

### Errores

Todos heredan de `ErrorModbus`.

| Error | Cuándo | Cómo provocarlo con el simulador |
|---|---|---|
| `ExcepcionModbus` | El servidor responde rechazando la petición (función + 0x80) | `c.leer_holding_registers(9999, 2)` |
| `ErrorTimeout` | El servidor no responde a tiempo | *Comportamiento*: atender solo al Unit ID 1 con la política *Descartar* (el cliente usa 0xFF) |
| `ErrorConexion` | No se puede conectar o se corta la conexión | `ClienteModbusTCP("127.0.0.1", 5999).leer_coils(0, 1)` |
| `ErrorProtocolo` | La respuesta no tiene sentido (Transaction ID, eco...) | No se da con el simulador |

Después de una `ExcepcionModbus` el cliente sigue funcionando. Tras un timeout
o un error de conexión, el cliente cierra el socket y vuelve a conectar en la
siguiente petición.

## Uso de `modbus_cli.py`

```
python3 modbus_cli.py [--ip IP] [--puerto P] [--unidad U] [--timeout S] [--traza] ORDEN ARGUMENTOS
```

Por defecto: IP `127.0.0.1`, puerto `502`, unidad `0xFF` y timeout de 3 s.
Con el simulador hay que indicar siempre `--puerto 5020`. Los números se
pueden escribir en decimal (`255`, `-5`) o en hexadecimal (`0xFF`).

| Orden | Argumentos |
|---|---|
| `leer-coils`, `leer-entradas`, `leer-holding`, `leer-input` | `DIRECCION CANTIDAD` |
| `escribir-coil` | `DIRECCION VALOR` (`1`/`0`, `on`/`off`, `true`/`false`) |
| `escribir-registro` | `DIRECCION VALOR` |
| `escribir-coils`, `escribir-registros` | `DIRECCION VALOR...` |
| `leer-escribir` | `DIR_LECTURA CANTIDAD DIR_ESCRITURA VALOR...` |

Ejemplos:

```bash
python3 modbus_cli.py --puerto 5020 leer-holding 1 3
python3 modbus_cli.py --puerto 5020 --traza escribir-coils 19 1 0 1 1 0 0 1 1 1 0
python3 modbus_cli.py --puerto 5020 escribir-registro 2 -5
python3 modbus_cli.py --puerto 5020 leer-escribir 3 6 14 0xFF 0xFF 0xFF
echo $?        # muestra el código de salida de la última orden
```

Salida:

| Caso | Salida | Código de salida |
|---|---|---|
| Lectura de bits | Una línea por bit: `direccion valor` | 0 |
| Lectura de registros | Una línea por registro: `direccion sin_signo con_signo 0xHHHH` | 0 |
| Escritura correcta | `OK` | 0 |
| Argumento fuera de rango | `ARGUMENTO INVALIDO: <motivo>` | 2 |
| Excepción Modbus | `EXCEPCION 0xCC NOMBRE` | 3 |
| Timeout | `TIMEOUT` | 4 |
| Error de conexión | `ERROR DE CONEXION: <motivo>` | 5 |
| Error de protocolo | `ERROR DE PROTOCOLO: <motivo>` | 6 |

Ejemplo de lectura de registros:

```
$ python3 modbus_cli.py --puerto 5020 leer-holding 1 3
1 10 10 0x000A
2 258 258 0x0102
3 65531 -5 0xFFFB
```

## Diseño de la biblioteca

Cada función Modbus es una clase que sabe construir su PDU (`datos()`) e
interpretar su respuesta (`procesar()`). El cliente (`ejecutar()`) añade la
cabecera MBAP, envía la trama, recibe la respuesta y comprueba la cabecera y
las excepciones. Las funciones que comparten trama heredan de una clase común:

```
Peticion                       pdu() = código de función + datos()
├── LeerBits                   01, 02: bits empaquetados 8 por byte
│   ├── LeerCoils (01)
│   └── LeerEntradasDiscretas (02)
├── LeerRegistros              03, 04: 2 bytes por registro
│   ├── LeerHoldingRegisters (03)
│   ├── LeerInputRegisters (04)
│   └── LeerEscribirRegistros (17)   reutiliza también EscribirRegistros
├── EscribirSimple             05, 06: dirección + valor; la respuesta es un eco
│   ├── EscribirCoil (05)
│   └── EscribirRegistro (06)
└── EscribirMultiple           0F, 10: dirección + cantidad + N + valores
    ├── EscribirCoils (0F)
    └── EscribirRegistros (10)
```

Cómo se recibe una respuesta: TCP entrega un flujo de bytes, no mensajes.
Por eso el cliente lee primero los 7 bytes de la cabecera MBAP y después
exactamente `Length − 1` bytes más (`_recibir_exacto()`).

## Wireshark (opcional)

Captura en la interfaz `lo` con el filtro `tcp.port == 5020`. Para que
Wireshark analice Modbus en ese puerto: *Analizar › Decodificar como…* y
asignar el puerto TCP 5020 a *Modbus/TCP*.
