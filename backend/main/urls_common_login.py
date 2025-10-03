from django.urls import path
from .views_common_login import common_login, tutor_dashboard, employee_dashboard, common_logout

urlpatterns = [
    path('', common_login, name='common_login'),
    path('tutor/dashboard/', tutor_dashboard, name='tutor_dashboard'),
    path('employee/dashboard/', employee_dashboard, name='employee_dashboard'),
    path('logout/', common_logout, name='common_logout'),
]
