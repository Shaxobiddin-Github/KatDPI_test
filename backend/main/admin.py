from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, University, Faculty, Group, Subject, Question, AnswerOption, Test, TestQuestion, StudentTest, StudentAnswer, Log, Semester, Kafedra, Bulim, GroupSubject

# StudentTest uchun inline (bog‘liq ma'lumotlar)
class StudentTestInline(admin.TabularInline):
    model = StudentTest
    extra = 0
    readonly_fields = ('test', 'start_time', 'end_time', 'total_score', 'completed')
    can_delete = False
    show_change_link = True  # Talaba testini alohida ko‘rish uchun havola
    fk_name = 'student'  # Bir nechta User FK mavjudligi sababli aniq ko'rsatiladi

# User modeli uchun admin sozlamalari
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'role', 'access_code', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'access_code', 'first_name', 'last_name')
    inlines = [StudentTestInline]
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Shaxsiy ma\'lumotlar', {'fields': ('first_name', 'last_name', 'email', 'group', 'kafedra', 'bulim')}),
        ('Ruxsatlar', {'fields': ('role', 'access_code', 'is_active', 'is_staff', 'is_superuser')}),
    )
    readonly_fields = ('access_code',)  # Faqat admin ko‘radi
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'role', 'group', 'kafedra', 'bulim', 'is_active', 'is_staff', 'is_superuser'),
        }),
    )

# Universitet modeli uchun admin sozlamalari
@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
    list_filter = ('created_at',)
    ordering = ('name',)

# Fakultet modeli uchun admin sozlamalari
@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('name', 'university', 'created_at')
    search_fields = ('name', 'university__name')
    list_filter = ('university', 'created_at')
    ordering = ('university', 'name')

# Guruh modeli uchun admin sozlamalari
@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'faculty', 'created_at')
    search_fields = ('name', 'faculty__name')
    list_filter = ('faculty', 'created_at')
    ordering = ('faculty', 'name')

# Fan modeli uchun admin sozlamalari
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
    list_filter = ('created_at',)
    ordering = ('name',)

# Javob variantlari uchun inline
class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    extra = 1
    fields = ('text', 'is_correct')
    readonly_fields = ('created_at',)

# Savol modeli uchun admin sozlamalari
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text_preview', 'subject', 'question_type', 'created_by', 'created_at', 'updated_at')
    search_fields = ('text', 'subject__name', 'created_by__username')
    list_filter = ('question_type', 'subject', 'created_at', 'updated_at')
    inlines = [AnswerOptionInline]
    ordering = ('subject', 'created_at')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user
        if user.is_superuser:
            return qs
        # Teacher va controller faqat o‘zining savollarini ko‘radi
        if hasattr(user, 'role') and user.role in ['teacher', 'controller']:
            return qs.filter(created_by=user)
        return qs.none()

    def has_add_permission(self, request):
        user = request.user
        # Teacher va controller savol qo‘sha oladi
        if hasattr(user, 'role') and user.role in ['teacher', 'controller']:
            return True
        return super().has_add_permission(request)

    def save_model(self, request, obj, form, change):
        # Teacher/controller savol qo‘shsa, created_by ni avtomatik o‘ziga belgilash
        if not change and hasattr(request.user, 'role') and request.user.role in ['teacher', 'controller']:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = "Savol matni"

# Test savollari uchun inline
class TestQuestionInline(admin.TabularInline):
    model = TestQuestion
    extra = 0
    fields = ('question', 'score')
    readonly_fields = ('question', 'score')
    show_change_link = True

# Test modeli uchun admin sozlamalari
@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('group', 'question_count', 'total_score', 'pass_percent', 'duration', 'created_by', 'active', 'created_at')
    search_fields = ('group__name', 'created_by__username')
    list_filter = ('group', 'pass_percent', 'active', 'created_at')
    inlines = [TestQuestionInline]
    ordering = ('group', 'created_at')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user
        if user.is_superuser:
            return qs
        # Teacher va controller faqat o‘zining testlarini ko‘radi
        if hasattr(user, 'role') and user.role in ['teacher', 'controller']:
            return qs.filter(created_by=user)
        return qs.none()

    def has_add_permission(self, request):
        user = request.user
        # Teacher va controller test qo‘sha oladi
        if hasattr(user, 'role') and user.role in ['teacher', 'controller']:
            return True
        return super().has_add_permission(request)

    def save_model(self, request, obj, form, change):
        # Teacher/controller test qo‘shsa, created_by ni avtomatik o‘ziga belgilash
        if not change and hasattr(request.user, 'role') and request.user.role in ['teacher', 'controller']:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

# Talaba javoblari uchun inline
class StudentAnswerInline(admin.TabularInline):
    model = StudentAnswer
    extra = 0
    fields = ('question', 'text_answer', 'is_correct', 'score')
    readonly_fields = ('question', 'is_correct', 'score', 'text_answer')
    show_change_link = True

# Talaba testi uchun admin sozlamalari
@admin.register(StudentTest)
class StudentTestAdmin(admin.ModelAdmin):
    list_display = ('student', 'test', 'group', 'subject', 'semester', 'completed', 'can_retake', 'total_score', 'overridden_score', 'pass_override', 'start_time', 'end_time')
    search_fields = ('student__username', 'test__id', 'group__name', 'subject__name', 'semester__number')
    list_filter = ('completed', 'can_retake', 'group', 'subject', 'semester', 'test', 'start_time', 'end_time')
    readonly_fields = ('start_time', 'end_time', 'total_score', 'question_ids', 'overridden_score', 'pass_override', 'override_reason', 'overridden_by', 'overridden_at')
    inlines = [StudentAnswerInline]
    ordering = ('-start_time',)

# Log modeli uchun admin sozlamalari
@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'created_at')
    search_fields = ('user__username', 'action')
    list_filter = ('created_at',)
    readonly_fields = ('user', 'action', 'created_at')
    ordering = ('-created_at',)

# User modelini admin paneliga ro‘yxatdan o‘tkazish
admin.site.register(User, UserAdmin)  # Maxsus User modeli uchun
admin.site.register(Semester)  # Semestr modeli uchun

@admin.register(Kafedra)
class KafedraAdmin(admin.ModelAdmin):
    list_display = ("name", "faculty", "created_at")   # admin jadvalida ko‘rinadigan ustunlar
    list_filter = ("faculty", "created_at")            # filtrlash imkoniyati
    search_fields = ("name", "faculty__name")          # qidiruv (kafedra nomi yoki fakultet nomi bo‘yicha)


@admin.register(Bulim)
class BulimAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")              # admin jadvalida ko‘rinadigan ustunlar
    list_filter = ("created_at",)                      # sanaga qarab filtrlash
    search_fields = ("name",)

@admin.register(GroupSubject)
class GroupSubjectAdmin(admin.ModelAdmin):
    list_display = ('subject', 'group', 'bulim', 'kafedra', 'semester')
    search_fields = ('subject__name', 'group__name', 'bulim__name', 'kafedra__name')
    list_filter = ('group', 'bulim', 'kafedra', 'semester')
    ordering = ('subject',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('subject', 'group', 'bulim', 'kafedra', 'semester')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Group tanlanganda faqat shu guruhga biriktirilgan fanlar ko‘rinsin (frontend/form/api’da filtrlanadi)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)