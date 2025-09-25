
from django.urls import path, include
from main.views_common_login import common_login
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, UniversityViewSet, FacultyViewSet, GroupViewSet, SubjectViewSet,
    QuestionViewSet, AnswerOptionViewSet, TestViewSet, TestQuestionViewSet,
    StudentTestViewSet, StudentAnswerViewSet, LogViewSet
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import StudentLoginAPIView, subject_max_question_count
from .views_log import log_action

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'universities', UniversityViewSet)
router.register(r'faculties', FacultyViewSet)
router.register(r'groups', GroupViewSet)
router.register(r'subjects', SubjectViewSet)
router.register(r'questions', QuestionViewSet)
router.register(r'answer-options', AnswerOptionViewSet)
router.register(r'tests', TestViewSet)
router.register(r'test-questions', TestQuestionViewSet)
router.register(r'student-tests', StudentTestViewSet)
router.register(r'student-answers', StudentAnswerViewSet)
router.register(r'logs', LogViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('', common_login, name='root_login'),
    path('login/', include('main.urls_common_login')),
    path('test-api/', include('main.urls_test_api')),
    path('teacher-panel/', include('main.urls_teacher_panel')),
    path('controller-panel/', include('main.urls_controller_panel')),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('student/login/', StudentLoginAPIView.as_view(), name='student_login'),
    path('log-blur/', log_action, name='log_action'),
    path('subject-max-question-count/', subject_max_question_count, name='subject_max_question_count'),
]