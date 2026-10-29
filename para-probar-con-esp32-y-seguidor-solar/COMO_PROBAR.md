# Seguidor Solar IoT — para probar con la ESP32 y el seguidor solar

La **ESP32, el seguidor y la Raspberry Pi son reales**; solo el **PLC se simula**, a partir de
los datos que envía la ESP32. Para probar sin hardware usa la carpeta `solo-simulado`.

| Equipo | Origen |
|---|---|
| ESP32 (`seguidor-solar-iot`) | **real**, por MQTT |
| Raspberry Pi (`raspberry`) | **real**, con `raspberry/publicar_estado.py` |
| PLC (`plc`) | simulado con `python manage.py simular_seguidor --esp32-real` |

## Qué hace el PLC simulado

En cada ciclo lee los servos (`azimuth`, `zenith`) y los 4 LDR de la ESP32 real:
- inclinación y azimut del panel = ángulos reales de los servos;
- motores encendidos cuando los servos reales se mueven;
- voltaje, corriente y potencia según cuánta luz ven los LDR y qué tan parejos están
  (panel bien apuntado = más potencia).

Si la ESP32 deja de enviar datos por más de 15 s, el PLC informa motores detenidos y 0 W.
Los botones Manual/Automático y los sliders del dashboard envían los comandos por MQTT a la
ESP32 real (`mode`, `servo`, `servo2`).

## Credenciales

| Usuario | Contraseña |
|---|---|
| `admin` | `1234` |

Se crea solo al ejecutar `python manage.py migrate` (rol Global, acceso a todo y a `/admin/`).

Si el login dice "Usuario o contraseña incorrectos" (por ejemplo, porque la base de datos ya
tenía un `admin` con otra contraseña), dentro de `backend/` ejecuta:

```bash
python manage.py asegurar_admin
```

Con Docker: `docker compose exec web python manage.py asegurar_admin`.

## Cómo correrlo (SQLite, sin Docker)

Dentro de `backend/`:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

1. Entrar a http://localhost:8000, ir a **Dispositivos → Agregar** y registrar la ESP32 con
   slug `seguidor-solar-iot`. Copiar el token generado al firmware.
2. Tener corriendo el broker Mosquitto y apuntar la ESP32 a la IP de este PC (puerto 1883).
3. En otras terminales dentro de `backend/` (con `MQTT_BROKER_HOST=localhost`):

```bash
python manage.py run_mqtt_listener
python puente_esp32.py              # solo si la ESP32 publica en los topics lina/esp32/...
python manage.py simular_seguidor --esp32-real
```

En el dashboard, ESP32 y PLC deben aparecer en verde en "Estado de conexión".

## Conectar la Raspberry Pi

La Raspberry publica su estado (temperatura y uso de CPU, uso de memoria y horas encendida)
por MQTT, igual que la ESP32, para aparecer en verde en "Estado de conexión".

1. En el dashboard, **Dispositivos → Agregar**, registrar la Raspberry con ID `raspberry`
   y copiar su token.
2. Copiar `raspberry/publicar_estado.py` a la Raspberry e instalar la librería:

```bash
pip install paho-mqtt==1.6.1
```

3. Ejecutarlo en la Raspberry (IP del PC donde corre Mosquitto; usuario y contraseña MQTT del `.env`):

```bash
MQTT_BROKER_HOST=192.168.1.50 MQTT_USERNAME=ecs MQTT_PASSWORD=la-del-env RASPBERRY_TOKEN=el-token python3 publicar_estado.py
```

Si el servidor (Django y Mosquitto) corre en la misma Raspberry, usar `MQTT_BROKER_HOST=localhost`.
Con los tres conectados, ESP32, PLC y Raspberry Pi aparecen en verde.

## Con Docker

```bash
cp .env.example .env    # ya trae admin / 1234
docker compose up --build
```

El servicio `simulacion_seguidor` arranca el PLC simulado con `--esp32-real`. Registrar la ESP32
en el dashboard (paso 1) y apuntarla al broker del PC.

No levantar esta carpeta y `solo-simulado` al mismo tiempo: ambas usan los puertos 8000 y 1883.
