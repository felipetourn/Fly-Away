import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **campos):
        if not email:
            raise ValueError('El email es obligatorio')
        usuario = self.model(email=self.normalize_email(email), **campos)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, email, password=None, **campos):
        campos['rol'] = Usuario.Rol.ADMINISTRADOR
        return self.create_user(email, password, **campos)


class Usuario(AbstractBaseUser):
    """Tabla `usuarios` del DBML. Sin PermissionsMixin: el rol define el acceso."""

    class Rol(models.TextChoices):
        ADMINISTRADOR = 'administrador', 'Administrador'
        EMPLEADO_MOSTRADOR = 'empleado_mostrador', 'Empleado de mostrador'
        PASAJERO = 'pasajero', 'Pasajero'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128, db_column='password_hash')
    nombre = models.CharField(max_length=150)
    apellido = models.CharField(max_length=150)
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.PASAJERO)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    last_login = None  # no está en el DBML

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'apellido']

    class Meta:
        db_table = 'usuarios'

    def __str__(self):
        return self.email

    @property
    def is_active(self):
        return self.activo

    # El admin de Django es una herramienta interna: solo para administradores.
    @property
    def is_staff(self):
        return self.activo and self.rol == self.Rol.ADMINISTRADOR

    def has_perm(self, perm, obj=None):
        return self.is_staff

    def has_module_perms(self, app_label):
        return self.is_staff
