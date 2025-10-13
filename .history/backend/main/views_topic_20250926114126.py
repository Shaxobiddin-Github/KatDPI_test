from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from .models import Topic, TopicIntroVideo, TopicQuestion, TopicAnswerOption, TopicTest, TopicStudentTest, TopicStudentAnswer, Subject, Group, User
from django.db.models import Sum
from datetime import timedelta
import random

# ---------- Helpers ----------

def teacher_required(fn):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or getattr(request.user, 'role', None) != 'teacher':
            return HttpResponseForbidden('Ruxsat yo\'q')
        return fn(request, *args, **kwargs)
    return wrapper

# ---------- Topic Dashboard ----------
@login_required
@teacher_required
def topic_dashboard(request):
    topics = Topic.objects.filter(created_by=request.user).select_related('subject', 'group')
    return render(request, 'topic_panel/dashboard.html', {'topics': topics})

# ---------- Create Topic ----------
@login_required
@teacher_required
@require_http_methods(["POST"])
@transaction.atomic
def create_topic(request):
    subject_id = request.POST.get('subject_id')
    group_id = request.POST.get('group_id')
    title = request.POST.get('title')
    description = request.POST.get('description')
    if not (subject_id and group_id and title):
        return JsonResponse({'error': 'Majburiy maydonlar yo\'q'}, status=400)
    subject = get_object_or_404(Subject, id=subject_id)
    group = get_object_or_404(Group, id=group_id)
    topic = Topic.objects.create(subject=subject, group=group, title=title, description=description or '', created_by=request.user)
    return JsonResponse({'id': topic.id, 'title': topic.title})

# ---------- Topic Detail (basic JSON) ----------
@login_required
@teacher_required
def topic_detail(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id, created_by=request.user)
    questions = topic.questions.count()
    tests = topic.tests.count()
    has_video = hasattr(topic, 'intro_video')
    return JsonResponse({'id': topic.id, 'title': topic.title, 'questions': questions, 'tests': tests, 'has_video': has_video})

# ---------- Add Question ----------
@login_required
@teacher_required
@require_http_methods(["POST"])
@transaction.atomic
def add_question(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id, created_by=request.user)
    text = request.POST.get('text')
    qtype = request.POST.get('question_type')
    if qtype not in ['single', 'multi']:
        return JsonResponse({'error': 'Noto\'g\'ri savol turi'}, status=400)
    if not text:
        return JsonResponse({'error': 'Matn kerak'}, status=400)
    image = request.FILES.get('image')
    question = TopicQuestion.objects.create(topic=topic, text=text, question_type=qtype, image=image, created_by=request.user)
    # Expect options posted as option_text_1..n with is_correct_1..n
    option_keys = [k for k in request.POST.keys() if k.startswith('option_text_')]
    correct_count = 0
    for key in option_keys:
        idx = key.split('_')[-1]
        otext = request.POST.get(key)
        if not otext:
            continue
        is_correct = request.POST.get(f'is_correct_{idx}') == 'on'
        if is_correct:
            correct_count += 1
        TopicAnswerOption.objects.create(question=question, text=otext, is_correct=is_correct)
    # Validation: single => exactly 1 correct; multi => at least 2
    if qtype == 'single' and correct_count != 1:
        question.delete()
        return JsonResponse({'error': 'Bitta to\'g\'ri javob bo\'lishi kerak'}, status=400)
    if qtype == 'multi' and correct_count < 2:
        question.delete()
        return JsonResponse({'error': 'Kamida 2 to\'g\'ri javob bo\'lishi kerak (multi).'}, status=400)
    return JsonResponse({'id': question.id, 'text': question.text})

# ---------- Create Test ----------
@login_required
@teacher_required
@require_http_methods(["POST"])
@transaction.atomic
def create_test(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id, created_by=request.user)
    title = request.POST.get('title') or f"{topic.title} testi"
    question_count = int(request.POST.get('question_count') or 0)
    total_score = int(request.POST.get('total_score') or 0)
    duration_minutes = int(request.POST.get('duration_minutes') or 0)
    # Optional multiple groups (comma separated IDs or multiple inputs named group_ids)
    raw_group_ids = request.POST.getlist('group_ids') or []
    if len(raw_group_ids) == 1 and ',' in raw_group_ids[0]:
        raw_group_ids = [g.strip() for g in raw_group_ids[0].split(',') if g.strip()]
    if question_count <= 0 or total_score <=0 or duration_minutes <=0:
        return JsonResponse({'error':'Parametrlar to\'liq emas'}, status=400)
    available = list(topic.questions.values_list('id', flat=True))
    if len(available) < question_count:
        return JsonResponse({'error':'Mavzuda yetarli savol yo\'q'}, status=400)
    chosen = random.sample(available, question_count)
    test = TopicTest.objects.create(
        topic=topic,
        title=title,
        question_count=question_count,
        total_score=total_score,
        duration=timedelta(minutes=duration_minutes),
        created_by=request.user,
        question_ids=chosen
    )
    if raw_group_ids:
        valid_groups = Group.objects.filter(id__in=raw_group_ids)
        if valid_groups.exists():
            test.groups.set(valid_groups)
    return JsonResponse({'id': test.id, 'title': test.title})

# ---------- Start Test (student gating) ----------
@login_required
def start_topic_test(request, test_id):
    test = get_object_or_404(TopicTest, id=test_id)
    if getattr(request.user, 'role', '') != 'student':
        return HttpResponseForbidden('Talaba emas')
    # Group check: allow if student's group matches topic.group OR in additional test.groups
    allowed_group_ids = {test.topic.group_id} if test.topic.group_id else set()
    # Add many-to-many extra groups
    extra_ids = list(test.groups.values_list('id', flat=True))
    allowed_group_ids.update(extra_ids)
    if request.user.group_id not in allowed_group_ids:
        return HttpResponseForbidden('Bu test sizning guruhingiz uchun emas')
    # Pre-video gating
    if hasattr(test.topic, 'intro_video') and not request.session.get(f'topic_video_seen_{test.id}'):
        return render(request, 'topic_panel/pre_video.html', {'test': test, 'video': test.topic.intro_video})
    # Create or reuse student test
    st, created = TopicStudentTest.objects.get_or_create(student=request.user, test=test)
    if created or not st.randomized_question_ids:
        # Random order of existing frozen question_ids
        st.randomized_question_ids = random.sample(test.question_ids, len(test.question_ids))
        st.save()
    duration_seconds = int(test.duration.total_seconds()) if test.duration else 0
    return render(request, 'topic_panel/test_run.html', {'test': test, 'student_test': st, 'duration_seconds': duration_seconds})

# ---------- Mark video seen ----------
@login_required
def mark_topic_video_seen(request, test_id):
    test = get_object_or_404(TopicTest, id=test_id)
    request.session[f'topic_video_seen_{test.id}'] = True
    return JsonResponse({'ok': True})

# ---------- Submit Answer ----------
@login_required
@require_http_methods(["POST"])
@transaction.atomic
def submit_answer(request, student_test_id):
    st = get_object_or_404(TopicStudentTest, id=student_test_id, student=request.user)
    qid = int(request.POST.get('question_id'))
    q = get_object_or_404(TopicQuestion, id=qid)
    selected = request.POST.getlist('options')  # list of option IDs
    ans, _ = TopicStudentAnswer.objects.get_or_create(student_test=st, question=q)
    ans.selected_options.clear()
    chosen_options = TopicAnswerOption.objects.filter(id__in=selected, question=q)
    ans.selected_options.add(*chosen_options)
    # Scoring
    correct_ids = set(q.options.filter(is_correct=True).values_list('id', flat=True))
    chosen_ids = set(chosen_options.values_list('id', flat=True))
    if q.question_type == 'single':
        ans.is_correct = (len(chosen_ids) == 1 and chosen_ids == correct_ids)
    else:  # multi
        ans.is_correct = (chosen_ids == correct_ids)
    # Per-question score = total_score / question_count
    per_q = st.test.total_score / st.test.question_count if st.test.question_count else 0
    ans.score = per_q if ans.is_correct else 0
    ans.save()
    # update total
    agg = st.answers.aggregate(s=Sum('score'))
    st.total_score = agg['s'] or 0
    st.save()
    return JsonResponse({'correct': ans.is_correct, 'score': ans.score, 'total': st.total_score})

# ---------- Finish Test ----------
@login_required
@require_http_methods(["POST"])
@transaction.atomic
def finish_topic_test(request, student_test_id):
    st = get_object_or_404(TopicStudentTest, id=student_test_id, student=request.user)
    st.completed = True
    st.finished_at = timezone.now()
    st.save()
    return JsonResponse({'completed': True, 'total_score': st.total_score})

# ---------- Question detail (student fetch) ----------
@login_required
def topic_question_detail(request, question_id):
    q = get_object_or_404(TopicQuestion, id=question_id)
    # permission: ensure student belongs to group when student; teachers can view own topics
    if getattr(request.user, 'role', '') == 'student':
        if request.user.group_id != q.topic.group_id:
            return HttpResponseForbidden('Guruh mos emas')
    elif getattr(request.user, 'role', '') == 'teacher':
        if q.topic.created_by_id != request.user.id:
            return HttpResponseForbidden('Ruxsat yo\'q')
    data = {
        'id': q.id,
        'text': q.text,
        'question_type': q.question_type,
        'image': q.image.url if q.image else None,
        'options': [
            {'id': o.id, 'text': o.text}
            for o in q.options.all()
        ]
    }
    return JsonResponse(data)

# ---------- Video create/update ----------
@login_required
@teacher_required
@require_http_methods(["POST"])
@transaction.atomic
def save_topic_video(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id, created_by=request.user)
    video_url = request.POST.get('video_url')
    video_file = request.FILES.get('video_file')
    iv, _ = TopicIntroVideo.objects.get_or_create(topic=topic)
    if video_url:
        iv.video_url = video_url
    if video_file:
        iv.video_file = video_file
    iv.save()
    return JsonResponse({'ok': True, 'video_url': iv.video_url, 'has_file': bool(iv.video_file)})

# ---------- Get video info ----------
@login_required
@teacher_required
def get_topic_video(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id, created_by=request.user)
    if hasattr(topic, 'intro_video'):
        iv = topic.intro_video
        return JsonResponse({'video_url': iv.video_url, 'video_file': bool(iv.video_file)})
    return JsonResponse({'video_url': None, 'video_file': False})

# ---------- Delete video ----------
@login_required
@teacher_required
@require_http_methods(["POST"])
@transaction.atomic
def delete_topic_video(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id, created_by=request.user)
    if hasattr(topic, 'intro_video'):
        topic.intro_video.delete()
    return JsonResponse({'ok': True})

# ---------- Manage Topic (teacher UI) ----------
@login_required
@teacher_required
def topic_manage(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id, created_by=request.user)
    questions = topic.questions.prefetch_related('options').all()
    tests = topic.tests.all().order_by('-created_at')
    video = getattr(topic, 'intro_video', None)
    # Groups for multi-select (teacher may have access restrictions later; for now all groups)
    all_groups = Group.objects.all().order_by('name')
    return render(request, 'topic_panel/topic_manage.html', {
        'topic': topic,
        'questions': questions,
        'tests': tests,
        'video': video,
        'all_groups': all_groups,
    })

# ---------- Test Results (teacher) ----------
@login_required
@teacher_required
def topic_test_results(request, test_id):
    test = get_object_or_404(TopicTest, id=test_id, topic__created_by=request.user)
    # related_name on TopicStudentTest is 'student_runs'
    attempts = test.student_runs.select_related('student').all().order_by('-finished_at','-started_at')
    return render(request, 'topic_panel/test_results.html', {
        'test': test,
        'attempts': attempts
    })
