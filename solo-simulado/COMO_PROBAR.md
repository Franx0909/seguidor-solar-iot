# Seguidor Solar IoT — solo simulado (sin hardware)

Todo el sistema simulado: no necesitas ESP32, PLC ni Raspberry, ni broker MQTT.
Para probar con el seguidor real usa la carpeta `para-probar-con-esp32-y-seguidor-solar`.

## Qué simula `python manage.py simular_seguidor`

Una **luz imaginaria** (el "sol") recorre el cielo de Este a Oeste pasando por el Norte (como en
Chile) en un ciclo de 3 minutos: 2 min 24 s de "día" y 36 s de "noche".

| Equipo | Slug | Qué hace en la simulación |
|---|---|---|
| ESP32 | `seguidor-solar-iot` | 4 LDR leen la luz según hacia dónde apunta el panel; los servos (`azimuth`, `zenith`) giran hacia el LDR más iluminado (seguimiento en lazo cerrado). De noche vuelve al Este. |
| PLC | `plc` | Inclinación y azimut del seguidor, motores encendidos/apagados, luz promedio de los LDR, error horizontal (derecha − izquierda), error vertical (arriba − abajo) y si está alineado con la luz. |
| Raspberry Pi | `raspberry` | Gateway: temperatura y uso de CPU y lecturas reenviadas. |

Los tres aparecen en verde en "Estado de conexión" y todas sus variables se ven en tiempo real.

**Variables ejecutadas (control):** en el dashboard, en "Control del Seguidor Solar":
- **Manual / Automático** cambia el modo.
- En **Manual**, los sliders de servo horizontal y vertical mueven el panel al ángulo pedido
  (el PLC muestra el motor encendido mientras se mueve).
- Al volver a **Automático**, el seguidor vuelve a buscar la luz.

Opciones: `--ciclo 60` (día más rápido), `--interval 2` (lecturas cada 2 s).

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
```

Luego, en 2 terminales dentro de `backend/`:

```bash
python manage.py runserver
python manage.py simular_seguidor
```

Abrir http://localhost:8000 e iniciar sesión con `admin` / `1234`.

## Con Docker

```bash
cp .env.example .env    # ya trae admin / 1234
docker compose up --build
```

El servicio `simulacion_seguidor` arranca la simulación completa solo.
