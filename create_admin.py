import os
import django
from django.contrib.auth import get_user_model

# Django muhitini sozlash
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_tizimi.settings")
django.setup()

User = get_user_model()

# Admin ma'lumotlari (DIQQAT: Xavfsizlik uchun murakkab parol kiriting!)
ADMIN_USERNAME = os.environ.get('DJANGO_ADMIN_USERNAME', 'bakirov')
ADMIN_EMAIL = os.environ.get('DJANGO_ADMIN_EMAIL', 'admin@example.com')
ADMIN_PASSWORD = os.environ.get('DJANGO_ADMIN_PASSWORD', 'quwanish') # O'zingizning murakkab parolingizni kiriting!

# Superuser mavjudligini tekshirish
if not User.objects.filter(username=ADMIN_USERNAME).exists():
    print(f"--- INFO: '{ADMIN_USERNAME}' Superuser'i yaratilmoqda ---")
    try:
        User.objects.create_superuser(
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            password=ADMIN_PASSWORD
        )
        print("--- OK: Superuser muvaffaqiyatli yaratildi! ---")
    except Exception as e:
        print(f"--- XATO: Superuser yaratishda xatolik: {e} ---")
else:
    print(f"--- INFO: '{ADMIN_USERNAME}' Superuser allaqachon mavjud. Yangi foydalanuvchi yaratilmadi. ---")