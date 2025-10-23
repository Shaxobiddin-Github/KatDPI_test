from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from main.models import StudentTest, Group, Bulim, Kafedra, User, Test, Subject
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Q, F, FloatField, ExpressionWrapper
from django.db.models.functions import Coalesce

@login_required
def participated_students_list(request):
    from main.models import StudentAnswer
    from django.db.models import Count, Case, When, F, FloatField, Value
    from django.db.models.functions import Cast
    from django.db.models import Count, Case, When, F, FloatField

    # Completed student tests with required relations
    student_tests = StudentTest.objects.filter(completed=True).select_related(
        'student', 'test', 'group', 'subject', 'semester', 'test__subject'
    ).prefetch_related('answers')

    # Compute per-stats for display (correct count and percent)
    from main.models import StudentAnswer
    for st in student_tests:
        answers = StudentAnswer.objects.filter(student_test=st)
        if st.question_ids:
            answers = answers.filter(question_id__in=st.question_ids)
        total = answers.count()
        correct = answers.filter(is_correct=True).count()
        st.total_answers = total
        st.correct_answers_count = correct
        st.percent_result = round((correct / total * 100), 1) if total > 0 else 0

    # Build subject -> group -> {passed: [st], failed: [st]}
    subject_data = {}
    for st in student_tests:
        # Subject resolution
        subj = st.subject or getattr(st.test, 'subject', None)
        if not subj:
            continue
        # Group resolution: prefer StudentTest.group, else if student's real group matches one of Test.groups
        grp = st.group
        if not grp:
            try:
                real_grp = getattr(st.student, 'group', None)
                if real_grp and st.test.groups.filter(id=real_grp.id).exists():
                    grp = real_grp
            except Exception:
                grp = st.group  # leave None
        if not grp:
            continue

        if subj not in subject_data:
            subject_data[subj] = {}
        if grp not in subject_data[subj]:
            subject_data[subj][grp] = {'passed': [], 'failed': []}

        if getattr(st, 'final_passed', False):
            subject_data[subj][grp]['passed'].append(st)
        else:
            subject_data[subj][grp]['failed'].append(st)

    return render(request, 'controller_panel/participated_students_list.html', {
        'subject_data': subject_data,
    })

@require_POST
@login_required
def allow_retake(request):
    stest_id = request.POST.get('stest_id')
    password = request.POST.get('password')
    if password != '96970204':
        return JsonResponse({'success': False, 'error': 'Parol noto‘g‘ri!'}, status=403)
    try:
        stest = StudentTest.objects.get(id=stest_id)
        stest.can_retake = True
        stest.save()
        return JsonResponse({'success': True})
    except StudentTest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Test topilmadi!'}, status=404)


@require_POST
@login_required
def allow_retake_bulk(request):
    ids_csv = request.POST.get('stest_ids', '')
    password = request.POST.get('password')
    if password != '96970204':
        return JsonResponse({'success': False, 'error': 'Parol noto‘g‘ri!'}, status=403)
    ids = [i for i in ids_csv.split(',') if i]
    updated = StudentTest.objects.filter(id__in=ids).update(can_retake=True)
    return JsonResponse({'success': True, 'updated': updated})


@require_POST
@login_required
def allow_retake_group(request):
    group_id = request.POST.get('group_id')
    password = request.POST.get('password')
    if password != '96970204':
        return JsonResponse({'success': False, 'error': 'Parol noto‘g‘ri!'}, status=403)
    if not group_id:
        return JsonResponse({'success': False, 'error': 'Guruh ID berilmadi'}, status=400)
    updated = StudentTest.objects.filter(group_id=group_id, completed=True).update(can_retake=True)
    return JsonResponse({'success': True, 'updated': updated})


@require_POST
@login_required
def allow_retake_group_subject(request):
    """Allow retake for all completed attempts within a specific group and subject."""
    group_id = request.POST.get('group_id')
    subject_id = request.POST.get('subject_id')
    password = request.POST.get('password')
    if password != '96970204':
        return JsonResponse({'success': False, 'error': 'Parol noto‘g‘ri!'}, status=403)
    if not group_id or not subject_id:
        return JsonResponse({'success': False, 'error': 'Guruh yoki fan ko\'rsatilmagan'}, status=400)
    # Include legacy and M2M-matched cases
    base_qs = StudentTest.objects.filter(completed=True).filter(
        Q(group_id=group_id, subject_id=subject_id)
        | Q(group_id=group_id, test__subject_id=subject_id)
        | (Q(group__isnull=True) & Q(student__group_id=group_id) & Q(test__groups__id=group_id) & Q(test__subject_id=subject_id))
    ).distinct()
    updated = base_qs.update(can_retake=True)
    return JsonResponse({'success': True, 'updated': updated})


@require_POST
@login_required
def allow_retake_group_subject_failed(request):
    """Allow retake for only failed attempts within a specific group and subject."""
    group_id = request.POST.get('group_id')
    subject_id = request.POST.get('subject_id')
    password = request.POST.get('password')
    if password != '96970204':
        return JsonResponse({'success': False, 'error': 'Parol noto‘g‘ri!'}, status=403)
    if not group_id or not subject_id:
        return JsonResponse({'success': False, 'error': 'Guruh yoki fan ko\'rsatilmagan'}, status=400)
    # Compute percent using overridden_score if present
    final_score = Coalesce(F('overridden_score'), F('total_score'))
    percent = ExpressionWrapper(final_score * 100.0 / F('test__total_score'), output_field=FloatField())
    qs = StudentTest.objects.filter(completed=True).filter(
        Q(group_id=group_id, subject_id=subject_id)
        | Q(group_id=group_id, test__subject_id=subject_id)
        | (Q(group__isnull=True) & Q(student__group_id=group_id) & Q(test__groups__id=group_id) & Q(test__subject_id=subject_id))
    ).annotate(percent=percent).filter(pass_override=False, test__total_score__gt=0, percent__lt=F('test__pass_percent')).distinct()
    updated = qs.update(can_retake=True)
    return JsonResponse({'success': True, 'updated': updated})
