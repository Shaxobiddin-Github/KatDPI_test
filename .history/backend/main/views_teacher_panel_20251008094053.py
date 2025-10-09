from django.shortcuts import render, redirect, get_object_or_404
from main.models import Subject, Group, Faculty, University, Question, AnswerOption, Semester, GroupSubject
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.http import JsonResponse

@login_required
def teacher_help(request):
    login_redirect = login_check(request)
    if login_redirect:
        return login_redirect
    return render(request, 'teacher_panel/help.html')
@require_GET
def get_subjects_by_group_semester(request):
    group_id = request.GET.get('group_id')
    semester_id = request.GET.get('semester_id')
    subjects = []
    if group_id and semester_id:
        group_ids = [gid for gid in str(group_id).split(',') if gid]
        group_subjects = GroupSubject.objects.filter(
            group_id__in=group_ids,
            semester_id=semester_id
        ).select_related('subject')
        seen = set()
        for gs in group_subjects:
            if gs.subject_id in seen:
                continue
            seen.add(gs.subject_id)
            subjects.append({'id': gs.subject.id, 'name': gs.subject.name})
    return JsonResponse({'subjects': subjects})

@login_required
def teacher_logout(request):
    logout(request)
    return redirect('/api/login/')

def login_check(request):
    if not request.user.is_authenticated:
        return redirect('/api/login/')
    return None

# Edit question view (real form)
@login_required
def edit_question(request, question_id):
    login_redirect = login_check(request)
    if login_redirect:
        return login_redirect
    question = get_object_or_404(Question, id=question_id, created_by=request.user)
    faculties = Faculty.objects.all()
    groups = Group.objects.all()
    subjects = Subject.objects.all()
    semesters = Semester.objects.all()
    # 'sentence_ordering' vaqtincha yashiriladi
    question_types = [qt for qt in Question.QUESTION_TYPE_CHOICES if qt[0] != 'sentence_ordering']
    selected = {
        'faculty': getattr(question.subject, 'faculty_id', ''),
        'group': '',
        'semester': getattr(question, 'semester_id', ''),
        'subject': question.subject.id,
        'question_type': question.question_type,
    }
    answer_options = list(question.answer_options.all())
    if request.method == 'POST':
        text = request.POST.get('text')
        subject_id = request.POST.get('subject')
        question_type = request.POST.get('question_type')
        group_id = request.POST.get('group')
        semester = request.POST.get('semester')
        selected = {
            'faculty': request.POST.get('faculty', ''),
            'group': group_id,
            'semester': semester,
            'subject': subject_id,
            'question_type': question_type,
        }
        subject = Subject.objects.get(id=subject_id)
        question.text = text
        question.subject = subject
        question.question_type = question_type
        # Persist semester when provided (student context)
        if semester:
            try:
                question.semester_id = int(semester)
            except ValueError:
                pass
        question.save()
        question.answer_options.all().delete()
        if question_type == 'single_choice':
            for i in range(1, 25):  # allow more dynamic additions
                option_text = request.POST.get(f'single_option_{i}')
                option_image = request.FILES.get(f'single_image_{i}')
                if option_text or option_image:
                    is_correct = (request.POST.get('single_correct') == str(i))
                    AnswerOption.objects.create(
                        question=question,
                        text=option_text or '',
                        is_correct=is_correct,
                        image=option_image if option_image else None
                    )
                else:
                    # stop only after initial 4? better: continue scanning until 24 to catch sparse indexes
                    continue
        elif question_type == 'multiple_choice':
            for i in range(1, 25):
                option_text = request.POST.get(f'multi_option_{i}')
                option_image = request.FILES.get(f'multi_image_{i}')
                if option_text or option_image:
                    is_correct = bool(request.POST.get(f'multi_correct_{i}'))
                    AnswerOption.objects.create(
                        question=question,
                        text=option_text or '',
                        is_correct=is_correct,
                        image=option_image if option_image else None
                    )
                else:
                    continue
        elif question_type == 'fill_in_blank':
            answer = request.POST.get('fill_blank_answer')
            if answer:
                AnswerOption.objects.create(question=question, text=answer, is_correct=True)
        elif question_type == 'true_false':
            answer = request.POST.get('true_false_answer')
            AnswerOption.objects.create(question=question, text=answer, is_correct=(answer == 'true'))
        elif question_type == 'matching':
            i = 1
            while True:
                left = request.POST.get(f'matching_left_{i}')
                right = request.POST.get(f'matching_right_{i}')
                if left or right:
                    if left and right:
                        AnswerOption.objects.create(question=question, left=left, right=right, is_correct=True)
                    i += 1
                else:
                    break
        elif question_type == 'sentence_ordering':
            for i in range(1, 5):
                order_text = request.POST.get(f'ordering_{i}')
                if order_text:
                    AnswerOption.objects.create(question=question, text=order_text, is_correct=True)
        return redirect('teacher_dashboard')
    return render(request, 'teacher_panel/add_question.html', {
        'subjects': subjects,
        'faculties': faculties,
        'groups': groups,
        'semesters': semesters,
        'question_types': question_types,
        'selected': selected,
        'edit_mode': True,
        'question': question,
        'answer_options': answer_options,
    })

# Delete question view
@login_required
def delete_question(request, question_id):
    login_redirect = login_check(request)
    if login_redirect:
        return login_redirect
    question = get_object_or_404(Question, id=question_id, created_by=request.user)
    question.delete()
    return redirect('teacher_dashboard')

@login_required
def teacher_dashboard(request):
    login_redirect = login_check(request)
    if login_redirect:
        return login_redirect
    if not hasattr(request.user, 'role') or request.user.role != 'teacher':
        return redirect('/api/login/')
    # Endi guruh+fan+semestr bo'yicha bo'linadi (group None bo'lsa alohida ko'rsatish)
    questions = (
        Question.objects
        .filter(created_by=request.user)
        .select_related('subject', 'semester', 'group')
        .order_by('group__name', 'subject__name', 'semester__number', 'created_at')
    )

    grouped = {}
    for q in questions:
        key = (q.group_id, q.subject_id, q.semester_id)
        if key not in grouped:
            grouped[key] = {
                'group': q.group,  # None bo'lsa global eski
                'subject': q.subject,
                'semester': q.semester,
                'accordion_id': f"{q.group_id or 'global'}-{q.subject_id}-{q.semester_id or 'none'}",
                'questions': []
            }
        grouped[key]['questions'].append(q)

    blocks = list(grouped.values())
    return render(request, 'teacher_panel/dashboard.html', {'group_subject_semesters': blocks})


from main.models import Kafedra, Bulim

@login_required
def add_question(request):
    login_redirect = login_check(request)
    if login_redirect:
        return login_redirect
    if not hasattr(request.user, 'role') or request.user.role != 'teacher':
        return redirect('/api/login/')
    target = request.GET.get('target', 'student')
    context = {'question_types': [qt for qt in Question.QUESTION_TYPE_CHOICES if qt[0] != 'sentence_ordering'], 'selected': {}, 'target': target}
    # Only subject + semester (for student path) – groups removed per new TZ
    if target == 'student':
        context['semesters'] = Semester.objects.all()
        # Dynamic subjects filtered by semester if possible (through GroupSubject indirectly) – fallback all
        semester_id = request.GET.get('semester') or request.POST.get('semester')
        if semester_id:
            # Collect subjects that appear in any GroupSubject for this semester (teacher can add generic question not tied to group)
            subject_ids = GroupSubject.objects.filter(semester_id=semester_id).values_list('subject_id', flat=True).distinct()
            context['subjects'] = Subject.objects.filter(id__in=subject_ids) if subject_ids else Subject.objects.all()
        else:
            context['subjects'] = Subject.objects.all()
    elif target == 'tutor':
        from main.models import Kafedra
        context['subjects'] = Subject.objects.all()
    elif target == 'employee':
        from main.models import Bulim
        context['subjects'] = Subject.objects.all()
    else:
        context['semesters'] = Semester.objects.all()
        context['subjects'] = Subject.objects.all()
        context['target'] = 'student'
    if request.method == 'POST':
        text = request.POST.get('text')
        subject_id = request.POST.get('subject')
        question_type = request.POST.get('question_type')
        semester_id_val = request.POST.get('semester') if target == 'student' else None
        kafedra_id_val = request.POST.get('kafedra') if target == 'tutor' else None
        bulim_id_val = request.POST.get('bulim') if target == 'employee' else None
        context['selected'] = {
            'subject': subject_id,
            'question_type': question_type,
            'semester': semester_id_val,
            'kafedra': kafedra_id_val,
            'bulim': bulim_id_val,
        }
        error = None
        if not text or not subject_id or not question_type:
            error = "Barcha maydonlarni to‘ldiring!"
        if target == 'student' and not semester_id_val:
            error = "Semestrni tanlang!"
        if target == 'tutor' and not kafedra_id_val:
            error = "Kafedrani tanlang!"
        if target == 'employee' and not bulim_id_val:
            error = "Bo'limni tanlang!"
        if error:
            context['error'] = error
            return render(request, 'teacher_panel/add_question.html', context)
        subject = Subject.objects.get(id=subject_id)
        question_image = request.FILES.get('question_image')
        try:
            q_local = Question.objects.create(
                text=text,
                subject=subject,
                question_type=question_type,
                created_by=request.user,
                image=question_image if question_image else None,
                semester_id=int(semester_id_val) if semester_id_val else None,
                kafedra_id=int(kafedra_id_val) if kafedra_id_val else None,
                bulim_id=int(bulim_id_val) if bulim_id_val else None,
                group_id=None
            )
        except Exception as e:
            context['error'] = f"Saqlashda xatolik: {e}"
            return render(request, 'teacher_panel/add_question.html', context)
        # Answers
        if question_type == 'single_choice':
            for i in range(1, 25):
                option_text = request.POST.get(f'single_option_{i}')
                option_image = request.FILES.get(f'single_image_{i}')
                if option_text or option_image:
                    is_correct = (request.POST.get('single_correct') == str(i))
                    AnswerOption.objects.create(question=q_local, text=option_text or '', is_correct=is_correct, image=option_image if option_image else None)
        elif question_type == 'multiple_choice':
            for i in range(1, 25):
                option_text = request.POST.get(f'multi_option_{i}')
                option_image = request.FILES.get(f'multi_image_{i}')
                if option_text or option_image:
                    is_correct = bool(request.POST.get(f'multi_correct_{i}'))
                    AnswerOption.objects.create(question=q_local, text=option_text or '', is_correct=is_correct, image=option_image if option_image else None)
        elif question_type == 'fill_in_blank':
            answer = request.POST.get('fill_blank_answer')
            if answer:
                AnswerOption.objects.create(question=q_local, text=answer, is_correct=True)
        elif question_type == 'true_false':
            answer = request.POST.get('true_false_answer')
            AnswerOption.objects.create(question=q_local, text=answer, is_correct=(answer == 'true'))
        elif question_type == 'matching':
            i = 1
            while True:
                left = request.POST.get(f'matching_left_{i}')
                right = request.POST.get(f'matching_right_{i}')
                image = request.FILES.get(f'matching_image_{i}')
                if left or right or image:
                    AnswerOption.objects.create(question=q_local, left=left or '', right=right or '', image=image if image else None, is_correct=True)
                    i += 1
                else:
                    break
        elif question_type == 'sentence_ordering':
            for i in range(1, 5):
                order_text = request.POST.get(f'ordering_{i}')
                if order_text:
                    AnswerOption.objects.create(question=q_local, text=order_text, is_correct=True)
        context['success'] = "Savol muvaffaqiyatli qo'shildi (guruhsiz)."
        return render(request, 'teacher_panel/add_question.html', context)
    return render(request, 'teacher_panel/add_question.html', context)
