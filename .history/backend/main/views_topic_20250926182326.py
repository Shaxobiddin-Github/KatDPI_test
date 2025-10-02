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
from django.contrib.auth import authenticate, login

# ---------- Student Simple Login (username only) ----------
def topic_student_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        user = authenticate(request, username=username, password=None)
        # If authenticate with no password not configured, fallback manual lookup (assuming already created users)
        if user is None:
            try:
                user = User.objects.get(username=username, role='student')
            except User.DoesNotExist:
                return render(request, 'topic_panel/student_login.html', {'error': 'Foydalanuvchi topilmadi'})
        if getattr(user, 'role', '') != 'student':
            return render(request, 'topic_panel/student_login.html', {'error': 'Talaba emas'})
        login(request, user)
        return redirect('topic:student_dashboard')
    return render(request, 'topic_panel/student_login.html')

# ---------- Student Dashboard (available tests) ----------
def topic_student_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('topic:student_login')
    if getattr(request.user, 'role', '') != 'student':
        return HttpResponseForbidden('Talaba emas')
    gid = request.user.group_id
    # Tests where this group explicitly assigned
    tests = TopicTest.objects.filter(groups__id=gid, is_published=True).select_related('topic').distinct().order_by('-created_at')
    # Build status info
    runs = {r.test_id: r for r in TopicStudentTest.objects.filter(student=request.user, test_id__in=tests.values_list('id', flat=True))}
    enriched = []
    for t in tests:
        run = runs.get(t.id)
        enriched.append({
            'obj': t,
            'attempt_id': run.id if run else None,
            'completed': run.completed if run else False,
            'score': run.total_score if run else None
        })
    student_full_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
    group_name = getattr(request.user.group, 'name', None)
    return render(request, 'topic_panel/student_dashboard.html', {
        'tests': enriched,
        'student_full_name': student_full_name,
        'student_group_name': group_name,
    })

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
    from .models import Subject
    topics = Topic.objects.filter(created_by=request.user).select_related('subject', 'group')
    subjects = Subject.objects.all().order_by('name')
    # Simple aggregates for header stats
    topic_ids = list(topics.values_list('id', flat=True))
    question_count = 0
    test_count = 0
    if topic_ids:
        question_count = TopicQuestion.objects.filter(topic_id__in=topic_ids).count()
        test_count = TopicTest.objects.filter(topic_id__in=topic_ids).count()
    ctx = {
        'topics': topics,
        'subjects': subjects,
        'teacher_full_name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
        'teacher_username': request.user.username,
        'agg_questions': question_count,
        'agg_tests': test_count,
        'agg_topics': len(topic_ids),
    }
    return render(request, 'topic_panel/dashboard.html', ctx)

# Safe wrapper for mixed role accidental access
def topic_dashboard_entry(request):
    if not request.user.is_authenticated:
        return redirect('/api/login/?next=/api/topic-panel/dashboard/')
    role = getattr(request.user, 'role', '')
    if role == 'student':
        return redirect('topic:student_dashboard')
    if role == 'teacher':
        return topic_dashboard(request)
    return HttpResponseForbidden('Ruxsat yo\'q')

# ---------- Create Topic ----------
@login_required
@teacher_required
@require_http_methods(["POST"])
@transaction.atomic
def create_topic(request):
    subject_id = request.POST.get('subject_id')
    title = request.POST.get('title')
    description = request.POST.get('description')
    if not (subject_id and title):
        return JsonResponse({'error': 'Fan va sarlavha majburiy'}, status=400)
    # Graceful validation to avoid returning full 404 HTML page
    try:
        subject_id_int = int(subject_id)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Subject ID noto\'g\'ri'}, status=400)
    subject = Subject.objects.filter(id=subject_id_int).first()
    if not subject:
        return JsonResponse({'error': 'Subject topilmadi'}, status=400)
    topic = Topic.objects.create(subject=subject, title=title, description=description or '', created_by=request.user)
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
    if not raw_group_ids:
        return JsonResponse({'error': 'Kamida bitta guruh tanlang'}, status=400)
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
        if not valid_groups.exists():
            return JsonResponse({'error': 'Tanlangan guruh topilmadi'}, status=400)
        test.groups.set(valid_groups)
    return JsonResponse({'id': test.id, 'title': test.title})

# ---------- Start Test (student gating) ----------
@login_required
def start_topic_test(request, test_id):
    test = get_object_or_404(TopicTest, id=test_id)
    if getattr(request.user, 'role', '') != 'student':
        return HttpResponseForbidden('Talaba emas')
    # Group check: ONLY explicitly assigned groups (topic.group not automatic anymore)
    assigned_ids = set(test.groups.values_list('id', flat=True))
    if request.user.group_id not in assigned_ids:
        return HttpResponseForbidden('Bu test siz uchun emas (guruh kiritilmagan)')
    # Pre-video gating
    if hasattr(test.topic, 'intro_video') and not request.session.get(f'topic_video_seen_{test.id}'):
        iv = test.topic.intro_video
        embed_url = None
        if iv.video_url:
            raw = iv.video_url.strip()
            # Convert common YouTube URL formats to embed form
            # Examples handled: https://www.youtube.com/watch?v=ID , https://youtu.be/ID , embed already
            import re
            yt_id = None
            patterns = [
                r'youtube\.com/watch\?v=([A-Za-z0-9_-]{6,})',
                r'youtu\.be/([A-Za-z0-9_-]{6,})',
                r'youtube\.com/embed/([A-Za-z0-9_-]{6,})'
            ]
            for p in patterns:
                m = re.search(p, raw)
                if m:
                    yt_id = m.group(1)
                    break
            if yt_id:
                embed_url = f'https://www.youtube.com/embed/{yt_id}?rel=0&modestbranding=1'
            else:
                # If direct mp4 link or unrecognized, let template try raw in iframe (may fail) or fallback below
                embed_url = raw
        return render(request, 'topic_panel/pre_video.html', {'test': test, 'video': iv, 'embed_url': embed_url})
    # Create or reuse student test
    st, created = TopicStudentTest.objects.get_or_create(student=request.user, test=test)
    if created or not st.randomized_question_ids:
        base_ids = list(test.question_ids)
        # Apply block shuffle if configured
        if test.shuffle_questions and base_ids:
            if test.question_block_size and test.question_block_size > 0:
                block = test.question_block_size
                shuffled = []
                for i in range(0, len(base_ids), block):
                    seg = base_ids[i:i+block]
                    random.shuffle(seg)
                    shuffled.extend(seg)
                base_ids = shuffled
            else:
                random.shuffle(base_ids)
        st.randomized_question_ids = base_ids
        st.save()
    duration_seconds = int(test.duration.total_seconds()) if test.duration else 0
    # Remaining seconds (in case student re-enters)
    remaining = None
    if st.started_at and test.duration:
        elapsed = (timezone.now() - st.started_at).total_seconds()
        remaining = max(0, duration_seconds - int(elapsed))
    return render(request, 'topic_panel/test_run.html', {'test': test, 'student_test': st, 'duration_seconds': remaining if remaining is not None else duration_seconds})

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
    # Enforce time expiry before accepting answers
    test = st.test
    if test.duration and st.started_at:
        elapsed = (timezone.now() - st.started_at).total_seconds()
        if elapsed > test.duration.total_seconds():
            if not st.completed:
                st.completed = True
                st.finished_at = timezone.now()
                st.save(update_fields=['completed', 'finished_at'])
            return JsonResponse({'error': 'Vaqt tugagan'}, status=403)
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
    # If time expired, still mark completed
    test = st.test
    if test.duration and st.started_at:
        elapsed = (timezone.now() - st.started_at).total_seconds()
        if elapsed > test.duration.total_seconds():
            if not st.completed:
                st.completed = True
                st.finished_at = st.started_at + test.duration
                st.save(update_fields=['completed', 'finished_at'])
    if not st.completed:
        st.completed = True
        st.finished_at = timezone.now()
        st.save(update_fields=['completed', 'finished_at'])
    # Stats
    total_q = len(st.test.question_ids)
    answered = st.answers.count()
    correct = st.answers.filter(is_correct=True).count()
    incorrect = answered - correct
    unanswered = total_q - answered
    return JsonResponse({
        'completed': True,
        'total_score': st.total_score,
        'total_questions': total_q,
        'answered': answered,
        'correct': correct,
        'incorrect': incorrect,
        'unanswered': unanswered
    })

# ---------- Question detail (student fetch) ----------
@login_required
def topic_question_detail(request, question_id):
    q = get_object_or_404(TopicQuestion, id=question_id)
    # permission: ensure student belongs to group when student; teachers can view own topics
    if getattr(request.user, 'role', '') == 'student':
        gid = request.user.group_id
        # Fast path: if student has an active TopicStudentTest whose test contains this question id
        active_run = TopicStudentTest.objects.filter(student=request.user, test__groups__id=gid).first()
        allowed = False
        if active_run and q.id in active_run.test.question_ids:
            allowed = True
        else:
            # Fallback: scan tests for this group containing q.id in question_ids list
            for t in TopicTest.objects.filter(groups__id=gid).only('id','question_ids'):
                if q.id in t.question_ids:
                    allowed = True
                    break
        if not allowed:
            return HttpResponseForbidden('Guruh mos emas')
    elif getattr(request.user, 'role', '') == 'teacher':
        if q.topic.created_by_id != request.user.id:
            return HttpResponseForbidden('Ruxsat yo\'q')
    # Option shuffling if the owning test has shuffle_options enabled.
    # We detect current active student test for this question (if any) to decide.
    opt_list = list(q.options.all())
    if getattr(request.user, 'role', '') == 'student':
        active_run = TopicStudentTest.objects.filter(student=request.user, test__question_ids__contains=[q.id]).order_by('-started_at').first()
        if active_run and active_run.test.shuffle_options:
            random.shuffle(opt_list)
    data = {
        'id': q.id,
        'text': q.text,
        'question_type': q.question_type,
        'image': q.image.url if q.image else None,
        'options': [
            {'id': o.id, 'text': o.text}
            for o in opt_list
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

# ---------- Topic Stats (AJAX) ----------
@login_required
@teacher_required
def topic_stats(request, topic_id):
    """Return aggregated statistics for a topic via JSON.
    Counts questions, tests, attempts, and average score across completed attempts.
    """
    topic = get_object_or_404(Topic, id=topic_id, created_by=request.user)
    question_count = topic.questions.count()
    test_count = topic.tests.count()
    runs = TopicStudentTest.objects.filter(test__topic=topic, completed=True)
    attempts = runs.count()
    avg_score = None
    if attempts:
        from django.db.models import Sum
        total_score = runs.aggregate(s=Sum('total_score'))['s'] or 0
        avg_score = round(total_score / attempts, 2)
    return JsonResponse({
        'topic_id': topic.id,
        'title': topic.title,
        'questions': question_count,
        'tests': test_count,
        'attempts': attempts,
        'avg_score': avg_score,
    })

# ---------- Update / Delete Question ----------
@login_required
@teacher_required
@require_http_methods(["POST"])
@transaction.atomic
def update_topic_question(request, topic_id, question_id):
    topic = get_object_or_404(Topic, id=topic_id, created_by=request.user)
    q = get_object_or_404(TopicQuestion, id=question_id, topic=topic)
    text = request.POST.get('text')
    qtype = request.POST.get('question_type')
    if text:
        q.text = text
    if qtype in ['single','multi']:
        q.question_type = qtype
    # Option updates: existing options come as option_<id>=text and correct_<id>=on, plus new_option_text_N
    # Collect existing options
    existing_options = {o.id: o for o in q.options.all()}
    # Track correct count
    correct_count = 0
    for oid, opt in existing_options.items():
        new_text = request.POST.get(f'option_{oid}')
        delete_flag = request.POST.get(f'delete_{oid}')
        if delete_flag == '1':
            opt.delete()
            continue
        if new_text:
            opt.text = new_text
        is_corr = request.POST.get(f'correct_{oid}') == 'on'
        opt.is_correct = is_corr
        if is_corr:
            correct_count += 1
        opt.save()
    # New options pattern: new_option_text_X with new_option_correct_X
    index = 1
    while True:
        ntxt = request.POST.get(f'new_option_text_{index}')
        if not ntxt:
            break
        is_corr = request.POST.get(f'new_option_correct_{index}') == 'on'
        o = TopicAnswerOption.objects.create(question=q, text=ntxt, is_correct=is_corr)
        if is_corr:
            correct_count += 1
        index += 1
    # Re-evaluate correctness constraints
    if q.question_type == 'single':
        # Ensure exactly one correct, else invalidate by picking first correct or set first option correct
        corrects = list(q.options.filter(is_correct=True))
        if len(corrects) != 1 and corrects:
            # Keep only first correct
            for extra in corrects[1:]:
                extra.is_correct = False
                extra.save()
        elif len(corrects) == 0:
            first = q.options.first()
            if first:
                first.is_correct = True
                first.save()
    else:  # multi
        # At least 2 correct; if not, mark first two
        corrects = list(q.options.filter(is_correct=True))
        if len(corrects) < 2:
            all_opts = list(q.options.all())
            for idx,opt in enumerate(all_opts):
                opt.is_correct = (idx < 2)
                opt.save()
    q.save()
    return JsonResponse({'ok': True, 'id': q.id})

@login_required
@teacher_required
@require_http_methods(["POST"])
@transaction.atomic
def delete_topic_question(request, topic_id, question_id):
    topic = get_object_or_404(Topic, id=topic_id, created_by=request.user)
    q = get_object_or_404(TopicQuestion, id=question_id, topic=topic)
    q.delete()
    return JsonResponse({'ok': True})

# ---------- Update / Delete Test ----------
@login_required
@teacher_required
@require_http_methods(["POST"])
@transaction.atomic
def update_topic_test(request, topic_id, test_id):
    topic = get_object_or_404(Topic, id=topic_id, created_by=request.user)
    test = get_object_or_404(TopicTest, id=test_id, topic=topic)
    title = request.POST.get('title')
    total_score = request.POST.get('total_score')
    duration_minutes = request.POST.get('duration_minutes')
    is_published = request.POST.get('is_published')
    changed = []
    if title:
        test.title = title; changed.append('title')
    if total_score:
        try:
            test.total_score = int(total_score); changed.append('total_score')
        except ValueError:
            pass
    if duration_minutes:
        try:
            from datetime import timedelta
            test.duration = timedelta(minutes=int(duration_minutes)); changed.append('duration')
        except ValueError:
            pass
    if is_published is not None:
        test.is_published = (is_published == '1'); changed.append('is_published')
    # Optional reassign groups: group_ids repeated
    group_ids = request.POST.getlist('group_ids')
    if group_ids:
        from .models import Group
        groups = Group.objects.filter(id__in=group_ids)
        if groups.exists():
            test.groups.set(groups)
            changed.append('groups')
    test.save()
    return JsonResponse({'ok': True, 'id': test.id, 'changed': changed})

@login_required
@teacher_required
@require_http_methods(["POST"])
@transaction.atomic
def delete_topic_test(request, topic_id, test_id):
    topic = get_object_or_404(Topic, id=topic_id, created_by=request.user)
    test = get_object_or_404(TopicTest, id=test_id, topic=topic)
    # Prevent deleting if students already attempted? (Optional) For now allow.
    test.delete()
    return JsonResponse({'ok': True})

# ---------- Remaining Time (AJAX) ----------
@login_required
def test_remaining_time(request, student_test_id):
    st = get_object_or_404(TopicStudentTest, id=student_test_id, student=request.user)
    test = st.test
    remaining = None
    if test.duration and st.started_at:
        total = test.duration.total_seconds()
        elapsed = (timezone.now() - st.started_at).total_seconds()
        remaining = max(0, int(total - elapsed))
        if remaining == 0 and not st.completed:
            st.completed = True
            st.finished_at = st.started_at + test.duration
            st.save(update_fields=['completed', 'finished_at'])
    return JsonResponse({'remaining_seconds': remaining})
