from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.urls import reverse, path  # path import qilindi
from django.utils.html import format_html
from django.shortcuts import render, redirect  # render va redirect import qilindi
from django.contrib import messages  # Xabar chiqarish uchun
import re  # Matn tahlili uchun
from django.db import models

from tinymce.widgets import TinyMCE

# --- Lokal modellar va formalarni import qilish ---
# Sizning loyihangizdagi modellar
from .models import (
    CustomUser, Sinf, StudentProfile,
    Test, Savol, Variant,
    TestResult, StudentAnswer
)
# Yangi yaratilgan forma
from .forms import QuestionImportForm


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


# ---------------- 2. IMPORT LOGIKASI (Yangi Klass) ----------------

class QuestionImporter:
    """
    Matnni tahlil qilib, Savol va Variantlarni yaratish uchun yordamchi klass.
    Docx shablonidagi (#1., #ball:, +A) formatini tahlil qiladi.
    """

    def __init__(self, test_instance):
        self.test = test_instance

    def process_text(self, raw_text):
        # Faylning to'liq matnini savollarga ajratamiz. # raqami bilan boshlangan har bir satr.
        questions_blocks = re.split(r'#\d+\.', raw_text)

        # Birinchi element bo'sh bo'lishi mumkin
        if questions_blocks and not questions_blocks[0].strip():
            questions_blocks.pop(0)

        imported_count = 0

        for block in questions_blocks:
            if not block.strip():
                continue

            # 1. Ballni topish
            score_match = re.search(r'#ball:\s*([\d\.]+)', block)
            score = float(score_match.group(1)) if score_match else 1.0

            # 2. Savol matnini topish (Ball va variantlardan oldin)
            # Ball tagidan oldingi qismni ajratib olamiz
            question_text_part = re.split(r'#ball:', block, 1)
            question_text = question_text_part[0].strip()

            if not question_text:
                continue

            # Savol yaratish
            try:
                question_instance = Savol.objects.create(
                    test=self.test,
                    matn=question_text,
                    ball=score
                )
            except Exception as e:
                # Agar saqlashda xato bo'lsa (masalan, matn juda uzun)
                raise Exception(f"Savol yaratishda xatolik: {e}. Savol: {question_text[:50]}...")

            # 3. Variantlarni ajratish (Ball tagidan keyingi qism)
            if len(question_text_part) > 1:
                variants_part = question_text_part[1]

                # Regex: (\+?[A-D])\)\s*(.*?) - formatidagi variantlarni ajratish
                variants = re.findall(r'(\+?[A-D])\)\s*(.*?)(?=\+?[A-D]\)|\Z)', variants_part, re.DOTALL)

                for prefix, text in variants:
                    is_correct = '+' in prefix
                    # Variant matnining boshidagi harf va qavslarni tozalash shart emas, chunki regex ularni ajratib oladi
                    clean_text = text.strip()

                    Variant.objects.create(
                        savol=question_instance,
                        matn=clean_text,
                        is_correct=is_correct
                    )

            imported_count += 1

        return imported_count


# ---------------- 4. Test va Savollar Admini ----------------

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
    list_display = ('id', 'test', 'savol_excerpt', 'ball')
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
    # Import action'ini qo'shish
    actions = ['import_questions_action']

    # --- URL va VIEW Sozlamalari (IMPORT UCHUN) ---
    def get_urls(self):
        """Admin URL'lariga yangi import sahifasi uchun URL qo'shadi."""
        urls = super().get_urls()
        custom_urls = [
            # Yangi URL manzili: /admin/core/test/<test_id>/import-questions/
            path(
                '<int:test_id>/import-questions/',
                self.admin_site.admin_view(self.import_questions_view),
                name='core_test_import_questions'
            ),
        ]
        return custom_urls + urls

    # --- ADMIN ACTIONS (IMPORT TUGMASI) ---

    @admin.action(description='Tanlangan testga savollarni matndan import qilish')
    def import_questions_action(self, request, queryset):
        """Action orqali foydalanuvchini import sahifasiga yo'naltiradi."""
        # Faqat bitta test tanlangan bo'lishi shart
        if queryset.count() != 1:
            messages.error(request, "Iltimos, faqat bitta testni tanlang.")
            return

        test_instance = queryset.first()
        # Import sahifasiga yo'naltirish
        return redirect('admin:core_test_import_questions', test_id=test_instance.pk)

    # --- CUSTOM VIEWS (IMPORT SAHIFASI) ---

    def import_questions_view(self, request, test_id):
        """Savollarni matndan import qilish formasini ko'rsatadi va mantiqni bajaradi."""
        try:
            test_instance = Test.objects.get(pk=test_id)
        except Test.DoesNotExist:
            messages.error(request, "Tanlangan test topilmadi.")
            return redirect('admin:core_test_changelist')

        if request.method == 'POST':
            form = QuestionImportForm(request.POST)
            if form.is_valid():
                raw_text = form.cleaned_data['import_data']

                importer = QuestionImporter(test_instance)
                try:
                    imported_count = importer.process_text(raw_text)
                    messages.success(request,
                                     f"Muvaffaqiyatli! {imported_count} ta savol va ularning variantlari '{test_instance.nom}' testiga qo'shildi.")
                except Exception as e:
                    messages.error(request, f"Import jarayonida xatolik yuz berdi: {e}")

                return redirect('admin:core_test_changelist')
        else:
            form = QuestionImportForm()

        context = self.admin_site.each_context(request)
        context.update({
            'title': f"Savollarni '{test_instance.nom}' testiga import qilish",
            'form': form,
            'test_instance': test_instance,  # Shablon uchun test ob'ekti
            'opts': self.model._meta,
            'has_permission': self.has_view_or_change_permission(request),
        })
        # Shablonni render qilish. (core/templates/admin/test_import_form.html)
        return render(request, 'admin/test_import_form.html', context)

    # --- Mavjud metodlar ---

    def manage_savollar(self, obj):
        url = reverse('admin:core_savol_changelist') + f'?test__id__exact={obj.id}'
        return format_html(f"<a class='button' href='{url}'>Savollarni boshqarish</a>")

    manage_savollar.short_description = "Savollar"


# ---------------- 5. Natijalar ----------------

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