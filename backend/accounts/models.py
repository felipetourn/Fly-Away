from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        PASSENGER = 'passenger', 'Pasajero'
        COUNTER = 'counter', 'Empleado de mostrador'
        ADMIN = 'admin', 'Administrador'

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PASSENGER)
