from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from main.models import Log  # User modelini settings dan olish uchun
from django.contrib.auth import get_user_model

User = get_user_model()  # main.User modelini dinamik ravishda olish

@receiver(user_logged_in)
def log_user_login(sender, user, request, **kwargs):
    Log.objects.create(user=user, action="Tizimga kirish")

@receiver(user_logged_out)
def log_user_logout(sender, user, request, **kwargs):

    Log.objects.create(user=user, action="Tizimdan chiqish")


# Log yozuvlari 1000 tadan oshsa, eski yozuvlarni avtomatik o‘chirish
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Log)
def limit_log_count(sender, **kwargs):
    max_logs = 1000
    total = Log.objects.count()
    if total > max_logs:
        # Eski loglarni o‘chirish (eng eski yaratilgan sana bo‘yicha)
        to_delete = Log.objects.order_by('created_at')[:total - max_logs]
        Log.objects.filter(id__in=[l.id for l in to_delete]).delete()