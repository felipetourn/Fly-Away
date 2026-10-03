from rest_framework import generics, permissions

from .serializers import RegistroPasajeroSerializer, UsuarioSerializer


class RegistroPasajeroView(generics.CreateAPIView):
    serializer_class = RegistroPasajeroSerializer
    permission_classes = [permissions.AllowAny]


class UsuarioActualView(generics.RetrieveAPIView):
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
