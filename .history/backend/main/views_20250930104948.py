
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from rest_framework.response import Response
from rest_framework import serializers
from django.db import models

# API: Get max question count for a subject (optionally by semester)
@api_view(['GET'])
@permission_classes([AllowAny])
def subject_max_question_count(request):
    subject_id = request.query_params.get('subject_id')
    semester_id = request.query_params.get('semester_id')
    group_id = request.query_params.get('group_id')
    if not subject_id:
        return Response({'error': 'subject_id required'}, status=400)
    try:
        from .models import Subject, Question
        subject = Subject.objects.get(id=subject_id)
    except Subject.DoesNotExist:
        return Response({'error': 'Subject not found'}, status=404)
    # If semester_id provided, filter questions by that semester; otherwise, count all
    if semester_id:
        try:
            sem_id = int(semester_id)
        except ValueError:
            sem_id = None
    else:
        sem_id = None
    qs = Question.objects.filter(subject_id=subject.id)
    if sem_id:
        qs = qs.filter(semester_id=sem_id)
    if group_id:
        qs = qs.filter(group_id=group_id)
    count = qs.count()
    return Response({'max_question_count': count})
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User

class StudentLoginAPIView(APIView):
    def post(self, request):
        access_code = request.data.get('access_code')
        if not access_code:
            return Response({'detail': 'Access code required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(access_code=access_code, role='student')
        except User.DoesNotExist:
            return Response({'detail': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)
        refresh = RefreshToken.for_user(user)
        return Response({
            'token': str(refresh.access_token)
        }, status=status.HTTP_200_OK)
# Yuqoridagi view’lar bilan birga yangilangan versiya
import csv
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
import random
from .models import (
    User, University, Faculty, Group, Subject, Question, AnswerOption, Test,
    TestQuestion, StudentTest, StudentAnswer, Log, StudentTestModification
)
from django.db import models
from .serializers import (
    UserSerializer, UniversitySerializer, FacultySerializer, GroupSerializer, SubjectSerializer,
    QuestionSerializer, AnswerOptionSerializer, TestSerializer, TestQuestionSerializer,
    StudentTestSerializer, StudentTestAdminSerializer, StudentAnswerSerializer, LogSerializer,
    StudentTestModificationSerializer
)
from .permissions import IsAdmin, IsTeacher, IsController, IsStudent, HasMultipleRoles, IsRTTM, IsStudentOrSuper, IsSuperUser

# Mavjud view’lar (qisqartirilgan)
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]

class UniversityViewSet(viewsets.ModelViewSet):
    queryset = University.objects.all()
    serializer_class = UniversitySerializer
    permission_classes = [IsAdmin]

class FacultyViewSet(viewsets.ModelViewSet):
    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer
    permission_classes = [IsAdmin]

class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAdmin]

class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [HasMultipleRoles(allowed_roles=['teacher', 'controller'])]

    def get_queryset(self):
        queryset = super().get_queryset()
        group_id = self.request.query_params.get('group_id')
        if group_id:
            from main.models import GroupSubject
            subject_ids = GroupSubject.objects.filter(group_id=group_id).values_list('subject_id', flat=True)
            queryset = queryset.filter(id__in=subject_ids)
        return queryset

class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [IsTeacher]

class AnswerOptionViewSet(viewsets.ModelViewSet):
    queryset = AnswerOption.objects.all()
    serializer_class = AnswerOptionSerializer
    permission_classes = [IsTeacher]

class TestViewSet(viewsets.ModelViewSet):
    queryset = Test.objects.all()
    serializer_class = TestSerializer
    permission_classes = [IsController]

    def perform_create(self, serializer):
        test = serializer.save(created_by=self.request.user)
        Log.objects.create(user=self.request.user, action=f"Test yaratildi: {test.subject.name}")

    @action(detail=True, methods=['post'])
    def generate_questions(self, request, pk=None):
        test = self.get_object()
        # Use semester-aware filtering if Test has semester
        if getattr(test, 'semester_id', None):
            questions = Question.objects.filter(subject=test.subject, semester_id=test.semester_id)
        else:
            questions = Question.objects.filter(subject=test.subject)
        # Guruh bo'yicha filtrlash (yangi group field). Global (group=None) savollar ham qo'shilishi mumkin.
        if getattr(test, 'group_id', None):
            questions = questions.filter(models.Q(group_id=test.group_id) | models.Q(group__isnull=True))
        if len(questions) < test.question_count:
            return Response({"error": "Yetarli savol mavjud emas"}, status=400)
        
        selected_questions = random.sample(list(questions), test.question_count)
        score_per_question = test.total_score / test.question_count
        
        for question in selected_questions:
            TestQuestion.objects.create(test=test, question=question, score=score_per_question)
        
        Log.objects.create(user=self.request.user, action=f"Test uchun savollar tanlandi: {test.id}")
        return Response({"status": "Savollar tanlandi"})

    @action(detail=True, methods=['get'])
    def export_stats(self, request, pk=None):
        test = self.get_object()
        student_tests = StudentTest.objects.filter(test=test)
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="test_{test.id}_stats.csv"'
        
        writer = csv.writer(response)
        is_super = request.user.is_authenticated and request.user.is_superuser
        if is_super:
            writer.writerow(['Talaba', 'To‘g‘ri javoblar', 'Noto‘g‘ri javoblar', 'Asl ball', 'Yakuniy ball', 'Asl foiz', 'Yakuniy foiz', 'Status'])
        else:
            writer.writerow(['Talaba', 'To‘g‘ri javoblar', 'Noto‘g‘ri javoblar', 'Ball', 'Foiz'])
        
        for student_test in student_tests:
            correct_answers = student_test.answers.filter(is_correct=True).count()
            incorrect_answers = student_test.answers.count() - correct_answers
            original_percentage = (student_test.total_score / test.total_score) * 100 if test.total_score else 0
            final_percentage = (student_test.final_score / test.total_score) * 100 if test.total_score else original_percentage
            if is_super:
                status = 'Override' if student_test.is_overridden else 'Normal'
                writer.writerow([
                    student_test.student.username,
                    correct_answers,
                    incorrect_answers,
                    f"{student_test.total_score:.2f}",
                    f"{student_test.final_score:.2f}",
                    f"{original_percentage:.2f}%",
                    f"{final_percentage:.2f}%",
                    status
                ])
            else:
                writer.writerow([
                    student_test.student.username,
                    correct_answers,
                    incorrect_answers,
                    f"{student_test.final_score:.2f}",
                    f"{final_percentage:.2f}%"
                ])
        
        Log.objects.create(user=self.request.user, action=f"Test statistikasi eksport qilindi: {test.id}")
        return response

class TestQuestionViewSet(viewsets.ModelViewSet):
    queryset = TestQuestion.objects.all()
    serializer_class = TestQuestionSerializer
    permission_classes = [IsController | IsStudent]

class StudentTestViewSet(viewsets.ModelViewSet):
    queryset = StudentTest.objects.all()
    permission_classes = [IsStudentOrSuper]

    def get_serializer_class(self):
        # Superuser uchun to'liq ma'lumot
        if self.request and self.request.user and self.request.user.is_superuser:
            return StudentTestAdminSerializer
        return StudentTestSerializer

    def get_queryset(self):
        # Superuser barcha natijalarni ko'rishi mumkin
        if self.request.user.is_superuser:
            return StudentTest.objects.all()
        return StudentTest.objects.filter(student=self.request.user)

    def perform_create(self, serializer):
        test = serializer.validated_data['test']
        group = test.group
        subject = test.subject
        semester = None
        # GroupSubject orqali semestrni aniqlash (agar kerak bo‘lsa)
        from main.models import GroupSubject
        gs = GroupSubject.objects.filter(group=group, subject=subject).first()
        if gs:
            semester = gs.semester
        # Faqat bitta marta topshirish (yakunlanmagan yoki can_retake=False bo‘lsa bloklanadi)
        already = StudentTest.objects.filter(
            student=self.request.user,
            group=group,
            subject=subject,
            semester=semester
        ).filter(
            models.Q(completed=False) | models.Q(completed=True, can_retake=False)
        ).exists()
        if already:
            raise serializers.ValidationError({"error": "Siz bu fanga ushbu semestrda testni allaqachon topshirgansiz yoki yakunlanmagan test mavjud!"})
        # Yangi yozuvga group, subject, semester ni ham saqlaymiz
        student_test = serializer.save(
            student=self.request.user,
            group=group,
            subject=subject,
            semester=semester
        )
        Log.objects.create(user=self.request.user, action=f"Test boshlandi: {student_test.subject.name}")

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        student_test = self.get_object()
        if student_test.completed:
            return Response({"error": "Test allaqachon yakunlangan"}, status=400)
        
        # Vaqtni tekshirish
        if student_test.start_time + student_test.test.duration < timezone.now():
            student_test.completed = True
            student_test.end_time = timezone.now()
            total_score = sum(answer.score for answer in student_test.answers.all())
            student_test.total_score = total_score
            student_test.save()
            Log.objects.create(user=self.request.user, action=f"Test vaqti tugashi bilan yakunlandi: {student_test.test.subject.name}")
            return Response({"error": "Test vaqti tugadi", "total_score": total_score}, status=400)
        
        student_test.completed = True
        student_test.end_time = timezone.now()
        total_score = sum(answer.score for answer in student_test.answers.all())
        student_test.total_score = total_score
        student_test.save()
        
        Log.objects.create(user=self.request.user, action=f"Test yakunlandi: {student_test.test.subject.name}")
        return Response({"status": "Test yakunlandi", "total_score": total_score})

    # --- Override (faqat superuser) ---
    @action(detail=True, methods=['post'], permission_classes=[IsSuperUser])
    def override(self, request, pk=None):
        st = self.get_object()
        if not st.completed:
            return Response({'detail': 'Test hali yakunlanmagan'}, status=400)
        new_score = request.data.get('new_score', None)
        pass_override = request.data.get('pass_override', None)
        reason = request.data.get('reason')
        if not reason:
            return Response({'detail': 'Sabab majburiy'}, status=400)
        if new_score is None and pass_override is None:
            return Response({'detail': 'Hech qanday o\'zgarish berilmadi'}, status=400)
        try:
            if new_score is not None:
                new_score = float(new_score)
                if new_score < 0 or new_score > st.test.total_score:
                    return Response({'detail': 'Yaroqsiz ball qiymati'}, status=400)
        except ValueError:
            return Response({'detail': 'Ball noto\'g\'ri formatda'}, status=400)

        prev_score = st.overridden_score if st.overridden_score is not None else st.total_score
        prev_pass_override = st.pass_override

        if new_score is not None:
            st.overridden_score = new_score
        if pass_override is not None:
            st.pass_override = bool(pass_override)
        st.override_reason = reason
        from django.utils import timezone as dj_tz
        st.overridden_by = request.user
        st.overridden_at = dj_tz.now()
        st.save()

        StudentTestModification.objects.create(
            student_test=st,
            previous_score=prev_score,
            new_score=st.overridden_score if st.overridden_score is not None else st.total_score,
            previous_pass_override=prev_pass_override,
            new_pass_override=st.pass_override,
            reason=reason,
            changed_by=request.user,
            change_type='override'
        )
        Log.objects.create(user=request.user, action=f"RESULT_OVERRIDE st_test={st.id} old={prev_score} new={st.final_score} pass={st.pass_override}")
        serializer = self.get_serializer(st)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsSuperUser])
    def revert(self, request, pk=None):
        st = self.get_object()
        if not st.is_overridden:
            return Response({'detail': 'Override mavjud emas'}, status=409)
        reason = request.data.get('reason') or 'Revert'
        prev_score = st.overridden_score if st.overridden_score is not None else st.total_score
        prev_pass_override = st.pass_override
        st.overridden_score = None
        st.pass_override = False
        st.override_reason = None
        st.overridden_by = None
        st.overridden_at = None
        st.save()
        StudentTestModification.objects.create(
            student_test=st,
            previous_score=prev_score,
            new_score=st.total_score,
            previous_pass_override=prev_pass_override,
            new_pass_override=False,
            reason=reason,
            changed_by=request.user,
            change_type='revert'
        )
        Log.objects.create(user=request.user, action=f"RESULT_REVERT st_test={st.id} restore_to={st.total_score}")
        serializer = self.get_serializer(st)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[IsSuperUser])
    def history(self, request, pk=None):
        st = self.get_object()
        mods = st.modifications.all()
        ser = StudentTestModificationSerializer(mods, many=True)
        return Response(ser.data)

    @action(detail=True, methods=['get'])
    def check_unanswered(self, request, pk=None):
        student_test = self.get_object()
        test_questions = TestQuestion.objects.filter(test=student_test.test)
        answered_questions = student_test.answers.values_list('question_id', flat=True)
        unanswered = test_questions.exclude(question__id__in=answered_questions)
        
        if unanswered.exists():
            return Response({
                "status": "Belgilanmagan savollar mavjud",
                "unanswered_questions": [q.question.id for q in unanswered]
            }, status=200)
        return Response({"status": "Barcha savollar javoblangan"})

    # Yangi: Qolgan vaqtni tekshirish
    @action(detail=True, methods=['get'])
    def check_time(self, request, pk=None):
        student_test = self.get_object()
        if student_test.completed:
            return Response({"error": "Test allaqachon yakunlangan"}, status=400)
        
        time_remaining = student_test.start_time + student_test.test.duration - timezone.now()
        if time_remaining.total_seconds() <= 0:
            student_test.completed = True
            student_test.end_time = timezone.now()
            student_test.total_score = sum(answer.score for answer in student_test.answers.all())
            student_test.save()
            Log.objects.create(user=self.request.user, action=f"Test vaqti tugashi bilan yakunlandi: {student_test.test.subject.name}")
            return Response({"error": "Test vaqti tugadi"}, status=400)
        
        return Response({"time_remaining_seconds": time_remaining.total_seconds()})

class StudentAnswerViewSet(viewsets.ModelViewSet):
    queryset = StudentAnswer.objects.all()
    serializer_class = StudentAnswerSerializer
    # Superuser ham (admin paneldan) answerlarni ko'rishi va tuzatishi uchun
    permission_classes = [IsStudentOrSuper]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return StudentAnswer.objects.all()
        return StudentAnswer.objects.filter(student_test__student=self.request.user)

    def perform_create(self, serializer):
        student_answer = serializer.save()
        question = student_answer.question
        correct_answers = set(question.answer_options.filter(is_correct=True).values_list('id', flat=True))
        selected_answers = set(student_answer.answer_option.values_list('id', flat=True))
        
        # Maxsus savol turlari uchun logika
        if question.question_type == 'single_choice':
            student_answer.is_correct = selected_answers and (selected_answers.issubset(correct_answers))
        elif question.question_type == 'multiple_choice':
            student_answer.is_correct = selected_answers == correct_answers
        elif question.question_type == 'fill_in_blank':
            student_answer.is_correct = student_answer.text_answer.strip().lower() in [ans.text.strip().lower() for ans in question.answer_options.filter(is_correct=True)]
        elif question.question_type == 'true_false':
            student_answer.is_correct = selected_answers and (selected_answers.issubset(correct_answers))
        elif question.question_type == 'sentence_ordering':
            student_answer.is_correct = student_answer.text_answer == question.answer_options.filter(is_correct=True).first().text
        elif question.question_type == 'matching':
            student_answer.is_correct = student_answer.text_answer == question.answer_options.filter(is_correct=True).first().text
        
        student_answer.score = student_answer.student_test.test.test_questions.get(question=question).score if student_answer.is_correct else 0
        student_answer.save()
        
        Log.objects.create(user=self.request.user, action=f"Javob yuborildi: {question.text[:50]}...")

    @action(detail=True, methods=['post'], permission_classes=[IsSuperUser])
    def adjust(self, request, pk=None):
        """Superuser javobni tuzatishi.
        Faqat is_correct keladi (UI shunday). Agar to'g'ri bo'lsa ball = total_score/question_count, aks holda 0.
        Agar score yoki text_answer keladigan bo'lsa (kelajak ehtimoli) ular ham qo'llab-quvvatlanadi.
        Yakunda StudentTest.total_score qayta hisoblanadi.
        """
        ans = self.get_object()
        data = request.data
        changed = False
        prev_score = ans.score
        prev_correct = ans.is_correct
        new_text = data.get('text_answer', None)
        if new_text is not None:
            ans.text_answer = new_text
            changed = True
        is_correct_present = 'is_correct' in data
        score_present = 'score' in data
        if is_correct_present:
            ans.is_correct = bool(data.get('is_correct'))
            changed = True
        if score_present:
            try:
                new_score = float(data.get('score'))
                if new_score < 0:
                    return Response({'detail': 'Score manfiy bo\'lmasin'}, status=400)
                ans.score = new_score
            except ValueError:
                return Response({'detail': 'Score noto\'g\'ri format'}, status=400)
            changed = True
        # UI soddalashtirilgan: is_correct kelsa va score keltirilmasa — teng taqsimlangan ball
        if is_correct_present and not score_present:
            test = ans.student_test.test
            # Teng taqsimlash: umumiy ball / savollar soni (float saqlaymiz)
            try:
                question_count = test.question_count or test.test_questions.count() or 1
            except Exception:
                question_count = 1
            per_question = (test.total_score / question_count) if question_count else 0
            ans.score = per_question if ans.is_correct else 0

        # Agar endi to'g'ri deb belgilansa (oldin noto'g'ri bo'lgan) – javob matnini/variantlarini ham to'g'ri qilib qo'yamiz
        update_selected_answers = False
        if is_correct_present and ans.is_correct and not prev_correct:
            q = ans.question
            # keyinchalik javob_option.set() qilish uchun avval save qilamiz (agar hali saqlanmagan bo'lsa)
            # (ans hali saqlanmagan bo'lishi mumkin, lekin odatda pk mavjud)
            update_selected_answers = True
            # Turiga qarab to'g'ri javobni set qilamiz
            correct_options_qs = q.answer_options.filter(is_correct=True)
            if q.question_type in ['single_choice', 'true_false']:
                # faqat bitta to'g'ri: birinchi correct ni tanlaymiz
                first = correct_options_qs.first()
                if first:
                    # M2M ni keyin set qilamiz
                    selected_ids = [first.id]
                else:
                    selected_ids = []
            elif q.question_type == 'multiple_choice':
                selected_ids = list(correct_options_qs.values_list('id', flat=True))
            elif q.question_type in ['fill_in_blank', 'sentence_ordering', 'matching']:
                # text_answer ni canonical correct ga o'zgartiramiz
                first = correct_options_qs.first()
                if first and first.text:
                    ans.text_answer = first.text
                selected_ids = None  # M2M ishlatilmaydi
            else:
                selected_ids = None
        else:
            selected_ids = None
        if not changed:
            return Response({'detail': 'Hech narsa o\'zgarmadi'}, status=400)
        ans.save()
        # M2M yangilash (faqat yuqoridagi shartda kerak bo'lsa)
        if update_selected_answers and selected_ids is not None:
            ans.answer_option.set(selected_ids)
        st = ans.student_test
        st.total_score = sum(a.score for a in st.answers.all())
        st.save(update_fields=['total_score'])
        StudentTestModification.objects.create(
            student_test=st,
            previous_score=prev_score,
            new_score=ans.score,
            previous_pass_override=st.pass_override,
            new_pass_override=st.pass_override,
            reason=f"Answer adjust (answer_id={ans.id})",
            changed_by=request.user,
            change_type='override'  # agar xohlasak 'answer_adjust' deb alohida tur kiritishimiz mumkin
        )
        Log.objects.create(user=request.user, action=f"ANSWER_ADJUST ans={ans.id} prev_score={prev_score} new_score={ans.score} prev_correct={prev_correct} new_correct={ans.is_correct}")
        resp = {
            'status': 'updated',
            'answer_id': ans.id,
            'new_score': ans.score,
            'is_correct': ans.is_correct,
            'student_test_total': st.total_score,
        }
        # Qo'shimcha: yangilangan variantlar yoki matnni qaytaramiz front-end darhol yangilashi uchun
        if selected_ids is not None:
            resp['answer_option_ids'] = selected_ids
        if ans.text_answer:
            resp['text_answer'] = ans.text_answer
        return Response(resp)


# Log ViewSet
class LogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Log.objects.all()
    serializer_class = LogSerializer
    permission_classes = [IsAdmin]