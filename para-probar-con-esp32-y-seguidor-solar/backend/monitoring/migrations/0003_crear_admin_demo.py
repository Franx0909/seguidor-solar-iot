from django.contrib.auth.hashers import make_password
from django.db import migrations

# shortcut: usuario de demo con contraseña fija para la entrega; cámbiala antes de exponer el sitio a internet.
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"


def create_demo_admin(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Profile = apps.get_model("monitoring", "Profile")
    user, created = User.objects.get_or_create(
        username=ADMIN_USERNAME,
        defaults={"password": make_password(ADMIN_PASSWORD), "is_staff": True, "is_superuser": True},
    )
    if created:
        Profile.objects.get_or_create(user=user, defaults={"role": "global"})


def remove_demo_admin(apps, schema_editor):
    apps.get_model("auth", "User").objects.filter(username=ADMIN_USERNAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("monitoring", "0002_seed_product_types"),
    ]

    operations = [migrations.RunPython(create_demo_admin, remove_demo_admin)]
