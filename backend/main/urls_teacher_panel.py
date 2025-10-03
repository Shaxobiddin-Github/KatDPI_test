from django.urls import path
from . import views_teacher_panel

urlpatterns = [
    path('get-subjects-by-group-semester/', views_teacher_panel.get_subjects_by_group_semester, name='get_subjects_by_group_semester'),
    path('dashboard/', views_teacher_panel.teacher_dashboard, name='teacher_dashboard'),
    path('add-question/', views_teacher_panel.add_question, name='add_question'),
    path('edit-question/<int:question_id>/', views_teacher_panel.edit_question, name='edit_question'),
    path('delete-question/<int:question_id>/', views_teacher_panel.delete_question, name='delete_question'),
    path('logout/', views_teacher_panel.teacher_logout, name='teacher_logout'),
    path('help/', views_teacher_panel.teacher_help, name='teacher_help'),
]
