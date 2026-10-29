"""Corre en la Raspberry Pi real: publica su estado por MQTT para que aparezca conectada en el dashboard.

Publica cada INTERVALO segundos en <prefijo>/raspberry/<variable>, con el mismo formato
que la ESP32 ({"value": ..., "token": ...}), así lo guarda run_mqtt_listener.

Uso (en la Raspberry):
    pip install paho-mqtt==1.6.1
    MQTT_BROKER_HOST=192.168.1.50 MQTT_USERNAME=ecs MQTT_PASSWORD=... RASPBERRY_TOKEN=... python3 publicar_estado.py
"""

import json
import os
import time

import paho.mqtt.client as mqtt

BROKER = os.environ.get("MQTT_BROKER_HOST", "localhost")
PORT = int(os.environ.get("MQTT_BROKER_PORT", "1883"))
USERNAME = os.environ.get("MQTT_USERNAME", "")
PASSWORD = os.environ.get("MQTT_PASSWORD", "")
PREFIX = os.environ.get("MQTT_TOPIC_PREFIX", "ecs")
TOKEN = os.environ.get("RASPBERRY_TOKEN", "")
SLUG = os.environ.get("RASPBERRY_SLUG", "raspberry")  # el dashboard reconoce raspberry, raspberry-pi o rpi
INTERVALO = float(os.environ.get("INTERVALO", "5"))


def temp_cpu():
    with open("/sys/class/thermal/thermal_zone0/temp") as f:
        return int(f.read()) / 1000


def uso_cpu():
    return min(100.0, os.getloadavg()[0] / os.cpu_count() * 100)


def uso_memoria():
    info = {}
    with open("/proc/meminfo") as f:
        for line in f:
            key, value = line.split(":", 1)
            info[key] = int(value.split()[0])
    return 100 * (1 - info["MemAvailable"] / info["MemTotal"])


def uptime_horas():
    with open("/proc/uptime") as f:
        return float(f.read().split()[0]) / 3600


LECTURAS = {
    "rpi_temp_cpu": temp_cpu,
    "rpi_uso_cpu": uso_cpu,
    "rpi_uso_memoria": uso_memoria,
    "rpi_uptime_h": uptime_horas,
}


def build_messages():
    """[(topic, payload)] con las lecturas disponibles en este equipo (las que fallen se omiten)."""
    messages = []
    for variable, read in LECTURAS.items():
        try:
            value = round(read(), 2)
        except (OSError, ValueError, KeyError, AttributeError):
            continue
        messages.append((f"{PREFIX}/{SLUG}/{variable}", json.dumps({"value": value, "token": TOKEN})))
    return messages


def main():
    if not TOKEN:
        raise SystemExit("Falta RASPBERRY_TOKEN: registra el dispositivo 'raspberry' en el dashboard y copia su token.")
    client = mqtt.Client()
    if USERNAME:
        client.username_pw_set(USERNAME, PASSWORD)
    client.connect(BROKER, PORT, keepalive=60)
    client.loop_start()
    print(f"Publicando estado de la Raspberry en {BROKER}:{PORT} cada {INTERVALO}s (Ctrl+C para detener)")
    try:
        while True:
            for topic, payload in build_messages():
                client.publish(topic, payload, qos=1)
            time.sleep(INTERVALO)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
