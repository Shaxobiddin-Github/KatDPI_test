from django.contrib.auth.models import AbstractUser
from django.db import models
import random


# 1
# User modeli
class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('teacher', 'O‘qituvchi'),
        ('controller', 'Controller'),
        ('student', 'Talaba'),
        ('tutor', 'Tutor'),
        ('employee', 'Xodim'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    access_code = models.CharField(max_length=5, unique=True, blank=True, null=True)  # Talaba, tutor, xodim uchun
    group = models.ForeignKey('Group', on_delete=models.SET_NULL, null=True, blank=True, related_name='students', verbose_name='Guruh')  # Talabani guruhga bog‘lash
    # Tutor uchun faqat kafedra
    kafedra = models.ForeignKey('Kafedra', on_delete=models.SET_NULL, null=True, blank=True, related_name='tutors', verbose_name='Kafedra')
    # Employee uchun bo'lim
    bulim = models.ForeignKey('Bulim', on_delete=models.SET_NULL, null=True, blank=True, related_name='employees', verbose_name="Bo'lim")

    # groups va user_permissions uchun related_name qo‘shish
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='main_user_set',  # Ziddiyatni oldini olish uchun
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='main_user_set',  # Ziddiyatni oldini olish uchun
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"

    def save(self, *args, **kwargs):
        if self.role in ['student', 'tutor', 'employee'] and not self.access_code:
            # 5 xonali avtomatik kod generatsiyasi
            self.access_code = ''.join(random.choices('0123456789', k=5))
        super().save(*args, **kwargs)
# Kafedra modeli
class Kafedra(models.Model):
    faculty = models.ForeignKey('Faculty', on_delete=models.CASCADE, related_name='kafedralar', verbose_name='Fakultet')
    name = models.CharField(max_length=255, verbose_name='Kafedra nomi')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan sana')

    class Meta:
        verbose_name = 'Kafedra'
        verbose_name_plural = 'Kafedralar'

    def __str__(self):
        return f"{self.name} ({self.faculty.name})"

# Bo'lim modeli
class Bulim(models.Model):
    name = models.CharField(max_length=255, verbose_name="Bo'lim nomi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan sana')

    class Meta:
        verbose_name = "Bo'lim"
        verbose_name_plural = "Bo'limlar"

    def __str__(self):
        return self.name
    



# 2
class University(models.Model):
    name = models.CharField(max_length=255, verbose_name="Universitet nomi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")

    class Meta:
        verbose_name = "Universitet"
        verbose_name_plural = "Universitetlar"

    def __str__(self):
        return self.name





# 3
class Faculty(models.Model):
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name='faculties', verbose_name="Universitet")
    name = models.CharField(max_length=255, verbose_name="Fakultet nomi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")

    class Meta:
        verbose_name = "Fakultet"
        verbose_name_plural = "Fakultetlar"

    def __str__(self):
        return self.name





# 4
class Group(models.Model):
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='groups', verbose_name="Fakultet")
    name = models.CharField(max_length=100, verbose_name="Guruh nomi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")

    class Meta:
        verbose_name = "Guruh"
        verbose_name_plural = "Guruhlar"

    def __str__(self):
        return self.name


class Semester(models.Model):
    number = models.PositiveIntegerField(unique=True, choices=[(i, str(i)) for i in range(1, 13)], verbose_name="Semestr raqami")

    class Meta:
        verbose_name = "Semestr"
        verbose_name_plural = "Semestrlar"

    def __str__(self):
        return str(self.number)

# 5
class Subject(models.Model):
    name = models.CharField(max_length=255, verbose_name="Fan nomi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")

    class Meta:
        verbose_name = "Fan"
        verbose_name_plural = "Fanlar"

    def __str__(self):
        return self.name


from django.db.models import Q, UniqueConstraint
from django.core.exceptions import ValidationError

class GroupSubject(models.Model):
    group = models.ForeignKey('Group', on_delete=models.CASCADE, related_name="group_subjects",
                              null=True, blank=True, verbose_name="Guruh")
    bulim = models.ForeignKey('Bulim', on_delete=models.CASCADE, related_name="bulim_subjects",
                              null=True, blank=True, verbose_name="Bo'lim")
    kafedra = models.ForeignKey('Kafedra', on_delete=models.CASCADE, related_name="kafedra_subjects",
                                null=True, blank=True, verbose_name="Kafedra")
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE, related_name="group_subjects",
                                verbose_name="Fan")
    semester = models.ForeignKey('Semester', on_delete=models.CASCADE, related_name="group_subjects",
                                 null=True, blank=True, verbose_name="Semestr")

    class Meta:
        constraints = [
            UniqueConstraint(fields=['group', 'subject', 'semester'], name='unique_group_subject_semester', condition=Q(group__isnull=False)),
            UniqueConstraint(fields=['bulim', 'subject'], name='unique_bulim_subject', condition=Q(bulim__isnull=False)),
            UniqueConstraint(fields=['kafedra', 'subject'], name='unique_kafedra_subject', condition=Q(kafedra__isnull=False)),
        ]
        verbose_name = "Guruh/Bulim/Kafedra fani"
        verbose_name_plural = "Guruh/Bulim/Kafedra fanlari"

    def clean(self):
        # Guruh bo'lsa, semester majburiy
        if self.group and not self.semester:
            raise ValidationError('Guruh uchun semestr majburiy!')
        # Bulim yoki kafedra uchun semester kerak emas
        if (self.bulim or self.kafedra) and self.semester:
            raise ValidationError('Bulim yoki kafedra uchun semester bo‘lmasligi kerak!')

    def __str__(self):
        if self.group:
            return f"{self.group} - {self.subject} ({self.semester})"
        elif self.bulim:
            return f"{self.bulim} - {self.subject}"
        elif self.kafedra:
            return f"{self.kafedra} - {self.subject}"
        return str(self.subject)
# ...existing code...
class Question(models.Model):
    QUESTION_TYPE_CHOICES = (
        ('single_choice', 'Bitta to‘g‘ri javob'),
        ('multiple_choice', 'Ko‘p to‘g‘ri javob'),
        ('fill_in_blank', 'Bo‘sh joyni to‘ldirish'),
        ('sentence_ordering', 'Jumlalarni tartiblash'),
        ('true_false', 'To‘g‘ri/Yolg‘on'),
        ('matching', 'Moslashtirish'),
    )
    
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='questions', verbose_name="Fan")
    semester = models.ForeignKey('Semester', on_delete=models.SET_NULL, null=True, blank=True, related_name='questions', verbose_name='Semestr')
    # Yangi: savolni aniq guruhga bog'lash (avval yo'q edi). Null bo'lsa – eskidan qolgan/global savol.
    group = models.ForeignKey('Group', on_delete=models.CASCADE, null=True, blank=True, related_name='questions', verbose_name='Guruh')
    text = models.TextField(verbose_name="Savol matni")
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, verbose_name="Savol turi")
    image = models.ImageField(upload_to='questions/', blank=True, null=True, verbose_name="Rasm")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Yaratuvchi")
    kafedra = models.ForeignKey('Kafedra', on_delete=models.SET_NULL, null=True, blank=True, related_name='questions', verbose_name='Kafedra')
    bulim = models.ForeignKey('Bulim', on_delete=models.SET_NULL, null=True, blank=True, related_name='questions', verbose_name="Bo'lim")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana")

    class Meta:
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"

    def __str__(self):
        return f"{self.text[:50]}... ({self.get_question_type_display()})"




# 7

# Matching uchun left/right ustunli model
class AnswerOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answer_options', verbose_name="Savol")
    text = models.TextField(verbose_name="Javob matni", blank=True)  # Single/multi/fill uchun
    is_correct = models.BooleanField(default=False, verbose_name="To‘g‘ri javobmi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    # Matching uchun
    left = models.CharField(max_length=255, blank=True, null=True, verbose_name="So‘z (chap)")
    right = models.CharField(max_length=255, blank=True, null=True, verbose_name="Javob (o‘ng)")
    image = models.ImageField(upload_to='matching_answers/', blank=True, null=True, verbose_name="Matching javob rasm")

    class Meta:
        verbose_name = "Javob varianti"
        verbose_name_plural = "Javob variantlari"

    def __str__(self):
        if self.left and self.right:
            return f"{self.left} — {self.right}"
        return self.text





# 8
class Test(models.Model):
    group = models.ForeignKey('Group', on_delete=models.CASCADE, related_name='tests', verbose_name="Guruh", null=True, blank=True)
    # New M2M for future multi-group assignment (initially unused in creation flow; populated by migration from existing group field)
    groups = models.ManyToManyField('Group', blank=True, related_name='multi_tests', verbose_name='Biriktirilgan guruhlar')
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE, related_name='tests', verbose_name="Fan")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_tests', verbose_name="Yaratuvchi (Controller)")
    kafedra = models.ForeignKey('Kafedra', on_delete=models.SET_NULL, null=True, blank=True, related_name='tests', verbose_name='Kafedra')
    bulim = models.ForeignKey('Bulim', on_delete=models.SET_NULL, null=True, blank=True, related_name='tests', verbose_name="Bo'lim")
    semester = models.ForeignKey('Semester', on_delete=models.SET_NULL, null=True, blank=True, related_name='tests', verbose_name='Semestr')
    question_count = models.PositiveIntegerField(verbose_name="Savollar soni")
    total_score = models.PositiveIntegerField(verbose_name="Umumiy ball")
    duration = models.DurationField(verbose_name="Test muddati")
    minutes = models.PositiveIntegerField(verbose_name="Test vaqti (daqiqa)", default=30)
    # Ixtiyoriy videoni qo'llab-quvvatlash (testdan avval ko'rsatiladi)
    video_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="Video URL (ixtiyoriy)")
    video_file = models.FileField(upload_to='test_videos/', blank=True, null=True, verbose_name="Video fayl (ixtiyoriy)")
    pass_percent = models.PositiveIntegerField(verbose_name="O'tish foizi", default=56, help_text="Talabaning foiz natijasi shu qiymatdan >= bo'lsa o'tgan hisoblanadi")
    active = models.BooleanField(default=True, verbose_name="Faol testmi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    start_time = models.DateTimeField(auto_now_add=True, verbose_name="Boshlanish vaqti", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_tests', verbose_name='Kim yangiladi')

    class Meta:
        verbose_name = "Test"
        verbose_name_plural = "Testlar"

    def __str__(self):
        return f"Test: {self.subject.name} ({self.question_count} savol)"

    @property
    def end_time(self):
        # Test tugash vaqti: start_time + duration
        if self.start_time and self.duration:
            return self.start_time + self.duration
        return None






# 9
class TestQuestion(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='test_questions', verbose_name="Test")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='test_questions', verbose_name="Savol")
    score = models.FloatField(verbose_name="Savol balli")

    class Meta:
        verbose_name = "Test savoli"
        verbose_name_plural = "Test savollari"

    def __str__(self):
        return f"{self.question.text[:50]}... ({self.score} ball)"






# 10
class StudentTest(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_tests', verbose_name="Talaba")
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='student_tests', verbose_name="Test")
    group = models.ForeignKey('Group', on_delete=models.CASCADE, null=True, blank=True, verbose_name="Guruh")
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE, null=True, blank=True, verbose_name="Fan")
    semester = models.ForeignKey('Semester', on_delete=models.CASCADE, null=True, blank=True, verbose_name="Semestr")
    start_time = models.DateTimeField(auto_now_add=True, verbose_name="Boshlangan vaqt")
    end_time = models.DateTimeField(blank=True, null=True, verbose_name="Tugagan vaqt")
    total_score = models.FloatField(default=0, verbose_name="Umumiy ball")
    completed = models.BooleanField(default=False, verbose_name="Tugatilganmi")
    question_ids = models.JSONField(default=list, blank=True, verbose_name="Tanlangan savollar ID")
    can_retake = models.BooleanField(default=False, verbose_name="Qayta topshirishga ruxsat (controller)")
    # --- Override bilan bog'liq maydonlar (faqat superuser ko'radi) ---
    overridden_score = models.FloatField(null=True, blank=True, verbose_name="Qo'lda o'zgartirilgan ball")
    pass_override = models.BooleanField(default=False, verbose_name="Majburan o'tkazish (override)")
    override_reason = models.TextField(null=True, blank=True, verbose_name="O'zgartirish sababi")
    overridden_by = models.ForeignKey('User', null=True, blank=True, on_delete=models.SET_NULL, related_name='overridden_tests', verbose_name="Kim o'zgartirdi")
    overridden_at = models.DateTimeField(null=True, blank=True, verbose_name="O'zgartirilgan vaqt")

    class Meta:
        verbose_name = "Talaba testi"
        verbose_name_plural = "Talaba testlari"
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'group', 'subject', 'semester'],
                condition=models.Q(completed=True, can_retake=False),
                name='unique_student_group_subject_semester_once'
            )
        ]

    def __str__(self):
        return f"{self.student.username} - {self.subject.name if self.subject else ''} ({self.semester})"

    @property
    def final_score(self):
        return self.overridden_score if self.overridden_score is not None else self.total_score

    @property
    def is_overridden(self):
        return (self.overridden_score is not None) or self.pass_override

    @property
    def final_passed(self):
        # 1) pass_override ustun
        if self.pass_override:
            return True
        # 2) Testdagi pass_percent bo'yicha foiz hisoblash
        if self.test and self.test.total_score:
            percent = (self.final_score / self.test.total_score) * 100 if self.final_score is not None else 0
            return percent >= getattr(self.test, 'pass_percent', 56)
        # 3) Zaxira holat
        return self.final_score > 0





# 11
class StudentAnswer(models.Model):
    student_test = models.ForeignKey(StudentTest, on_delete=models.CASCADE, related_name='answers', verbose_name="Talaba testi")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name="Savol")
    answer_option = models.ManyToManyField(AnswerOption, blank=True, verbose_name="Tanlangan javoblar")
    text_answer = models.TextField(blank=True, null=True, verbose_name="Matnli javob")
    is_correct = models.BooleanField(default=False, verbose_name="To‘g‘ri javobmi")
    score = models.FloatField(default=0, verbose_name="Ball")

    class Meta:
        verbose_name = "Talaba javobi"
        verbose_name_plural = "Talaba javoblari"

    def __str__(self):
        return f"{self.student_test.student.username} - {self.question.text[:50]}..."







# 12
class Log(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Foydalanuvchi")
    action = models.CharField(max_length=255, verbose_name="Harakat")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")

    class Meta:
        verbose_name = "Log"
        verbose_name_plural = "Loglar"

    def __str__(self):
        return f"{self.user.username if self.user else 'Noma’lum'} - {self.action}"


# --- Override tarixini saqlash uchun model ---
class StudentTestModification(models.Model):
    student_test = models.ForeignKey(StudentTest, on_delete=models.CASCADE, related_name='modifications', verbose_name="Talaba testi")
    previous_score = models.FloatField(null=True, blank=True, verbose_name="Oldingi ball")
    new_score = models.FloatField(null=True, blank=True, verbose_name="Yangi ball")
    previous_pass_override = models.BooleanField(default=False, verbose_name="Oldingi majburiy o'tkazish")
    new_pass_override = models.BooleanField(default=False, verbose_name="Yangi majburiy o'tkazish")
    reason = models.TextField(verbose_name="Sabab")
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='score_changes', verbose_name="O'zgartirgan foydalanuvchi")
    change_type = models.CharField(max_length=20, choices=(
        ('override', 'Override'),
        ('revert', 'Revert'),
    ), verbose_name="O'zgarish turi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqt")

    class Meta:
        verbose_name = "Natija o'zgarishi"
        verbose_name_plural = "Natija o'zgarishlari"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student_test_id} | {self.change_type} | {self.created_at}"


# QR kod orqali PDF tasdiqlash uchun yozuvlar
class PdfVerification(models.Model):
    hash_code = models.CharField(max_length=32, unique=True, verbose_name="QR hash")
    subject_name = models.CharField(max_length=255, verbose_name="Fan nomi")
    record_count = models.PositiveIntegerField(default=0, verbose_name="Qatorlar soni")
    payload = models.TextField(verbose_name="Asl ma'lumot")
    created_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='pdf_verifications')

    class Meta:
        verbose_name = "PDF tasdiq (QR)"
        verbose_name_plural = "PDF tasdiqlar (QR)"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject_name} | {self.hash_code}"


# =============================
#  TOPIC-BASED (Teacher-only) MINI TEST SYSTEM (isolated)
#  (No semester, only group + subject; questions reused per topic)
# =============================

class Topic(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='topics', verbose_name='Fan')
    # Group endi ixtiyoriy, test yaratishda biriktiriladi
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='topics', verbose_name='Guruh', null=True, blank=True)
    title = models.CharField(max_length=255, verbose_name='Mavzu nomi')
    description = models.TextField(blank=True, null=True, verbose_name='Izoh')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_topics', verbose_name='O‘qituvchi')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, verbose_name='Faol')

    class Meta:
        verbose_name = 'Mavzu'
        verbose_name_plural = 'Mavzular'
        ordering = ['-created_at']
        unique_together = [('subject', 'group', 'title', 'created_by')]

    def __str__(self):
        return f"{self.title} ({self.subject} / {self.group})"


class TopicIntroVideo(models.Model):
    topic = models.OneToOneField(Topic, on_delete=models.CASCADE, related_name='intro_video', verbose_name='Mavzu')
    video_url = models.URLField(max_length=500, blank=True, null=True, verbose_name='Video URL')
    video_file = models.FileField(upload_to='topic_videos/', blank=True, null=True, verbose_name='Video fayl')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Mavzu intro video'
        verbose_name_plural = 'Mavzu intro videolar'

    def __str__(self):
        return f"Video: {self.topic.title}"


class TopicQuestion(models.Model):
    SINGLE = 'single'
    MULTI = 'multi'
    QUESTION_TYPE_CHOICES = (
        (SINGLE, 'Bitta to‘g‘ri javob'),
        (MULTI, 'Ko‘p to‘g‘ri javob'),
    )
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='questions', verbose_name='Mavzu')
    text = models.TextField(verbose_name='Savol matni')
    image = models.ImageField(upload_to='topic_questions/', blank=True, null=True, verbose_name='Rasm')
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPE_CHOICES, default=SINGLE, verbose_name='Savol turi')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='topic_questions', verbose_name='Yaratuvchi')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Mavzu savoli'
        verbose_name_plural = 'Mavzu savollari'

    def __str__(self):
        return f"{self.text[:50]}... ({self.get_question_type_display()})"

    @property
    def correct_option_count(self):
        return self.options.filter(is_correct=True).count()


class TopicAnswerOption(models.Model):
    question = models.ForeignKey(TopicQuestion, on_delete=models.CASCADE, related_name='options', verbose_name='Savol')
    text = models.TextField(verbose_name='Variant matni')
    is_correct = models.BooleanField(default=False, verbose_name='To‘g‘ri javobmi')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Mavzu javob varianti'
        verbose_name_plural = 'Mavzu javob variantlari'

    def __str__(self):
        return self.text[:60]


class TopicTest(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='tests', verbose_name='Mavzu')
    title = models.CharField(max_length=255, verbose_name='Test nomi')
    question_count = models.PositiveIntegerField(verbose_name='Savollar soni')
    total_score = models.PositiveIntegerField(verbose_name='Umumiy ball')
    duration = models.DurationField(verbose_name='Test muddati')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='topic_tests', verbose_name='Yaratuvchi')
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=True, verbose_name='Faol')
    # Snapshot of selected question ids (to keep order consistency)
    question_ids = models.JSONField(default=list, blank=True, verbose_name='Tanlangan savollar ID')
    # New: optional extra groups that may ham testni ishlashi mumkin (asosiy topic.group dan tashqari)
    groups = models.ManyToManyField('Group', blank=True, related_name='topic_tests_multi', verbose_name='Qo‘shimcha guruhlar')
    # Shuffle configuration
    shuffle_questions = models.BooleanField(default=True, verbose_name='Savollar aralashtirilsinmi')
    shuffle_options = models.BooleanField(default=True, verbose_name='Variantlar aralashtirilsinmi')
    question_block_size = models.PositiveIntegerField(default=0, verbose_name='Blok hajmi (0=oddiy)', help_text='>0 bo‘lsa savollar shu hajmdagi bloklarda alohida aralashtiriladi')

    class Meta:
        verbose_name = 'Mavzu testi'
        verbose_name_plural = 'Mavzu testlari'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.topic.title})"


class TopicStudentTest(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='topic_student_tests', verbose_name='Talaba')
    test = models.ForeignKey(TopicTest, on_delete=models.CASCADE, related_name='student_runs', verbose_name='Test')
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='Boshlangan vaqt')
    finished_at = models.DateTimeField(blank=True, null=True, verbose_name='Tugagan vaqt')
    total_score = models.FloatField(default=0, verbose_name='Ball')
    completed = models.BooleanField(default=False, verbose_name='Tugadimi')
    # Random order per student (IDs) – ensures bir xil savollar, turli tartib
    randomized_question_ids = models.JSONField(default=list, blank=True, verbose_name='Random tartib savollar')

    class Meta:
        verbose_name = 'Mavzu talaba testi'
        verbose_name_plural = 'Mavzu talaba testlari'
        constraints = [
            models.UniqueConstraint(fields=['student', 'test'], name='unique_topic_student_test_once')
        ]

    def __str__(self):
        return f"{self.student.username} - {self.test.title}"


class TopicStudentAnswer(models.Model):
    student_test = models.ForeignKey(TopicStudentTest, on_delete=models.CASCADE, related_name='answers', verbose_name='Talaba testi')
    question = models.ForeignKey(TopicQuestion, on_delete=models.CASCADE, related_name='topic_student_answers', verbose_name='Savol')
    selected_options = models.ManyToManyField(TopicAnswerOption, blank=True, related_name='chosen_in', verbose_name='Tanlangan variantlar')
    is_correct = models.BooleanField(default=False, verbose_name='To‘g‘rimi')
    score = models.FloatField(default=0, verbose_name='Ball')

    class Meta:
        verbose_name = 'Mavzu talaba javobi'
        verbose_name_plural = 'Mavzu talaba javoblari'

    def __str__(self):
        return f"{self.student_test.student.username} - {self.question.id}"
