from django.core.management.base import BaseCommand
from main.models import Question

class Command(BaseCommand):
    help = "Ro'yxat: group biriktirilmagan (group_id IS NULL) savollar"

    def handle(self, *args, **options):
        qs = Question.objects.filter(group__isnull=True)
        count = qs.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS("Barcha savollar guruhlarga biriktirilgan."))
            return
        self.stdout.write(self.style.WARNING(f"{count} ta savolda group yo'q:"))
        for q in qs.order_by('-created_at')[:200]:
            self.stdout.write(f"ID={q.id} | Fan={q.subject_id} | Semestr={q.semester_id or '-'} | Matn={q.text[:70]}")
        if count > 200:
            self.stdout.write(self.style.NOTICE("(Ko'proq bor, faqat 200 tasi ko'rsatildi)"))
