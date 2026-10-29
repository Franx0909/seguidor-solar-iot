import math
import random
import time

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from monitoring.models import Device, Sensor, SensorReading

PLC_SLUG = "plc"

# variable -> (unidad, tipo de widget)
PLC_VARIABLES = {
    "plc_inclinacion": ("°", "meter"),
    "plc_azimut_panel": ("°", "meter"),
    "plc_motor_azimut": ("", "led"),
    "plc_motor_elevacion": ("", "led"),
    "plc_voltaje_panel": ("V", "line_chart"),
    "plc_corriente_panel": ("A", "line_chart"),
    "plc_potencia": ("W", "line_chart"),
    "plc_temperatura_panel": ("°C", "numeric"),
}


def simulate_plc_values(now, previous):
    """Valores realistas de un seguidor solar de 2 ejes según la hora local (Chile, UTC-3/-4)."""
    hour = (now.hour - 3 + now.minute / 60) % 24
    # Curva diurna 07:00-19:00: 0 de noche, 1 al mediodía solar.
    day = max(0.0, math.sin(math.pi * (hour - 7) / 12)) if 7 <= hour <= 19 else 0.0
    clouds = random.uniform(0.85, 1.0)

    target_tilt = 90 - 70 * day  # 90° = panel en reposo/horizonte, 20° = sol alto
    target_az = 90 + 180 * (hour - 7) / 12 if day else 90  # Este -> Oeste
    tilt = previous.get("plc_inclinacion", target_tilt)
    az = previous.get("plc_azimut_panel", target_az)
    # El PLC mueve el motor solo si el error supera 1°, máx 2° por ciclo.
    motor_el = abs(target_tilt - tilt) > 1
    motor_az = abs(target_az - az) > 1
    tilt += max(-2, min(2, target_tilt - tilt)) if motor_el else 0
    az += max(-2, min(2, target_az - az)) if motor_az else 0

    voltage = 36.5 * day * clouds + random.uniform(-0.3, 0.3) if day else 0.0
    current = 8.2 * day * clouds + random.uniform(-0.1, 0.1) if day else 0.0
    return {
        "plc_inclinacion": round(tilt, 1),
        "plc_azimut_panel": round(az, 1),
        "plc_motor_azimut": 1.0 if motor_az else 0.0,
        "plc_motor_elevacion": 1.0 if motor_el else 0.0,
        "plc_voltaje_panel": round(max(0.0, voltage), 2),
        "plc_corriente_panel": round(max(0.0, current), 2),
        "plc_potencia": round(max(0.0, voltage) * max(0.0, current), 1),
        "plc_temperatura_panel": round(15 + 30 * day + random.uniform(-0.5, 0.5), 1),
    }


class Command(BaseCommand):
    help = "Simula un PLC del seguidor solar escribiendo lecturas en la BD como si llegaran por MQTT."

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=float, default=2.0, help="Segundos entre lecturas.")

    def handle(self, *args, interval, **options):
        owner = User.objects.filter(is_superuser=True).order_by("id").first()
        if owner is None:
            self.stderr.write("Crea primero un superusuario: python manage.py createsuperuser")
            return

        device, _ = Device.objects.get_or_create(
            slug=PLC_SLUG, defaults={"name": "PLC Seguidor Solar (simulado)", "owner": owner, "tag": "plc-sim"}
        )
        sensors = {}
        for variable, (unit, widget_type) in PLC_VARIABLES.items():
            sensor, created = Sensor.objects.get_or_create(device=device, variable=variable, defaults={"unit": unit})
            if created:
                widget = sensor.get_widget()
                widget.widget_type = widget_type
                widget.max_value = 180
                widget.save()
            sensors[variable] = sensor

        self.stdout.write(self.style.SUCCESS(f"PLC simulado activo en dispositivo '{PLC_SLUG}' cada {interval}s"))
        values = {}
        try:
            while True:
                now = timezone.now()
                values = simulate_plc_values(now, values)
                SensorReading.objects.bulk_create(
                    SensorReading(sensor=sensors[var], value=val, timestamp=now) for var, val in values.items()
                )
                Device.objects.filter(pk=device.pk).update(last_seen_at=now)
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write("PLC simulado detenido.")
