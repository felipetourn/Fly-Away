from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework_simplejwt.views import TokenBlacklistView, TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', lambda r: JsonResponse({'status': 'ok'})),
    path('api/auth/token/', TokenObtainPairView.as_view()),
    path('api/auth/token/refresh/', TokenRefreshView.as_view()),
    path('api/auth/logout/', TokenBlacklistView.as_view()),
    path('api/auth/', include('usuarios.urls')),
    path('api/pagos/', include('pagos.urls')),
    path('api/', include('reservas.urls')),
    path('api/', include('vuelos.urls')),
]
