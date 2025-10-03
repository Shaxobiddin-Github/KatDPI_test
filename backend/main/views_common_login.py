
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
@login_required
def common_logout(request):
    logout(request)
    return redirect('common_login')

from main.models import Test

# Tutor dashboard view
@login_required
def tutor_dashboard(request):
    # Tutor o‘z kafedrasiga tegishli testlarni ko‘radi
    from django.utils import timezone
    tests = []
    test_statuses = {}
    completed_tests = 0
    if request.user.kafedra:
        now = timezone.now()
        tests = [test for test in Test.objects.filter(kafedra=request.user.kafedra, active=True) if not test.end_time or now <= test.end_time]
        from main.models import StudentTest
        for test in tests:
            st = StudentTest.objects.filter(test=test, student=request.user).first()
            if st:
                test_statuses[test.id] = 'qatnashgansiz'
                if st.completed:
                    completed_tests += 1
            else:
                test_statuses[test.id] = 'yangi test'
    return render(request, 'tutor_panel/dashboard.html', {'tests': tests, 'test_statuses': test_statuses, 'completed_tests': completed_tests})

# Employee dashboard view
@login_required
def employee_dashboard(request):
    # Xodim o‘z bo‘limiga tegishli testlarni ko‘radi
    from django.utils import timezone
    tests = []
    test_statuses = {}
    completed_tests = 0
    if request.user.bulim:
        now = timezone.now()
        tests = [test for test in Test.objects.filter(bulim=request.user.bulim, active=True) if not test.end_time or now <= test.end_time]
        from main.models import StudentTest
        for test in tests:
            st = StudentTest.objects.filter(test=test, student=request.user).first()
            if st:
                test_statuses[test.id] = 'qatnashgansiz'
                if st.completed:
                    completed_tests += 1
            else:
                test_statuses[test.id] = 'yangi test'
    return render(request, 'employee_panel/dashboard.html', {'tests': tests, 'test_statuses': test_statuses, 'completed_tests': completed_tests})


    # ...existing code...
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from main.models import User

def common_login(request):
    if request.method == 'POST':
        role = request.POST.get('role')
        if role in ['student', 'tutor', 'employee']:
            access_code = request.POST.get('access_code')
            try:
                user = User.objects.get(access_code=access_code, role=role)
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)
                # Dashboardga yo'naltirish
                if role == 'student':
                    return redirect('testapi_dashboard')
                elif role == 'tutor':
                    return redirect('tutor_dashboard')
                elif role == 'employee':
                    return redirect('employee_dashboard')
            except User.DoesNotExist:
                return render(request, 'common_login.html', {'error': 'Access code xato yoki foydalanuvchi topilmadi!'})
        elif role in ['teacher', 'controller']:
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None and getattr(user, 'role', None) == role:
                login(request, user)
                if role == 'teacher':
                    return redirect('teacher_dashboard')
                else:
                    return redirect('controller_dashboard')
            else:
                return render(request, 'common_login.html', {'error': 'Username yoki parol yoki rol xato!'})
    return render(request, 'common_login.html')
