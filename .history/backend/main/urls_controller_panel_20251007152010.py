from django.urls import path




from . import views_controller_panel
from . import views_participated

urlpatterns = [
    path('group-subjects/', views_controller_panel.group_subjects_list, name='group_subjects_list'),
    path('get-subjects-by-group/', views_controller_panel.get_subjects_by_group, name='get_subjects_by_group'),
    path('get-teachers-by-subject-semester/', views_controller_panel.get_teachers_by_subject_semester, name='get_teachers_by_subject_semester'),
    path('dashboard/', views_controller_panel.controller_dashboard, name='controller_dashboard'),
    path('add-test/', views_controller_panel.add_test, name='add_test'),
    path('assign-test/<int:test_id>/', views_controller_panel.assign_test, name='assign_test'),
    path('edit-test/<int:test_id>/', views_controller_panel.edit_test, name='edit_test'),
    path('delete-test/<int:test_id>/', views_controller_panel.delete_test, name='delete_test'),
    path('extend-test-time/<int:test_id>/', views_controller_panel.extend_test_time, name='extend_test_time'),
    path('subject-questions/<int:subject_id>/', views_controller_panel.subject_questions, name='subject_questions'),
    path('delete-question/<int:question_id>/', views_controller_panel.delete_question, name='delete_question'),
    path('logout/', views_controller_panel.controller_logout, name='controller_logout'),
    path('help/', views_controller_panel.controller_help, name='controller_help'),
    path('add-user/', views_controller_panel.add_user, name='add_user'),
    path('export-users-excel/', views_controller_panel.export_users_excel, name='export_users_excel'),
    path('export-users-word/', views_controller_panel.export_users_word, name='export_users_word'),
    path('export-users-pdf/', views_controller_panel.export_users_pdf, name='export_users_pdf'),
    path('download-student-import-template/', views_controller_panel.download_student_import_template, name='download_student_import_template'),

    # Qatnashganlar ro'yxati va qayta topshirish
    path('participated-students/', views_participated.participated_students_list, name='participated_students_list'),
    path('allow-retake/', views_participated.allow_retake, name='allow_retake'),
    path('allow-retake-bulk/', views_participated.allow_retake_bulk, name='allow_retake_bulk'),
    path('allow-retake-group/', views_participated.allow_retake_group, name='allow_retake_group'),
]
