from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from .models import Subject, Test as TestModel, StudentTest
from datetime import timedelta

User = get_user_model()

class OverrideFlowTests(TestCase):
    def setUp(self):
        self.super = User.objects.create_user(username='super', password='pass', is_superuser=True, role='admin')
        self.student = User.objects.create_user(username='stud', password='pass', role='student')
        self.subject = Subject.objects.create(name='Matematika')
        self.test_obj = TestModel.objects.create(subject=self.subject, question_count=1, total_score=100, duration=timedelta(minutes=10), minutes=10)
        self.st = StudentTest.objects.create(student=self.student, test=self.test_obj, total_score=55, completed=True)
        self.client = APIClient()

    def test_super_can_override(self):
        self.client.force_authenticate(self.super)
        url = f"/api/student-tests/{self.st.id}/override/"
        resp = self.client.post(url, {'new_score': 70, 'reason': 'Komissiya'})
        self.assertEqual(resp.status_code, 200)
        self.st.refresh_from_db()
        self.assertEqual(self.st.overridden_score, 70)

    def test_student_cannot_override(self):
        self.client.force_authenticate(self.student)
        url = f"/api/student-tests/{self.st.id}/override/"
        resp = self.client.post(url, {'new_score': 80, 'reason': 'Yo\'q'})
        self.assertEqual(resp.status_code, 403)

    def test_revert(self):
        self.client.force_authenticate(self.super)
        o_url = f"/api/student-tests/{self.st.id}/override/"
        self.client.post(o_url, {'new_score': 60, 'reason': 'Test'})
        r_url = f"/api/student-tests/{self.st.id}/revert/"
        resp = self.client.post(r_url, {'reason': 'Bekor'})
        self.assertEqual(resp.status_code, 200)
        self.st.refresh_from_db()
        self.assertIsNone(self.st.overridden_score)

    def test_history_access_control(self):
        # superuser can see history after override
        self.client.force_authenticate(self.super)
        o_url = f"/api/student-tests/{self.st.id}/override/"
        self.client.post(o_url, {'new_score': 65, 'reason': 'Nazorat'})
        h_url = f"/api/student-tests/{self.st.id}/history/"
        resp = self.client.get(h_url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(resp.json()) >= 1)
        # student cannot access history
        self.client.force_authenticate(self.student)
        resp2 = self.client.get(h_url)
        self.assertEqual(resp2.status_code, 403)

    def test_visibility_for_student(self):
        # override as superuser
        self.client.force_authenticate(self.super)
        o_url = f"/api/student-tests/{self.st.id}/override/"
        self.client.post(o_url, {'new_score': 75, 'reason': 'Qo\'shimcha'})
        # fetch as student
        self.client.force_authenticate(self.student)
        detail_url = f"/api/student-tests/{self.st.id}/"
        resp = self.client.get(detail_url)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        # student serializer should not expose internal override fields
        self.assertNotIn('overridden_score', body)
        self.assertNotIn('override_reason', body)
        self.assertIn('final_score', body)

    def test_pass_percent_threshold(self):
        # Default pass_percent=56; current total_score=55 of 100 -> should NOT pass
        self.assertFalse(self.st.final_passed)
        # Override to 60 -> now >=56% should pass
        self.client.force_authenticate(self.super)
        o_url = f"/api/student-tests/{self.st.id}/override/"
        self.client.post(o_url, {'new_score': 60, 'reason': 'Threshold test'})
        self.st.refresh_from_db()
        self.assertTrue(self.st.final_passed)