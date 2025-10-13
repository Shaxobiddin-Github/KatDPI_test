from django.urls import path
from . import views_topic as vt

app_name = 'topic'

urlpatterns = [
    path('dashboard/', vt.topic_dashboard, name='dashboard'),
    path('create/', vt.create_topic, name='create_topic'),
    path('<int:topic_id>/', vt.topic_detail, name='topic_detail'),
    path('<int:topic_id>/add-question/', vt.add_question, name='add_question'),
    path('<int:topic_id>/video/save/', vt.save_topic_video, name='save_video'),
    path('<int:topic_id>/video/get/', vt.get_topic_video, name='get_video'),
    path('<int:topic_id>/video/delete/', vt.delete_topic_video, name='delete_video'),
    path('<int:topic_id>/create-test/', vt.create_test, name='create_test'),
    path('student/test/<int:test_id>/start/', vt.start_topic_test, name='start_test'),
    path('student/test/<int:test_id>/video-seen/', vt.mark_topic_video_seen, name='video_seen'),
    path('student/answer/<int:student_test_id>/submit/', vt.submit_answer, name='submit_answer'),
    path('student/test/<int:student_test_id>/finish/', vt.finish_topic_test, name='finish_test'),
    path('question/<int:question_id>/', vt.topic_question_detail, name='question_detail'),
]
