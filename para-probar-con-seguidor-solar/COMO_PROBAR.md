# Seguidor Solar IoT — para probar con el seguidor solar

Versión del proyecto con simulación completa del sistema, dashboard solar con logo propio y
control de usuarios.

## Qué simula `python manage.py simular_seguidor`

Una **luz imaginaria** (el "sol") recorre el cielo de Este a Oeste pasando por el Norte (como en
Chile) en un ciclo de 3 minutos: 2 min 24 s de "día" y 36 s de "noche".

| Equipo | Slug | Qué hace en la simulación |
|---|---|---|
| ESP32 | `seguidor-solar-iot` | 4 LDR leen la luz según hacia dónde apunta el panel; los servos (`azimuth`, `zenith`) giran hacia el LDR más iluminado (seguimiento en lazo cerrado). De noche vuelve al Este. |
| PLC | `plc` | Inclinación y azimut del panel, motores encendidos/apagados, voltaje, corriente, potencia y temperatura del panel. |
| Raspberry Pi | `raspberry` | Gateway: temperatura y uso de CPU, energía generada acumulada (Wh) y lecturas reenviadas. |

Los tres aparecen en verde en "Estado de conexión" y todas sus variables se ven en tiempo real.

**Variables ejecutadas (control):** en el dashboard, en "Control del Seguidor Solar":
- **Manual / Automático** cambia el modo.
- En **Manual**, los sliders de servo horizontal y vertical mueven el panel al ángulo pedido
  (el PLC muestra el motor encendido mientras se mueve).
- Al volver a **Automático**, el seguidor vuelve a buscar la luz.

Opciones: `--ciclo 60` (día más rápido), `--interval 2` (lecturas cada 2 s),
`--sin-esp32` (no simula la ESP32, para usar el seguidor real).

## Cómo correrlo (sin Docker, SQLite)

Dentro de `backend/`:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
```

Luego, en 2 terminales dentro de `backend/`:

```bash
python manage.py runserver
python manage.py simular_seguidor
```

Abrir http://localhost:8000 e iniciar sesión con el superusuario.

## Con Docker

```bash
cp .env.example .env    # completar contraseñas
docker compose up --build
```

El servicio `simulacion_seguidor` arranca solo.

## Con el seguidor solar real (ESP32)

1. Registrar la ESP32 en **Dispositivos → Agregar** con slug `seguidor-solar-iot` y copiar el
   token al firmware.
2. Correr el broker MQTT y `python manage.py run_mqtt_listener` (con `MQTT_BROKER_HOST=localhost`).
3. Correr `python manage.py simular_seguidor --sin-esp32` para que el PLC y la Raspberry sigan
   simulados mientras la ESP32 envía datos reales.

No levantar esta carpeta y la versión original al mismo tiempo: ambas usan los puertos 8000 y 1883.
