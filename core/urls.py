# core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Kirish/Chiqish sahifalari (vaqtinchalik)
    path('', views.home_view, name='home'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    # O'quvchi Qismlari
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/tests/', views.student_test_list, name='student_test_list'),
    path('student/test/<int:test_id>/start/', views.test_start, name='test_start'),
    path('student/test/<int:test_id>/solve/', views.test_solve, name='test_solve'),
    path('student/test/<int:test_id>/review/<int:result_id>/', views.test_review, name='test_review'),

    # Admin Qismlari
    # (Hozircha admin uchun alohida views yozmaymiz, chunki barcha boshqaruv admin panelda)
]