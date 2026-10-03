from django import forms
from django.contrib import admin
from django.contrib.auth.password_validation import validate_password

from .models import Usuario


class UsuarioAdminForm(forms.ModelForm):
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput,
        required=False,
        strip=False,
        help_text='Dejá en blanco para conservar la contraseña actual.',
    )

    class Meta:
        model = Usuario
        fields = ('email', 'nombre', 'apellido', 'rol', 'activo')

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if self.instance._state.adding and not password:
            raise forms.ValidationError('La contraseña es obligatoria al crear un usuario.')
        if password:
            validate_password(password, self.instance)
        return password


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    form = UsuarioAdminForm
    fields = ('email', 'nombre', 'apellido', 'rol', 'activo', 'password')
    list_display = ('email', 'nombre', 'apellido', 'rol', 'activo')
    list_filter = ('rol', 'activo')
    search_fields = ('email', 'nombre', 'apellido')

    def save_model(self, request, obj, form, change):
        password = form.cleaned_data.get('password')
        if password:
            obj.set_password(password)
        super().save_model(request, obj, form, change)
