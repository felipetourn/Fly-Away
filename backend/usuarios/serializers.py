from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ('id', 'email', 'nombre', 'apellido', 'rol')
        read_only_fields = fields


class RegistroPasajeroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = Usuario
        fields = ('email', 'nombre', 'apellido', 'password')

    def validate_email(self, email):
        email = Usuario.objects.normalize_email(email.strip()).lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('Ya existe una cuenta con este email.')
        return email

    def validate_password(self, password):
        validate_password(password)
        return password

    def create(self, validated_data):
        return Usuario.objects.create_user(
            **validated_data,
            rol=Usuario.Rol.PASAJERO,
        )
