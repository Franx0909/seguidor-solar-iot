"""Simula el sistema completo del seguidor solar sin hardware.

Una luz imaginaria (el "sol") recorre el cielo de Este a Oeste en un ciclo
corto. Los 4 LDR de la ESP32 leen esa luz según hacia dónde apunta el panel,
la ESP32 corrige sus servos para igualar los LDR (seguimiento real en lazo
cerrado), el PLC informa ángulos, motores y energía generada, y la Raspberry
Pi actúa como gateway. Todo se guarda en la BD igual que si llegara por MQTT.
"""

import math
import random
import time

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from monitoring.models import Device, Sensor, SensorReading, Widget

SIM_TAG = "simulado"  # sensor_command guarda los comandos de estos dispositivos en la BD en vez de MQTT

# slug -> (nombre, {variable: (unidad, widget, min, max)})
DEVICES = {
    "seguidor-solar-iot": (
        "ESP32 Seguidor Solar (simulado)",
        {
            "light_left": ("", Widget.TYPE_LINE_CHART, 0, 4095),
            "light_right": ("", Widget.TYPE_LINE_CHART, 0, 4095),
            "light_up": ("", Widget.TYPE_LINE_CHART, 0, 4095),
            "light_down": ("", Widget.TYPE_LINE_CHART, 0, 4095),
            "azimuth": ("°", Widget.TYPE_METER, 0, 180),
            "zenith": ("°", Widget.TYPE_METER, 0, 180),
            "solar_azimuth": ("°", Widget.TYPE_NUMERIC, 0, 360),
            "solar_elevation": ("°", Widget.TYPE_NUMERIC, -90, 90),
            "mode": ("", Widget.TYPE_BUTTON, 0, 1),
            "servo": ("°", Widget.TYPE_SLIDER, 0, 180),
            "servo2": ("°", Widget.TYPE_SLIDER, 0, 180),
        },
    ),
    "plc": (
        "PLC Seguidor Solar (simulado)",
        {
            "plc_inclinacion": ("°", Widget.TYPE_METER, 0, 90),
            "plc_azimut_panel": ("°", Widget.TYPE_METER, 0, 360),
            "plc_motor_azimut": ("", Widget.TYPE_LED, 0, 1),
            "plc_motor_elevacion": ("", Widget.TYPE_LED, 0, 1),
            "plc_voltaje_panel": ("V", Widget.TYPE_LINE_CHART, 0, 40),
            "plc_corriente_panel": ("A", Widget.TYPE_LINE_CHART, 0, 10),
            "plc_potencia": ("W", Widget.TYPE_LINE_CHART, 0, 350),
            "plc_temperatura_panel": ("°C", Widget.TYPE_NUMERIC, 0, 80),
        },
    ),
    "raspberry": (
        "Raspberry Pi Gateway (simulado)",
        {
            "rpi_temp_cpu": ("°C", Widget.TYPE_NUMERIC, 0, 90),
            "rpi_uso_cpu": ("%", Widget.TYPE_METER, 0, 100),
            "rpi_energia_generada": ("Wh", Widget.TYPE_NUMERIC, 0, 10000),
            "rpi_lecturas_reenviadas": ("", Widget.TYPE_NUMERIC, 0, 1e9),
        },
    ),
}

LDR_MAX = 4095
LDR_GAIN = 0.015  # cuánto cambia cada LDR por grado de error de apuntamiento
TRACK_DEADBAND = 40  # diferencia mínima entre LDR para mover un servo
MAX_STEP = 3.0  # grados por ciclo que puede girar un servo


def light_position(t, cycle):
    """Luz imaginaria como (ángulo de recorrido 0=Este..180=Oeste, elevación); 80% del ciclo es 'día'."""
    p = (t % cycle) / cycle
    if p < 0.8:
        d = p / 0.8
        return 180 * d, 65 * math.sin(math.pi * d)
    return 180 - 180 * (p - 0.8) / 0.2, -10.0  # de noche vuelve bajo el horizonte hacia el Este


def compass_azimuth(track_angle):
    """En Chile (hemisferio sur) el sol pasa por el Norte: 0=Este(90°), 90=Norte(0°), 180=Oeste(270°)."""
    return (90 - track_angle) % 360


def ldr_readings(sun_track, sun_el, servo_az, servo_zen):
    """Los LDR ven más luz del lado hacia donde está la luz respecto al panel."""
    intensity = 3800 * math.sin(math.radians(sun_el)) + 150 if sun_el > 0 else 150
    err_az = sun_track - servo_az
    err_el = sun_el - (90 - servo_zen)

    def ldr(sign, err):
        noisy = intensity * (1 + sign * LDR_GAIN * err) + random.uniform(-15, 15)
        return round(max(0.0, min(LDR_MAX, noisy)))

    return {
        "light_left": ldr(-1, err_az),
        "light_right": ldr(+1, err_az),
        "light_up": ldr(+1, err_el),
        "light_down": ldr(-1, err_el),
    }


def _step(diff):
    if abs(diff) < TRACK_DEADBAND:
        return 0.0
    return max(-MAX_STEP, min(MAX_STEP, diff / 100))


def track(ldr, servo_az, servo_zen):
    """Lógica de la ESP32: girar hacia el LDR más iluminado. De noche vuelve al Este."""
    if max(ldr.values()) < 300:
        return max(0.0, servo_az - MAX_STEP), max(0.0, servo_zen - MAX_STEP)
    servo_az += _step(ldr["light_right"] - ldr["light_left"])
    servo_zen -= _step(ldr["light_up"] - ldr["light_down"])  # más luz arriba = subir el panel
    return max(0.0, min(180.0, servo_az)), max(0.0, min(90.0, servo_zen))


def toward(current, target):
    return current + max(-MAX_STEP, min(MAX_STEP, target - current))


class Command(BaseCommand):
    help = "Simula ESP32 + PLC + Raspberry Pi siguiendo una luz imaginaria que se mueve por el cielo."

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=float, default=1.0, help="Segundos entre lecturas.")
        parser.add_argument("--ciclo", type=float, default=180.0, help="Segundos que dura un 'día' completo.")
        parser.add_argument(
            "--sin-esp32",
            action="store_true",
            help="No simular la ESP32 (usar con el seguidor real conectado); se simulan PLC y Raspberry.",
        )

    def handle(self, *args, interval, ciclo, sin_esp32, **options):
        owner = User.objects.filter(is_superuser=True).order_by("id").first()
        if owner is None:
            self.stderr.write("Crea primero un superusuario: python manage.py createsuperuser")
            return

        sensors = {}
        for slug, (name, variables) in DEVICES.items():
            if sin_esp32 and slug == "seguidor-solar-iot":
                continue
            device, _ = Device.objects.get_or_create(slug=slug, defaults={"name": name, "owner": owner, "tag": SIM_TAG})
            for variable, (unit, widget_type, vmin, vmax) in variables.items():
                sensor, created = Sensor.objects.get_or_create(device=device, variable=variable, defaults={"unit": unit})
                if created:
                    Widget.objects.update_or_create(
                        sensor=sensor,
                        defaults={"widget_type": widget_type, "min_value": vmin, "max_value": vmax, "slider_step": 1},
                    )
                sensors[variable] = sensor

        mode_sensor = sensors.get("mode")
        if mode_sensor and not mode_sensor.readings.exists():
            SensorReading.objects.create(sensor=mode_sensor, value=1, timestamp=timezone.now())

        self.stdout.write(self.style.SUCCESS(
            f"Simulación activa: luz imaginaria con ciclo de {ciclo:.0f}s, lecturas cada {interval}s. Ctrl+C para detener."
        ))

        servo_az, servo_zen = 0.0, 0.0
        energy_wh, forwarded = 0.0, 0
        start = time.monotonic()
        try:
            while True:
                now = timezone.now()
                sun_track, sun_el = light_position(time.monotonic() - start, ciclo)
                ldr = ldr_readings(sun_track, sun_el, servo_az, servo_zen)

                prev_az, prev_zen = servo_az, servo_zen
                auto = True
                if mode_sensor:
                    last = lambda var: sensors[var].readings.values_list("value", flat=True).first()
                    auto = last("mode") != 0
                    if not auto:  # modo manual: los servos van al ángulo pedido desde el dashboard
                        servo_az = toward(servo_az, last("servo") if last("servo") is not None else servo_az)
                        servo_zen = toward(servo_zen, last("servo2") if last("servo2") is not None else servo_zen)
                if auto:
                    servo_az, servo_zen = track(ldr, servo_az, servo_zen)

                panel_el = 90 - servo_zen
                pointing = math.cos(math.radians(min(90, math.hypot(sun_track - servo_az, sun_el - panel_el))))
                sunlight = max(0.0, math.sin(math.radians(sun_el)))
                voltage = 36.5 * min(1, 4 * sunlight) * pointing if sun_el > 0 else 0.0
                current = 8.2 * sunlight * pointing if sun_el > 0 else 0.0
                power = voltage * current
                energy_wh += power * interval / 3600

                values = {
                    **ldr,
                    "azimuth": servo_az,
                    "zenith": servo_zen,
                    "solar_azimuth": compass_azimuth(sun_track),
                    "solar_elevation": sun_el,
                    "plc_inclinacion": servo_zen,
                    "plc_azimut_panel": compass_azimuth(servo_az),
                    "plc_motor_azimut": float(abs(servo_az - prev_az) > 0.1),
                    "plc_motor_elevacion": float(abs(servo_zen - prev_zen) > 0.1),
                    "plc_voltaje_panel": voltage,
                    "plc_corriente_panel": current,
                    "plc_potencia": power,
                    "plc_temperatura_panel": 18 + 30 * sunlight + random.uniform(-0.3, 0.3),
                    "rpi_temp_cpu": 47 + random.uniform(-2, 2),
                    "rpi_uso_cpu": random.uniform(12, 30),
                    "rpi_energia_generada": energy_wh,
                    "rpi_lecturas_reenviadas": forwarded,
                }
                readings = [
                    SensorReading(sensor=sensors[var], value=round(val, 2), timestamp=now)
                    for var, val in values.items()
                    if var in sensors
                ]
                SensorReading.objects.bulk_create(readings)
                forwarded += len(readings)
                Device.objects.filter(pk__in={r.sensor.device_id for r in readings}).update(last_seen_at=now)
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write("Simulación detenida.")
