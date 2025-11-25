# core/models.py
from typing import Any

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.html import format_html



# ----------------- 1. Foydalanuvchi va Profil Modellar -----------------

class CustomUser(AbstractUser):
    """Admin va O'quvchi uchun kengaytirilgan foydalanuvchi modeli."""
    is_student = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)

    def __str__(self):
        return self.username


class Sinf(models.Model):
    """O'quv sinflarini saqlash uchun model (Masalan: 5-A, 6-B)."""
    nom = models.CharField(max_length=10, unique=True)

    class Meta:
        verbose_name = "Sinf"
        verbose_name_plural = "Sinflar"

    def __str__(self):
        return self.nom


class StudentProfile(models.Model):
    """O'quvchi profili va umumiy ballarini saqlash."""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, primary_key=True)
    sinf = models.ForeignKey(Sinf, on_delete=models.SET_NULL, null=True, blank=True)
    total_points = models.IntegerField(default=0)  # Rating uchun ishlatiladigan umumiy ball

    class Meta:
        verbose_name = "O'quvchi Profili"
        verbose_name_plural = "O'quvchilar Profillari"

    def __str__(self):
        return f"{self.user.username} - {self.sinf.nom if self.sinf else 'Sinf tanlanmagan'}"


# ----------------- 2. Test Modellar -----------------

# core/models.py - Qayta tuzatilgan Test modeli
class Test(models.Model):
    """Asosiy test ma'lumotlari."""
    nom = models.CharField(max_length=255)
    sinf = models.ForeignKey(Sinf, on_delete=models.CASCADE,
                             help_text="Bu test qaysi sinf o'quvchilari uchun mo'ljallangan.")
    yaratilgan_sana = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Test"
        verbose_name_plural = "Testlar"
        ordering = ['-yaratilgan_sana']

    def __str__(self):
        return f"{self.nom} ({self.sinf.nom})"


class Savol(models.Model):
    """Har bir testdagi savollar."""
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='savollar')
    matn = models.TextField(
        help_text=format_html("Matematik formula, rasm va formatlash (Bold, Code) kiritish mumkin."))
    ball = models.IntegerField(default=1, help_text="Bu savol uchun beriladigan ball.")

    class Meta:
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"

    def __str__(self):
        # Matnning boshlang'ich qismini ko'rsatish
        return f"Savol {self.id}: {self.matn[:50]}..."


class Variant(models.Model):
    """Savol uchun javob variantlari."""
    savol = models.ForeignKey(Savol, on_delete=models.CASCADE, related_name='variantlar')
    matn = models.TextField(help_text=format_html("Variant matni (Rich Text)."))
    is_correct = models.BooleanField(default=False, verbose_name="To'g'ri javob")

    class Meta:
        verbose_name = "Variant"
        verbose_name_plural = "Variantlar"

    def __str__(self):
        return f"Variant {self.id}: {self.matn[:30]}"


# ----------------- 3. Natijalar Modellar -----------------

class TestResult(models.Model):
    """O'quvchining rasmiy (eng birinchi) test natijasi."""
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, verbose_name="O'quvchi")
    test = models.ForeignKey(Test, on_delete=models.CASCADE, verbose_name="Test")
    jami_ball = models.IntegerField(default=0, verbose_name="Jami Ball")
    sinov_sanasi = models.DateTimeField(auto_now_add=True, verbose_name="Sinov Sanasi")
    umumiy_savollar_soni = models.IntegerField(default=0)  # Oldingi xatoda qo'shdik
    togri_javoblar_soni = models.IntegerField(default=0)  # Oldingi xatoda qo'shdik

    class Meta:
        verbose_name = "Test Natijasi"
        verbose_name_plural = "Test Natijalari"
        ordering = ['-sinov_sanasi']

    def __str__(self):
        return f"{self.student.user.username} - {self.test.nom}: {self.jami_ball} ball"


class StudentAnswer(models.Model):
    """O'quvchining bergan javoblarini saqlash."""
    result = models.ForeignKey(TestResult, on_delete=models.CASCADE, related_name='javoblar')
    savol = models.ForeignKey(Savol, on_delete=models.CASCADE)
    tanlangan_variant = models.ForeignKey(Variant, on_delete=models.SET_NULL, null=True)
    is_correct = models.BooleanField(default=False)
    ball = models.IntegerField(default=1, verbose_name="Savol Bali")

    class Meta:
        verbose_name = "O'quvchi Javobi"
        verbose_name_plural = "O'quvchi Javoblari"

    def __str__(self):
        return f"Javob: {self.savol.test.nom} - {self.result.student.user.username}"