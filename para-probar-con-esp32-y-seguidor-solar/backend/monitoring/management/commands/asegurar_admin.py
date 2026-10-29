from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from monitoring.models import Profile

# shortcut: usuario de demo con contraseña fija para la entrega; cámbiala antes de exponer el sitio a internet.
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"


class Command(BaseCommand):
    help = "Crea el usuario admin/1234 o le restablece esa contraseña si ya existía."

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(username=ADMIN_USERNAME)
        user.set_password(ADMIN_PASSWORD)
        user.is_active = user.is_staff = user.is_superuser = True
        user.save()
        Profile.objects.update_or_create(user=user, defaults={"role": Profile.ROLE_GLOBAL})
        action = "creado" if created else "actualizado"
        self.stdout.write(self.style.SUCCESS(f"Usuario {action}: {ADMIN_USERNAME} / {ADMIN_PASSWORD}"))
