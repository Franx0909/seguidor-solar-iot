# Seguidor Solar IoT — versión con PLC simulado

Esta carpeta es una versión aparte del proyecto con:

- **PLC simulado** (`backend/monitoring/management/commands/simulate_plc.py`): genera cada 2 s
  inclinación, azimut, estado de motores, voltaje, corriente, potencia y temperatura del panel
  según la hora de Chile, y los guarda en la BD como dispositivo `plc`.
- **Dashboard solar** con logo propio (`static/monitoring/img/solar-logo.svg`) y tarjetas en vivo
  de todos los equipos (ESP32, PLC, Raspberry).
- **Control de usuarios**: login/logout de Django, `@login_required` en todas las vistas, roles
  Global/Administrador/Operador. Base de datos: SQLite3 en local, PostgreSQL con Docker.

## Opción A: sin Docker (SQLite)

Dentro de `backend/`:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
```

Luego, en 3 terminales (también dentro de `backend/`):

```bash
python manage.py runserver 0.0.0.0:8000
python manage.py simulate_plc
python manage.py run_mqtt_listener   # requiere un broker Mosquitto; definir MQTT_BROKER_HOST=localhost
```

Abrir http://localhost:8000 e iniciar sesión.

## Opción B: con Docker

```bash
cp .env.example .env    # completar contraseñas
docker compose up --build
```

El servicio `plc_simulator` arranca solo.

## Conectar el seguidor solar real (ESP32)

1. En **Dispositivos → Agregar**, registrar la ESP32 con slug `seguidor-solar-iot`.
2. Copiar el token generado al firmware (`firmware/esp32_ecs_iot/config.h`).
3. Apuntar la ESP32 al broker MQTT (IP de este PC en la red, puerto 1883).

No levantar esta carpeta y la versión original al mismo tiempo: ambas usan los puertos 8000 y 1883.
