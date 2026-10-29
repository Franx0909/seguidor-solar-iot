
import os
import json
import math
import django
import paho.mqtt.client as mqtt

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from monitoring.models import Device

DEVICE_SLUG = "seguidor-solar-iot"

TOPICS = {
    "lina/esp32/light/left": "light_left",
    "lina/esp32/light/right": "light_right",
    "lina/esp32/light/up": "light_up",
    "lina/esp32/light/down": "light_down",
    "lina/esp32/azimuth": "azimuth",
    "lina/esp32/zenith": "zenith",
    "lina/esp32/solar/azimuth": "solar_azimuth",
    "lina/esp32/solar/elevation": "solar_elevation",
    "lina/esp32/latitude": "latitude",
    "lina/esp32/longitude": "longitude",
}

device = Device.objects.filter(slug=DEVICE_SLUG).first()

if device is None:
    raise SystemExit(
        f"ERROR: No existe el dispositivo '{DEVICE_SLUG}' en Django."
    )

if not device.is_active:
    raise SystemExit("ERROR: El dispositivo está desactivado.")

print(f"Dispositivo encontrado: {device.slug}", flush=True)

client = mqtt.Client()

if settings.MQTT_USERNAME:
    client.username_pw_set(
        settings.MQTT_USERNAME,
        settings.MQTT_PASSWORD,
    )


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Conectado a Mosquitto", flush=True)
        client.subscribe("lina/esp32/#", qos=1)
        print("Escuchando datos del ESP32...", flush=True)
    else:
        print(f"Error de conexión MQTT: {rc}", flush=True)


def on_message(client, userdata, msg):
    variable = TOPICS.get(msg.topic)

    if variable is None:
        return

    try:
        value = float(msg.payload.decode("utf-8").strip())

        if not math.isfinite(value):
            raise ValueError("Valor no finito")

    except (UnicodeDecodeError, ValueError):
        print(f"Valor inválido: {msg.topic}", flush=True)
        return

    output_topic = (
        f"{settings.MQTT_TOPIC_PREFIX}/"
        f"{DEVICE_SLUG}/{variable}"
    )

    payload = json.dumps({
        "token": device.auth_token,
        "value": value,
    })

    result = client.publish(
        output_topic,
        payload,
        qos=1,
    )

    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(
            f"{variable}: {value} -> {output_topic}",
            flush=True,
        )
    else:
        print(
            f"Error al publicar {variable}: {result.rc}",
            flush=True,
        )


client.on_connect = on_connect
client.on_message = on_message

print("Iniciando puente MQTT...", flush=True)

client.connect(
    settings.MQTT_BROKER_HOST,
    settings.MQTT_BROKER_PORT,
    keepalive=60,
)

client.loop_forever()
