# Práctica 1 de Modbus TCP: ejecutable

**Autora:** Irene Montserrat · Redes de Comunicación Industriales

`practica1_modbus` es un único ejecutable para Linux que contiene:

- la biblioteca `modbus_tcp.py`: cliente Modbus TCP escrito a mano, solo con
  la biblioteca estándar de Python;
- el programa `modbus_cli.py`;
- el simulador del laboratorio.

No hace falta tener Python instalado.

## Contenido de la carpeta

| Archivo | Qué es |
|---|---|
| `practica1_modbus` | El ejecutable |
| `README.md` | Este documento |
| `lanzador.py` | Código del ejecutable: abre el simulador y la consola de órdenes |
| `construir.sh` | Script que vuelve a generar el ejecutable con PyInstaller |

El código de la práctica está en la carpeta `practica1` del repositorio
(`modbus_tcp.py` y `modbus_cli.py`).

## Cómo ejecutarlo

Desde una terminal, en esta carpeta:

```bash
chmod +x practica1_modbus      # solo la primera vez
./practica1_modbus
```

Hay que ejecutarlo desde la terminal: con doble clic no se vería la consola.

Al arrancar:

1. **Abre el simulador**: el servidor Modbus en el puerto **5020** y su
   interfaz en el navegador (http://127.0.0.1:8080). Si el simulador ya
   estaba abierto, usa ese.
2. **Muestra la consola `modbus>`**, donde se escriben las órdenes de
   `modbus_cli.py`. Cada orden muestra su salida y su código de salida.
3. Con `salir` (o Ctrl+D) termina y **cierra el simulador**, si lo abrió él.

```
Practica 1 de Modbus TCP - cliente escrito a mano
Autora: Irene Montserrat
Abriendo el simulador (se abre también en el navegador)...
Simulador listo en 127.0.0.1:5020. Interfaz: http://127.0.0.1:8080
...
modbus>
```

## Órdenes de la consola

| Orden | Argumentos | Función Modbus |
|---|---|---|
| `leer-coils` | `DIRECCION CANTIDAD` | 01 Read Coils |
| `leer-entradas` | `DIRECCION CANTIDAD` | 02 Read Discrete Inputs |
| `leer-holding` | `DIRECCION CANTIDAD` | 03 Read Holding Registers |
| `leer-input` | `DIRECCION CANTIDAD` | 04 Read Input Registers |
| `escribir-coil` | `DIRECCION VALOR` (`1`/`0`, `on`/`off`) | 05 Write Single Coil |
| `escribir-registro` | `DIRECCION VALOR` | 06 Write Single Register |
| `escribir-coils` | `DIRECCION VALOR...` | 0F Write Multiple Coils |
| `escribir-registros` | `DIRECCION VALOR...` | 10 Write Multiple Registers |
| `leer-escribir` | `DIR_LECTURA CANTIDAD DIR_ESCRITURA VALOR...` | 17 Read/Write Multiple Registers |
| `demo` | | Demostración automática de todo |
| `ayuda` | | Muestra la ayuda |
| `salir` | | Cierra el programa |

**Opciones**, que se escriben antes de la orden:

| Opción | Para qué |
|---|---|
| `--traza` | Muestra las tramas enviadas (TX) y recibidas (RX) |
| `--unidad U` | Unit ID (0xFF por defecto) |
| `--timeout S` | Segundos de espera (3 por defecto) |
| `--puerto P` | Puerto (5020 por defecto, el del simulador) |
| `--ip IP` | IP del servidor (127.0.0.1 por defecto) |

Los números se pueden escribir en decimal (`255`, `-5`) o en hexadecimal
(`0xFF`).

## Demostración rápida

```
modbus> demo
```

Ejecuta, en orden, todas las funciones (01, 02, 03, 04, 05, 06, 0F, 10 y 17),
una excepción Modbus, un argumento inválido y un error de conexión. Al lado
de cada paso indica el apartado del guion.

## Demostración paso a paso

Mientras se ejecutan las órdenes, se puede ver en el navegador cómo cambian
los valores (pestaña **Servidor y memoria**) y cada trama analizada campo a
campo (pestaña **Analizador de tramas**).

### Nivel básico

**Apartado 1: cabecera MBAP y FC03.** Escribe tres valores con la 06 y los
lee con la 03, viendo las tramas:

```
modbus> escribir-registro 107 555
modbus> escribir-registro 109 100
modbus> --traza leer-holding 107 3
TX: 00 01 00 00 00 06 FF 03 00 6B 00 03
RX: 00 01 00 00 00 09 FF 03 06 02 2B 00 00 00 64
107 555 555 0x022B
108 0 0 0x0000
109 100 100 0x0064
[codigo de salida 0]
```

La trama es la del ejemplo del guion (página 4). Solo cambian el
Transaction ID y el Unit ID, que aquí vale 0xFF.

**Apartado 2: FC04.** Primero, en el simulador, pon 10 en el input register 8.

```
modbus> leer-input 8 1
8 10 10 0x000A
```

**Apartado 3: FC01.** Primero, en el simulador, enciende las coils 20, 22,
23, 26, 28 y 29.

```
modbus> --traza leer-coils 20 10
TX: 00 01 00 00 00 06 FF 01 00 14 00 0A
RX: 00 01 00 00 00 05 FF 01 02 4D 03
20 1
21 0
22 1
...
```

**Apartado 4: FC02.** Primero, en el simulador, enciende las entradas
discretas 0, 1 y 4.

```
modbus> leer-entradas 0 5
0 1
1 1
2 0
3 0
4 1
```

**Apartado 5: FC06.** Los negativos se envían en complemento a 2, y la
respuesta es un eco de la petición:

```
modbus> --traza escribir-registro 2 -5
TX: 00 01 00 00 00 06 FF 06 00 02 FF FB
RX: 00 01 00 00 00 06 FF 06 00 02 FF FB
OK
```

**Apartado 6: FC05.** ON se envía como `FF 00`:

```
modbus> --traza escribir-coil 172 on
TX: 00 01 00 00 00 06 FF 05 00 AC FF 00
RX: 00 01 00 00 00 06 FF 05 00 AC FF 00
OK
```

**Apartado 7: errores.**

| Error | Cómo provocarlo | Salida | Código |
|---|---|---|---|
| Excepción Modbus | `leer-holding 9999 2` | `EXCEPCION 0x02 ILLEGAL DATA ADDRESS` | 3 |
| Conexión | `--puerto 5999 leer-coils 0 1` | `ERROR DE CONEXION: ...` | 5 |
| Timeout | En el simulador, *Comportamiento*: atender solo al **Unit ID 1** con la política **Descartar** y pulsar *Aplicar*. Después, `leer-coils 0 1` | `TIMEOUT` (tras 3 s) | 4 |

Después de la excepción, el cliente sigue funcionando: cualquier lectura
posterior responde con normalidad. Tras probar el timeout, hay que volver a
dejar el simulador en "Aceptar cualquiera".

### Nivel avanzado

**Apartado 8: FC10.** Escribe 0x000A y 0x0102 en los registros 1 y 2
(ejemplo del guion, página 6):

```
modbus> --traza escribir-registros 1 0x000A 0x0102
TX: 00 01 00 00 00 0B FF 10 00 01 00 02 04 00 0A 01 02
RX: 00 01 00 00 00 06 FF 10 00 01 00 02
OK
```

**Apartado 9: FC0F.** Escribe 10 coils desde la 19 (guion, página 5):

```
modbus> --traza escribir-coils 19 1 0 1 1 0 0 1 1 1 0
TX: 00 01 00 00 00 09 FF 0F 00 13 00 0A 02 CD 01
RX: 00 01 00 00 00 06 FF 0F 00 13 00 0A
OK
```

**Apartado 10: FC17.** Primero se ponen los valores del ejemplo del guion
(página 7) en los registros 3 a 8. Después se leen 6 desde el 3 y se escribe
0xFF en los registros 14 a 16:

```
modbus> escribir-registros 3 0xFE 0xACD 1 3 0xD 0xFF
modbus> --traza leer-escribir 3 6 14 0xFF 0xFF 0xFF
TX: 00 01 00 00 00 11 FF 17 00 03 00 06 00 0E 00 03 06 00 FF 00 FF 00 FF
RX: 00 01 00 00 00 0F FF 17 0C 00 FE 0A CD 00 01 00 03 00 0D 00 FF
3 254 254 0x00FE
4 2765 2765 0x0ACD
5 1 1 0x0001
6 3 3 0x0003
7 13 13 0x000D
8 255 255 0x00FF
```

**Apartado 11: `modbus_cli.py`.** La consola ejecuta las órdenes de
`modbus_cli.py`, así que cada orden da la salida y el código exactos del
guion:

| Caso | Salida | Código de salida |
|---|---|---|
| Lectura de bits | Una línea por bit: `direccion valor` | 0 |
| Lectura de registros | Una línea por registro: `direccion sin_signo con_signo 0xHHHH` | 0 |
| Escritura correcta | `OK` | 0 |
| Argumento fuera de rango | `ARGUMENTO INVALIDO: <motivo>` (p. ej. `leer-holding 0 126`) | 2 |
| Excepción Modbus | `EXCEPCION 0xCC NOMBRE` | 3 |
| Timeout | `TIMEOUT` | 4 |
| Error de conexión | `ERROR DE CONEXION: <motivo>` | 5 |
| Error de protocolo | `ERROR DE PROTOCOLO: <motivo>` | 6 |

El error de protocolo no se puede provocar con el simulador, porque siempre
responde con tramas correctas.

## Si algo falla

- **"Permission denied" al ejecutar:** falta el permiso de ejecución. Ejecuta
  `chmod +x practica1_modbus`.
- **"No se ha podido arrancar el simulador":** el programa muestra el mensaje
  del simulador. Lo habitual es que el puerto 8080 o el 5020 estén ocupados
  por otro programa.
- **No se abre el navegador:** abre a mano http://127.0.0.1:8080.

## Volver a generar el ejecutable

Hace falta PyInstaller (`python3 -m pip install pyinstaller`). PyInstaller solo
sirve para empaquetar: el código de la práctica no lo usa.

```bash
./construir.sh
```

El script mete en un solo archivo `lanzador.py`, `../practica1/modbus_tcp.py`,
`../practica1/modbus_cli.py` y `../simulador_modbus`.
