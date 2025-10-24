from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from main.models import StudentTest, Group, Bulim, Kafedra, User, Test, Subject
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Q, F, FloatField, ExpressionWrapper
from django.db.models.functions import Coalesce
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Table, TableStyle
from django.http import HttpResponse
import io

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
            subject_data[subj][grp] = {'passed': [], 'failed': [], 'not_participated': []}

        if getattr(st, 'final_passed', False):
            subject_data[subj][grp]['passed'].append(st)
        else:
            subject_data[subj][grp]['failed'].append(st)

    # After collecting passed/failed, compute not_participated per (subject, group)
    for subj, groups in list(subject_data.items()):
        for grp, buckets in list(groups.items()):
            participant_ids = {st.student_id for st in buckets['passed']} | {st.student_id for st in buckets['failed']}
            # Only consider students in this group
            group_students_qs = User.objects.filter(role='student', group=grp).only('id', 'first_name', 'last_name', 'username', 'access_code')
            not_parts = group_students_qs.exclude(id__in=participant_ids).order_by('last_name', 'first_name')
            # Store as list for template
            buckets['not_participated'] = list(not_parts)

    # All groups for top-level PDF export selector
    all_groups = Group.objects.all().order_by('name')
    return render(request, 'controller_panel/participated_students_list.html', {
        'subject_data': subject_data,
        'all_groups': all_groups,
    })


@login_required
def export_failed_pdf(request):
    """
    Bitta PDF eksport: tanlangan guruh uchun (ixtiyoriy fan bo'yicha) ikki xil ko'rinishda yuklash:
    - mode=access (default): Yiqilganlar + Qatnashmaganlar ro'yxati, access kodlari bilan.
    - mode=vedomost: Bitta jadvalda (yiqilgan + qatnashmagan) ism-familiya, semestr, 'Qayta topshirish' (yiqilgan=2, qatnashmagan="1 qayta"), 'Ball' (bo'sh).

    GET params:
      - group_id (required)
      - subject_id (optional)
      - mode: 'access' | 'vedomost'
    """

    group_id = request.GET.get('group_id')
    subject_id = request.GET.get('subject_id')
    mode = request.GET.get('mode') or request.GET.get('format') or 'access'
    if not group_id:
        return HttpResponse('group_id is required', status=400)

    try:
        group = Group.objects.get(id=group_id)
    except Group.DoesNotExist:
        return HttpResponse('Group not found', status=404)

    # Build base queryset of completed attempts for this group (+subject if provided)
    base = StudentTest.objects.filter(completed=True).filter(
        Q(group_id=group.id)
        | (Q(group__isnull=True) & Q(student__group_id=group.id) & Q(test__groups__id=group.id))
    )
    if subject_id:
        base = base.filter(Q(subject_id=subject_id) | Q(test__subject_id=subject_id))

    # Compute percent and filter failed only
    final_score = Coalesce(F('overridden_score'), F('total_score'))
    percent = ExpressionWrapper(final_score * 100.0 / F('test__total_score'), output_field=FloatField())
    failed_qs = base.annotate(percent=percent).filter(
        pass_override=False,
        test__total_score__gt=0,
        percent__lt=F('test__pass_percent')
    ).select_related('student', 'test', 'test__subject', 'semester').order_by('student__id', '-end_time', '-start_time')

    # Deduplicate: latest attempt per student (if subject filtered),
    # or latest per (student, subject) when exporting all subjects.
    unique_map = {}
    for st in failed_qs:
        resolved_subject = getattr(getattr(st.test, 'subject', None) or st.subject, 'id', None)
        if subject_id:
            key = (st.student_id,)
        else:
            key = (st.student_id, resolved_subject)
        prev = unique_map.get(key)

        def ts(x):
            return (x.end_time or x.start_time)

        if not prev or (ts(st) and ts(prev) and ts(st) > ts(prev)):
            unique_map[key] = st

    unique_failed = list(unique_map.values())
    unique_failed.sort(key=lambda st: (
        (st.student.last_name or '').lower(),
        (st.student.first_name or '').lower(),
        st.student.username or ''
    ))

    # Compute NOT PARTICIPATED list for the same scope (group [+ subject])
    group_students = User.objects.filter(role='student', group=group).only('id', 'first_name', 'last_name', 'username', 'access_code', 'middle_name')
    participants_qs = StudentTest.objects.filter(completed=True).filter(
        Q(group_id=group.id)
        | (Q(group__isnull=True) & Q(student__group_id=group.id) & Q(test__groups__id=group.id))
    )
    if subject_id:
        participants_qs = participants_qs.filter(Q(subject_id=subject_id) | Q(test__subject_id=subject_id))
    participant_ids = participants_qs.values_list('student_id', flat=True).distinct()
    not_part_qs = group_students.exclude(id__in=participant_ids).order_by('last_name', 'first_name')
    not_part = list(not_part_qs)

    # PDF build common header
    buffer = io.BytesIO()
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20, rightMargin=20, topMargin=36, bottomMargin=20)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('title', parent=styles['Title'], alignment=TA_CENTER, fontSize=14, spaceAfter=8)
    normal_style = ParagraphStyle('normal', parent=styles['Normal'], alignment=TA_LEFT, fontSize=10, spaceAfter=2)
    elements = []

    # Access mode: two tables (failed + not participated) with access codes
    if mode == 'access':
        from reportlab.platypus import Table, TableStyle
        elements.append(Paragraph("Yiqilgan va qatnashmagan talabalar (Access kodi bilan)", title_style))
        elements.append(Paragraph(f"Guruh: {group.name}", normal_style))
        subj = None
        if subject_id:
            try:
                subj = Subject.objects.get(id=subject_id)
                elements.append(Paragraph(f"Fan: {subj.name}", normal_style))
            except Subject.DoesNotExist:
                subj = None
        elements.append(Spacer(1, 8))

        # Failed table: only name and access code
        data_failed = [['№', 'Familiya, Ism', 'Access code']]
        idx = 1
        for st in unique_failed:
            s = st.student
            fio = f"{(s.last_name or '').upper()} {(s.first_name or '').title()}".strip()
            data_failed.append([str(idx), fio, (s.access_code or '')])
            idx += 1

        table_failed = Table(data_failed, repeatRows=1, colWidths=[12*mm, 95*mm, 35*mm])
        table_failed.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 12),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('GRID', (0,0), (-1,-1), 0.7, colors.grey),
            ('ALIGN', (0,0), (0,-1), 'CENTER'),
            ('ALIGN', (2,1), (2,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTSIZE', (0,1), (-1,-1), 11),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.whitesmoke, colors.white]),
        ]))
        elements.append(table_failed)

        # Not participated section
        elements.append(Spacer(1, 16))
        elements.append(Paragraph("Qatnashmagan talabalar", title_style))
        elements.append(Paragraph(
            f"Guruh: {group.name}" + (f", Fan: {subj.name}" if subject_id and subj else ''),
            normal_style
        ))
        # Not participated: only name and access code
        data_np = [['№', 'Familiya, Ism', 'Access code']]
        idx = 1
        for u in not_part:
            fio = f"{(u.last_name or '').upper()} {(u.first_name or '').title()}".strip()
            data_np.append([str(idx), fio, (u.access_code or '')])
            idx += 1
        table_np = Table(data_np, repeatRows=1, colWidths=[12*mm, 95*mm, 35*mm])
        table_np.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 12),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('GRID', (0,0), (-1,-1), 0.7, colors.grey),
            ('ALIGN', (0,0), (0,-1), 'CENTER'),
            ('ALIGN', (2,1), (2,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTSIZE', (0,1), (-1,-1), 11),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.whitesmoke, colors.white]),
        ]))
        elements.append(table_np)

        title_suffix = 'access'

    else:  # vedomost mode
        from reportlab.platypus import Table, TableStyle
        elements.append(Paragraph("Vedomost (Qayta topshirish ro'yxati)", title_style))
        elements.append(Paragraph(f"Guruh: {group.name}", normal_style))
        subj = None
        if subject_id:
            try:
                subj = Subject.objects.get(id=subject_id)
                elements.append(Paragraph(f"Fan: {subj.name}", normal_style))
            except Subject.DoesNotExist:
                subj = None
        elements.append(Spacer(1, 8))

        # Prepare combined rows: failed -> retake=2, not participated -> retake='1 qayta'
        data_v = [['№', 'Familiya, Ism', 'Otasining ismi', 'Semestr', 'Qayta topshirish', 'Ball', 'Talaba imzosi']]
        idx = 1
        for st in unique_failed:
            s = st.student
            fio = f"{(s.last_name or '').upper()} {(s.first_name or '').title()}".strip()
            middle = getattr(s, 'middle_name', '') or ''
            sem = getattr(getattr(st, 'semester', None), 'number', '-')
            data_v.append([str(idx), fio, middle, str(sem), '2', '', ''])
            idx += 1

        # Derive semester for non-participants when possible: prefer majority/first from failed
        sem_for_np = '-'
        try:
            sem_list = [getattr(getattr(st, 'semester', None), 'number', None) for st in unique_failed]
            sem_list = [s for s in sem_list if s is not None]
            if sem_list:
                # Choose the most common semester among failed, or first
                from collections import Counter
                sem_for_np = str(Counter(sem_list).most_common(1)[0][0])
            else:
                any_st = base.exclude(semester__isnull=True).first()
                if any_st and getattr(any_st.semester, 'number', None) is not None:
                    sem_for_np = str(any_st.semester.number)
        except Exception:
            pass

        for u in not_part:
            fio = f"{(u.last_name or '').upper()} {(u.first_name or '').title()}".strip()
            middle = getattr(u, 'middle_name', '') or ''
            data_v.append([str(idx), fio, middle, sem_for_np, '1', '', ''])
            idx += 1

        table_v = Table(data_v, repeatRows=1)
        table_v.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ALIGN', (0,0), (0,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTSIZE', (0,1), (-1,-1), 9),
        ]))
        elements.append(table_v)
        title_suffix = 'vedomost'

    # Build and return
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    resp = HttpResponse(pdf, content_type='application/pdf')
    base_name = f"{title_suffix}_{group.name}"
    if subject_id:
        base_name += f"_subject_{subject_id}"
    resp['Content-Disposition'] = f'attachment; filename="{base_name}.pdf"'
    return resp

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
