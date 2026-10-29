# Seguidor Solar IoT — para probar con la ESP32 y el seguidor solar

La **ESP32, el seguidor y la Raspberry Pi son reales**; solo el **PLC se simula**, a partir de
los datos que envía la ESP32. Para probar sin hardware usa la carpeta `solo-simulado`.

```
ESP32 --(lina/esp32/...)--> Mosquitto --> Raspberry Pi (puente) --(ecs/seguidor-solar-iot/...)--> Mosquitto --> Django
                                                       \--(ecs/raspberry/... estado propio)
PLC simulado (simular_seguidor --esp32-real) lee de la base de datos los datos de la ESP32
```

| Equipo | Origen |
|---|---|
| ESP32 (`seguidor-solar-iot`) | **real**, publica en `lina/esp32/...` |
| Raspberry Pi (`raspberry`) | **real**, es el puente: `raspberry/puente_raspberry.py` |
| PLC (`plc`) | simulado con `python manage.py simular_seguidor --esp32-real` |

## Qué hace cada parte

**Raspberry Pi (puente):** escucha los topics `lina/esp32/...` de la ESP32 (LDR izquierda,
derecha, arriba, abajo, servos, posición solar), los reenvía a la plataforma con el token de la
ESP32 y cada 5 s publica su propio estado (mensajes reenviados, temperatura y uso de CPU, uso de
memoria) para aparecer conectada.

**PLC simulado:** en cada ciclo lee los servos (`azimuth`, `zenith`) y los 4 LDR de la ESP32:
- inclinación y azimut del panel = ángulos reales de los servos;
- motores encendidos cuando los servos reales se mueven;
- voltaje, corriente y potencia según cuánta luz ven los LDR y qué tan parejos están.

Si la ESP32 deja de enviar datos por más de 15 s, el PLC informa motores detenidos y 0 W.

## Credenciales

| Usuario | Contraseña |
|---|---|
| `admin` | `1234` |

Se crea solo al ejecutar `python manage.py migrate` (rol Global, acceso a todo y a `/admin/`).
Si el login dice "Usuario o contraseña incorrectos", dentro de `backend/` ejecuta
`python manage.py asegurar_admin` (con Docker: `docker compose exec web python manage.py asegurar_admin`).

## 1. Levantar la plataforma en el PC

Con Docker (incluye Mosquitto):

```bash
cp .env.example .env    # ya trae admin / 1234 y el usuario/contraseña MQTT
docker compose up --build
```

El servicio `simulacion_seguidor` arranca el PLC simulado con `--esp32-real`.

Sin Docker (necesitas un Mosquitto instalado con el usuario/contraseña del `.env`), dentro de `backend/`:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

y en otras terminales dentro de `backend/` (con `MQTT_BROKER_HOST=localhost`):

```bash
python manage.py run_mqtt_listener
python manage.py simular_seguidor --esp32-real
```

## 2. Registrar los equipos en el dashboard

Entrar a http://localhost:8000 con `admin` / `1234`, ir a **Dispositivos → Agregar** y crear:

| ID del dispositivo | Para qué |
|---|---|
| `seguidor-solar-iot` | ESP32: copiar su token (lo usa el puente) |
| `raspberry` | Raspberry Pi: copiar su token |

## 3. ESP32

Apuntarla al Mosquitto del PC (IP del PC, puerto 1883, usuario/contraseña MQTT del `.env`).
Debe publicar en `lina/esp32/light/left`, `lina/esp32/light/right`, `lina/esp32/light/up`,
`lina/esp32/light/down`, `lina/esp32/azimuth`, `lina/esp32/zenith`, etc., con el valor como
número en texto plano (ej. `2345`).

## 4. Raspberry Pi (puente)

Copiar `raspberry/puente_raspberry.py` a la Raspberry e instalar la librería:

```bash
pip install paho-mqtt==1.6.1
```

Ejecutarlo con la IP del PC, el usuario/contraseña MQTT del `.env` y los dos tokens del paso 2:

```bash
MQTT_BROKER_HOST=192.168.1.50 MQTT_USERNAME=ecs MQTT_PASSWORD=la-del-env ESP32_TOKEN=token-esp32 RASPBERRY_TOKEN=token-raspberry python3 puente_raspberry.py
```

En el dashboard, **ESP32, PLC y Raspberry Pi** deben aparecer en verde y los LDR de izquierda,
derecha, arriba y abajo en el gráfico.

No levantar esta carpeta y `solo-simulado` al mismo tiempo: ambas usan los puertos 8000 y 1883.
