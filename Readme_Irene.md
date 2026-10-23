1. Terminal 1: arranca el simulador

cd ~/Irene/Irene_Redes
./simulador_modbus
Déjala abierta. Si dice que el puerto 5020 ya está en uso, es que ya lo tienes abierto: no hace falta abrir otro.

2. Terminal 2: ve a la carpeta del programa
Abre una pestaña nueva con Ctrl + Shift + T:


cd ~/Irene/Irene_Redes/practica1
No escribas python3 solo: cada orden se lanza entera desde la terminal de Linux (estudiante@...$).

3. Lecturas

python3 modbus_cli.py --puerto 5020 leer-holding 1 3
python3 modbus_cli.py --puerto 5020 leer-input 8 1
python3 modbus_cli.py --puerto 5020 leer-coils 19 10
python3 modbus_cli.py --puerto 5020 leer-entradas 0 5
4. Escrituras (cada una responde OK)

python3 modbus_cli.py --puerto 5020 escribir-registro 2 -5
python3 modbus_cli.py --puerto 5020 escribir-coil 172 on
python3 modbus_cli.py --puerto 5020 escribir-registros 1 10 258 -5
python3 modbus_cli.py --puerto 5020 escribir-coils 19 1 0 1 1 0 0 1 1 1 0
Después de cada una, puedes comprobar en el simulador (pestaña Servidor y memoria) que el valor ha llegado.

5. Función combinada

python3 modbus_cli.py --puerto 5020 leer-escribir 3 6 14 0xFF 0xFF 0xFF
6. Ver las tramas
Añade --traza antes de la orden:


python3 modbus_cli.py --puerto 5020 --traza leer-holding 1 3
7. Errores
; echo $? muestra el código de salida.


python3 modbus_cli.py --puerto 5020 leer-holding 9999 2 ; echo $?
→ EXCEPCION 0x02 ILLEGAL DATA ADDRESS y luego 3.


python3 modbus_cli.py --puerto 5020 leer-holding 0 126 ; echo $?
→ ARGUMENTO INVALIDO: ... y luego 2.


python3 modbus_cli.py --puerto 5999 leer-coils 0 1 ; echo $?
→ ERROR DE CONEXION: ... y luego 5.

Timeout: en el simulador, en Comportamiento, pon atender solo al Unit ID 1 con política Descartar y pulsa Aplicar. Luego:


python3 modbus_cli.py --puerto 5020 leer-coils 0 1 ; echo $?
→ TIMEOUT y luego 4. Después vuelve a poner "Aceptar cualquiera" en el simulador.

Ayuda

python3 modbus_cli.py -h
Muestra todas las opciones y órdenes.

Si te olvidas de --puerto 5020, el programa intentará conectar al puerto 502 y te dará ERROR DE CONEXION.