from django.urls import path
from . import views_topic as vt

app_name = 'topic'

urlpatterns = [
    path('dashboard/', vt.topic_dashboard_entry, name='dashboard'),
    path('student/login/', vt.topic_student_login, name='student_login'),
    path('student/panel/', vt.topic_student_dashboard, name='student_dashboard'),
    path('create/', vt.create_topic, name='create_topic'),
    path('<int:topic_id>/', vt.topic_detail, name='topic_detail'),
    path('<int:topic_id>/manage/', vt.topic_manage, name='topic_manage'),
    path('<int:topic_id>/add-question/', vt.add_question, name='add_question'),
    path('<int:topic_id>/video/save/', vt.save_topic_video, name='save_video'),
    path('<int:topic_id>/video/get/', vt.get_topic_video, name='get_video'),
    path('<int:topic_id>/video/delete/', vt.delete_topic_video, name='delete_video'),
    path('<int:topic_id>/create-test/', vt.create_test, name='create_test'),
    path('test/<int:test_id>/results/', vt.topic_test_results, name='test_results'),
    path('student/test/<int:test_id>/start/', vt.start_topic_test, name='start_test'),
    path('student/test/<int:test_id>/video-seen/', vt.mark_topic_video_seen, name='video_seen'),
    path('student/answer/<int:student_test_id>/submit/', vt.submit_answer, name='submit_answer'),
    path('student/test/<int:student_test_id>/finish/', vt.finish_topic_test, name='finish_test'),
    path('student/test/<int:student_test_id>/remaining/', vt.test_remaining_time, name='remaining_time'),
    path('question/<int:question_id>/', vt.topic_question_detail, name='question_detail'),
    path('topic/<int:topic_id>/stats/', vt.topic_stats, name='topic_stats'),
    # CRUD additions
    path('<int:topic_id>/question/<int:question_id>/update/', vt.update_topic_question, name='question_update'),
    path('<int:topic_id>/question/<int:question_id>/delete/', vt.delete_topic_question, name='question_delete'),
    path('<int:topic_id>/test/<int:test_id>/update/', vt.update_topic_test, name='test_update'),
    path('<int:topic_id>/test/<int:test_id>/delete/', vt.delete_topic_test, name='test_delete'),
    path('<int:topic_id>/import/', vt.topic_import_questions, name='import_questions'),
    path('<int:topic_id>/export/', vt.topic_export_questions, name='export_questions'),
    path('<int:topic_id>/export-xlsx/', vt.topic_export_questions_xlsx, name='export_questions_xlsx'),
    # Analytics
    path('<int:topic_id>/analytics/group-comparison/', vt.topic_group_comparison, name='analytics_group_comparison'),
    path('<int:topic_id>/analytics/personal/', vt.topic_student_personal_stats, name='analytics_personal'),
    path('<int:topic_id>/analytics/test/<int:test_id>/participants/', vt.topic_test_participants_stats, name='analytics_test_participants'),
]
