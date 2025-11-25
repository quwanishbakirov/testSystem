from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Count  # Count va Sum kerak
from .forms import LoginForm
from .models import CustomUser, Sinf, StudentProfile, Test, TestResult, Savol, StudentAnswer, \
    Variant  # Kerakli modellar


# -------------------- Yordamchi Funksiyalar --------------------

def is_student(user):
    """O'quvchiligini tekshiradigan dekorator yordamchisi."""
    return user.is_authenticated and user.is_student


# -------------------- Autentifikatsiya Views --------------------

def user_login(request):
    """Foydalanuvchi tizimga kirishi."""
    if request.user.is_authenticated:
        if request.user.is_student:
            return redirect('student_dashboard')
        elif request.user.is_admin or request.user.is_superuser:
            return redirect('admin:index')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)
                if user.is_student:
                    messages.success(request, f"Xosh keldińiz, {user.username}!")
                    return redirect('student_dashboard')
                elif user.is_admin or user.is_superuser:
                    messages.success(request, f"Admin panelge xosh keldińiz, {user.username}!")
                    return redirect('admin:index')
            else:
                messages.error(request, 'Nadurıs login yamasa parol.')
        else:
            messages.error(request, 'Kirisiw maǵlıwmatların tekseriń.')
    else:
        form = LoginForm()

    return render(request, 'core/login.html', {'form': form})


@login_required
def user_logout(request):
    """Foydalanuvchi tizimdan chiqishi."""
    logout(request)
    messages.info(request, "Siz sayttan shıqtıńız.")
    return redirect('login')


def home_view(request):
    """Asosiy sahifa (Login sahifasiga yo'naltiramiz)."""
    return redirect('login')


# -------------------- Student Views --------------------

@login_required
@user_passes_test(is_student)
def student_dashboard(request):
    """O'quvchi bosh sahifasi (Rating ko'rsatiladi)."""
    student_profile = get_object_or_404(StudentProfile, user=request.user)
    student_sinf = student_profile.sinf

    if student_sinf:
        # Ratingni hisoblash (Faqat o'z sinfidagi o'quvchilar)
        rating_list = StudentProfile.objects.filter(sinf=student_sinf).order_by('-total_points')

        rank = 0
        for i, profile in enumerate(rating_list):
            if profile.user.id == request.user.id:
                rank = i + 1
                break
    else:
        rating_list = None
        rank = 0

    all_tests = Test.objects.filter(sinf=student_sinf).count() if student_sinf else 0
    solved_tests = TestResult.objects.filter(student=student_profile).count()

    context = {
        'student_profile': student_profile,
        'sinf_nomi': student_sinf.nom if student_sinf else "Klass belgilenbegen",
        'rating_list': rating_list,
        'my_rank': rank,
        'all_tests_count': all_tests,
        'solved_tests_count': solved_tests,
    }
    return render(request, 'core/student_dashboard.html', context)


@login_required
@user_passes_test(is_student)
def student_test_list(request):
    """O'quvchining sinfiga tegishli testlar ro'yxatini ko'rsatadi."""
    student_profile = get_object_or_404(StudentProfile, user=request.user)
    student_sinf = student_profile.sinf

    if not student_sinf:
        messages.error(request, "Klasıńız belgilenbegen. Iltimas, administratorǵa xabarlasıń.")
        return redirect('student_dashboard')

    all_tests = Test.objects.filter(sinf=student_sinf).annotate(
        total_questions=Count('savollar')  # Agar Savol modelida Test uchun related_name='savollar' bo'lsa
    ).order_by('-yaratilgan_sana')

    solved_test_ids = TestResult.objects.filter(student=student_profile).values_list('test_id', flat=True)

    tests_with_status = []
    for test in all_tests:
        status = 'Yechilmagan'
        result_id = None

        if test.id in solved_test_ids:
            # TestResult allaqachon mavjud bo'lsa, uni olish
            result = TestResult.objects.filter(student=student_profile, test=test).first()
            if result:
                status = f"Sheshilgen ({result.jami_ball} ball)"
                result_id = result.id

        tests_with_status.append({
            'test': test,
            'status': status,
            'solved': test.id in solved_test_ids,
            'result_id': result_id,
            'total_questions': test.total_questions,
        })

    context = {
        'tests_with_status': tests_with_status,
        'sinf_nomi': student_sinf.nom,
    }
    return render(request, 'core/student_test_list.html', context)


@login_required
@user_passes_test(is_student)
def test_start(request, test_id):
    """Testni boshlashdan oldingi tasdiqlash sahifasi."""
    student_profile = get_object_or_404(StudentProfile, user=request.user)
    test = get_object_or_404(Test, id=test_id, sinf=student_profile.sinf)  # Testni sinf orqali tekshirish

    # 1. TESTNI AVVAL YECHILGANLIGINI TEKSHIRISH
    if TestResult.objects.filter(student=student_profile, test=test).exists():
        result = TestResult.objects.get(student=student_profile, test=test)
        messages.info(request, "Siz bul testti aldın sheshkensiz. Nátiyjeni kóriwińiz múmkin.")
        return redirect('test_review', test_id=test.id, result_id=result.id)

    # 2. GET so'rovi (Testni boshlashdan oldingi tasdiqlash sahifasi)
    if request.method == 'GET':
        context = {
            'test': test,
            'test_id': test_id,
            'savollar_soni': test.savollar.count()
        }
        return render(request, 'core/test_start.html', context)

    # 3. POST so'rovi (Testni haqiqatda boshlash)
    elif request.method == 'POST':
        return redirect('test_solve', test_id=test.id)

    return redirect('student_test_list')


# -------------------- ASOSIY YECHIM: Tekshirish Logikasi --------------------

@login_required
@user_passes_test(is_student)
def test_solve(request, test_id):
    """O'quvchiga test savollarini ko'rsatish va javoblarni qabul qilish hamda hisoblash."""
    student_profile = get_object_or_404(StudentProfile, user=request.user)
    # Sinfga mosligini tekshirish muhim
    test = get_object_or_404(Test, id=test_id, sinf=student_profile.sinf)

    # 1. Avval yechilganlikni tekshirish
    if TestResult.objects.filter(student=student_profile, test=test).exists():
        result = TestResult.objects.filter(student=student_profile,
                                           test=test).last()  # Agar bir nechta bo'lsa oxirgisini olamiz
        messages.info(request, "Siz bul testti aldın sheshkensiz.")
        return redirect('test_review', test_id=test.id, result_id=result.id)

    # GET so'rovida savollarni ko'rsatish
    if request.method == 'GET':
        savollar_with_variants = test.savollar.all().prefetch_related('variantlar')
        context = {
            'test': test,
            'savollar': savollar_with_variants,
        }
        return render(request, 'core/test_solve.html', context)

    # POST so'rovida javoblarni tekshirish va saqlash
    elif request.method == 'POST':
        # 1. Natijalarni hisoblash uchun boshlang'ich o'zgaruvchilar
        total_score = 0
        correct_answers_count = 0
        total_questions = test.savollar.count()
        student_answers_to_create = []

        # ** TUZATISH 1: TestResult yaratishni javoblar saqlanishidan OLDIN qilamiz
        # Lekin ballar hisoblangandan keyin uni yangilaymiz.
        # SQLite'da bulk_create orqali bog'lanish uchun avval TestResult yozilishi kerak.
        # Biz bu yerda to'g'ridan-to'g'ri hisob-kitobni qilib, keyin TestResultni yaratamiz,
        # shunda bitta INSERT so'rovi ketadi (UPDATE kerak bo'lmaydi).

        for savol in test.savollar.all():
            input_name = f'savol_{savol.id}'
            selected_variant_id = request.POST.get(input_name)

            if not selected_variant_id:
                continue

            try:
                # Variantni savolga tegishliligini tekshirib olamiz
                selected_variant = Variant.objects.get(id=selected_variant_id, savol=savol)
            except Variant.DoesNotExist:
                continue

            # To'g'ri javobni tekshirish
            is_correct = selected_variant.is_correct

            if is_correct:
                # Agar to'g'ri bo'lsa, ballarni hisoblash
                total_score += savol.ball  # Yoki savol.ball
                correct_answers_count += 1

            # StudentAnswer ob'ektini faqat yaratish uchun listga qo'shamiz
            # Hozircha 'result' maydoni bo'sh.
            answer = StudentAnswer(
                # result=None (keyin TestResult obyektiga biriktiriladi)
                savol=savol,
                tanlangan_variant=selected_variant,
                is_correct=is_correct
            )
            student_answers_to_create.append(answer)

        # 2. TestResult (Umumiy Natija) ni YARATISH (hisoblangan ballar bilan)
        # Endi bizda to'g'ri ballar mavjud
        test_result = TestResult.objects.create(
            student=student_profile,
            test=test,
            jami_ball=total_score,
            umumiy_savollar_soni=total_questions,
            togri_javoblar_soni=correct_answers_count,
        )

        # 3. StudentAnswer (Detalli Javoblar) ni saqlash uchun tayyorlash
        # ** TUZATISH 2: StudentAnswer ob'ektlariga test_result'ni biriktirish
        for answer in student_answers_to_create:
            # Foreign Key maydonining nomi odatda 'result' deb nomlanadi (TestResult.result).
            # Agar sizning modelingizda 'result' bo'lsa, 'answer.result = test_result' bo'ladi.
            # Agar sizning modelingizda TestResultga bog'lanuvchi maydon 'result' bo'lsa, quyidagini ishlatamiz.
            # Aks holda, modelingizga qarang va to'g'ri nomni toping.

            # Tracebackda core_studentanswer.result_id ishlatilgan,
            # shuning uchun modelda Foreign Key nomi 'result' deb taxmin qilamiz:
            answer.result = test_result
            # Eslatma: Agar modeliingizda nomi 'test_result' bo'lsa, 'answer.test_result = test_result' bo'ladi.

        # bulk_create faqat ob'ektlarni saqlaydi, endi ularning 'result' maydoni to'liq
        if student_answers_to_create:
            StudentAnswer.objects.bulk_create(student_answers_to_create)

        # 4. O'quvchi profili balini yangilash
        total_points_sum = TestResult.objects.filter(student=student_profile).aggregate(Sum('jami_ball'))[
            'jami_ball__sum']
        student_profile.total_points = total_points_sum or 0
        student_profile.save()

        messages.success(request,
                         f"Test tamamlandı. Siz {total_questions} dana sorawdan {correct_answers_count} danasına durıs juwap berdińiz! ({total_score} ball)")

        # Natija sahifasiga yo'naltirish
        return redirect('test_review', test_id=test.id, result_id=test_result.id)

    return redirect('student_test_list')


# core/views.py

@login_required
@user_passes_test(is_student)
def test_review(request, test_id, result_id):
    """Yechilgan test natijasining batafsil ko'rinishini taqdim etadi."""

    student_profile = get_object_or_404(StudentProfile, user=request.user)

    # Faqat o'sha o'quvchining shu testdagi natijasi ekanligiga ishonch hosil qilish
    test_result = get_object_or_404(
        TestResult,
        id=result_id,
        test_id=test_id,
        student=student_profile
    )
    test = test_result.test

    # --- 1. Samarali Ma'lumotlarni Olish ---
    student_answers = StudentAnswer.objects.filter(
        result=test_result
    ).select_related('savol', 'tanlangan_variant')

    savollar_with_variants = test.savollar.all().prefetch_related('variantlar')

    # O'quvchi javoblarini tezkor qidirish uchun savol IDsi orqali lug'atga solish
    answers_map = {answer.savol_id: answer.tanlangan_variant for answer in student_answers}

    # --- 2. Ma'lumotlarni Lug'atga Aylantirish va Birlashtirish (list_class ni hisoblash) ---

    savollar_data = []

    for savol in savollar_with_variants:
        user_answer = answers_map.get(savol.id)  # Variant obyektini olamiz
        is_savol_correct = user_answer.is_correct if user_answer else False

        updated_variants = []

        for variant in savol.variantlar.all():

            # Variant tanlanganmi?
            is_selected = user_answer and variant.id == user_answer.id

            # list_class ni hisoblash
            list_class = ""
            if is_selected and variant.is_correct:
                list_class = "list-group-item-success fw-bold"
            elif is_selected and not variant.is_correct:
                list_class = "list-group-item-danger fw-bold"
            elif variant.is_correct:
                list_class = "list-group-item-info"

            # Variant obyektiga yangi atributlarni dinamik qo'shamiz
            # Bu yordamchi atributlar templateda to'g'ridan-to'g'ri ishlatiladi.
            variant.is_selected = is_selected
            variant.list_class = list_class

            updated_variants.append(variant)

        # Ma'lumotlarni shablon uchun yig'ish
        savollar_data.append({
            'savol': savol,
            'variantlar': updated_variants,  # Yangi atributlar qo'shilgan variantlar
            'user_answer': user_answer,  # Tanlangan Variant obyekti (yoki None)
            'is_correct': is_savol_correct,
            # To'g'ri variantni alohida olish (lekin biz buni variant.is_correct bilan ham tekshirishimiz mumkin)
            'correct_variant': savol.variantlar.filter(is_correct=True).first()
        })

    # --- 3. Contextni Shablonga Uzatish ---
    context = {
        'test': test,
        'test_result': test_result,
        'savollar_data': savollar_data,
    }

    return render(request, 'core/test_review.html', context)