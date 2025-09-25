
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from main.views_common_login import common_login

from django.conf import settings
from django.conf.urls.static import static

# Asosiy URL yo‘nalishlari
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('main.urls')),
    path('', common_login, name='root_login'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

# Media fayllarni localda ko'rsatish (faqat development uchun)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)