
# --- Yangi kod: Telegramga xabar yuborish uchun ---
import os
import json
import requests
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from .models import Log

User = get_user_model()

# Telegram konfiguratsiyasi (TOKEN va CHAT_ID ni o'zingizniki bilan almashtiring)
TELEGRAM_BOT_TOKEN = '8455119643:AAHi5J0Tu4_T7FSilrHGvZrOS6OH3WheLns'
TELEGRAM_CHAT_ID = '7402066335'

def send_telegram_alert(full_name, group):
    message = f"{full_name} {group} guruh talabasi test paytida shubhali harakat qildi!"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        requests.post(url, data=data, timeout=5)
    except Exception as e:
        print(f"Telegramga xabar yuborilmadi: {e}")

@csrf_exempt
def log_action(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            user_id = data.get('user_id')
            user = User.objects.filter(id=user_id).first()
            Log.objects.create(user=user, action=action)

            # Faqat kerakli harakatlar va vaqt
            if user and action in ['Sahifani tark etdi', 'Sahifaga qaytdi']:
                base_dir = os.path.join(
                    os.path.dirname(__file__),
                    'templates', 'test_api', 'harakat', user.username
                )
                os.makedirs(base_dir, exist_ok=True)
                file_path = os.path.join(base_dir, 'actions.txt')
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                with open(file_path, 'a', encoding='utf-8') as f:
                    f.write(f"{now} - {action}\n")

                # --- Telegramga xabar yuborish ---
                full_name = f"{user.last_name} {user.first_name}"
                group = user.group.name if hasattr(user, 'group') and user.group else 'Noma’lum'
                send_telegram_alert(full_name, group)

            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Only POST allowed'}, status=405)



