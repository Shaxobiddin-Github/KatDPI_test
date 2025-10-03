from rest_framework import serializers
from .models import (
    User, University, Faculty, Group, Subject, Question, AnswerOption, Test,
    TestQuestion, StudentTest, StudentAnswer, Log, StudentTestModification
)

# Foydalanuvchi seriyalizatori
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'role', 'access_code']
        read_only_fields = ['access_code']  # Access_code faqat admin ko‘radi

# Universitet seriyalizatori
class UniversitySerializer(serializers.ModelSerializer):
    class Meta:
        model = University
        fields = ['id', 'name', 'created_at']

# Fakultet seriyalizatori
class FacultySerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = ['id', 'university', 'name', 'created_at']

# Guruh seriyalizatori
class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'faculty', 'name', 'created_at']

# Fan seriyalizatori
class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name', 'group', 'teacher', 'semester', 'created_at']

# Javob varianti seriyalizatori
class AnswerOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerOption
        fields = ['id', 'text', 'is_correct']

# Savol seriyalizatori
class QuestionSerializer(serializers.ModelSerializer):
    answer_options = AnswerOptionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Question
        fields = ['id', 'subject', 'text', 'question_type', 'image', 'answer_options', 'created_at', 'updated_at']

# Test seriyalizatori
class TestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
    fields = ['id', 'subject', 'question_count', 'total_score', 'duration', 'pass_percent', 'created_at']

# Test savoli seriyalizatori
class TestQuestionSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)
    
    class Meta:
        model = TestQuestion
        fields = ['id', 'test', 'question', 'score']

# Talaba javobi seriyalizatori
class StudentAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAnswer
        fields = ['question', 'answer_option', 'text_answer', 'is_correct', 'score']

# Talaba testi seriyalizatori
class StudentTestSerializer(serializers.ModelSerializer):
    answers = StudentAnswerSerializer(many=True, read_only=True)
    final_score = serializers.SerializerMethodField()
    final_passed = serializers.SerializerMethodField()
    is_overridden = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentTest
        fields = [
            'id', 'test', 'group', 'subject', 'semester',
            'start_time', 'end_time', 'total_score', 'completed', 'can_retake',
            'final_score', 'final_passed', 'is_overridden', 'answers'
        ]

    def get_final_score(self, obj):
        return obj.final_score

    def get_final_passed(self, obj):
        return obj.final_passed

    def get_is_overridden(self, obj):
        request = self.context.get('request')
        if request and request.user and request.user.is_superuser:
            return obj.is_overridden
        # Oddiy foydalanuvchiga override holati ko'rsatilmaydi
        return False


class StudentTestAdminSerializer(StudentTestSerializer):
    overridden_score = serializers.FloatField(read_only=True)
    pass_override = serializers.BooleanField(read_only=True)
    override_reason = serializers.CharField(read_only=True)
    overridden_by = serializers.SerializerMethodField()
    overridden_at = serializers.DateTimeField(read_only=True)

    class Meta(StudentTestSerializer.Meta):
        fields = StudentTestSerializer.Meta.fields + [
            'overridden_score', 'pass_override', 'override_reason', 'overridden_by', 'overridden_at'
        ]

    def get_overridden_by(self, obj):
        if obj.overridden_by:
            return {'id': obj.overridden_by.id, 'username': obj.overridden_by.username}
        return None


class StudentTestModificationSerializer(serializers.ModelSerializer):
    changed_by = serializers.SerializerMethodField()

    class Meta:
        model = StudentTestModification
        fields = [
            'id', 'previous_score', 'new_score', 'previous_pass_override', 'new_pass_override',
            'reason', 'changed_by', 'change_type', 'created_at'
        ]

    def get_changed_by(self, obj):
        if obj.changed_by:
            return {'id': obj.changed_by.id, 'username': obj.changed_by.username}
        return None

# Log seriyalizatori
class LogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Log
        fields = ['id', 'user', 'action', 'created_at']