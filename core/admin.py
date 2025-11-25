# core/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.urls import reverse
from django.utils.html import format_html
from .models import (
    CustomUser, Sinf, StudentProfile,
    Test, Savol, Variant,
    TestResult, StudentAnswer
)
from tinymce.widgets import TinyMCE
from django.db import models


# ---------------- 1. Custom User & Profiles ----------------

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('is_student', 'is_admin')}),
    )
    list_display = ('username', 'email', 'is_active', 'is_staff', 'is_student', 'is_admin')


admin.site.register(CustomUser, CustomUserAdmin)


@admin.register(Sinf)
class SinfAdmin(admin.ModelAdmin):
    list_display = ('nom',)
    search_fields = ('nom',)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'sinf', 'total_points')
    list_filter = ('sinf',)
    search_fields = ('user__username', 'sinf__nom')
    ordering = ('sinf__nom', '-total_points')


# ---------------- 2. Test Yaratish – QULAY MODE ----------------

# ❗ Variantlar faqat Savol sahifasida ko'rinadi
class VariantInline(admin.TabularInline):
    model = Variant
    extra = 4
    fields = ('matn', 'is_correct')
    formfield_overrides = {
        models.TextField: {'widget': TinyMCE(attrs={'cols': 50, 'rows': 5})},
    }


@admin.register(Savol)
class SavolAdmin(admin.ModelAdmin):
    list_display = ('id', 'test', 'savol_excerpt')
    list_filter = ('test',)
    search_fields = ('matn', 'test__nom')
    inlines = [VariantInline]

    formfield_overrides = {
        models.TextField: {'widget': TinyMCE(attrs={'cols': 100, 'rows': 10})},
    }

    def savol_excerpt(self, obj):
        return obj.matn[:50] + '...' if len(obj.matn) > 50 else obj.matn

    savol_excerpt.short_description = "Savol"


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('nom', 'sinf', 'yaratilgan_sana', 'manage_savollar')
    list_filter = ('sinf', 'yaratilgan_sana')
    search_fields = ('nom',)

    def manage_savollar(self, obj):
        url = reverse('admin:core_savol_changelist') + f'?test__id__exact={obj.id}'
        return format_html(f"<a class='button' href='{url}'>Savollarni boshqarish</a>")

    manage_savollar.short_description = "Savollar"


# ---------------- 3. Natijalar ----------------

class StudentAnswerInline(admin.TabularInline):
    model = StudentAnswer
    readonly_fields = ('savol', 'tanlangan_variant', 'is_correct')
    can_delete = False
    extra = 0


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ('student_username', 'test_name', 'sinf_name', 'jami_ball', 'sinov_sanasi')
    list_filter = ('test__sinf__nom', 'test__nom', 'sinov_sanasi')
    search_fields = ('student__user__username', 'test__nom')
    inlines = [StudentAnswerInline]

    def student_username(self, obj):
        return obj.student.user.username

    def test_name(self, obj):
        return obj.test.nom

    def sinf_name(self, obj):
        return obj.student.sinf.nom if obj.student.sinf else "—"
