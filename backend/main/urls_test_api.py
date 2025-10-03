from django.urls import path
from . import views_test_api

urlpatterns = [
    path('login/', views_test_api.testapi_login, name='testapi_login'),
    path('dashboard/', views_test_api.testapi_dashboard, name='testapi_dashboard'),
    path('test/<int:test_id>/', views_test_api.testapi_test, name='testapi_test'),
    path('result/<int:stest_id>/', views_test_api.testapi_result, name='testapi_result'),
    path('stats/', views_test_api.testapi_stats, name='testapi_stats'),
    path('all-results/', views_test_api.testapi_all_results, name='testapi_all_results'),
    path('all-results/excel/', views_test_api.export_all_results_excel, name='export_all_results_excel'),
    path('export-group/<int:group_id>/', views_test_api.export_group_results_excel, name='export_group_results'),
    path('export-students-group/<int:group_id>/', views_test_api.export_students_by_group_excel, name='export_students_by_group_excel'),
    path('export-tutors-kafedra/<int:kafedra_id>/', views_test_api.export_tutors_by_kafedra_excel, name='export_tutors_by_kafedra_excel'),
    path('export-employees-bulim/<int:bulim_id>/', views_test_api.export_employees_by_bulim_excel, name='export_employees_by_bulim_excel'),
    path('export-subject/<str:subject_name>/pdf/', views_test_api.export_subject_results_pdf, name='export_subject_results_pdf'),
    path('verify-qr/<str:hash_code>/', views_test_api.verify_qr, name='verify_qr'),
    path('logout/', views_test_api.testapi_logout, name='testapi_logout'),
]
