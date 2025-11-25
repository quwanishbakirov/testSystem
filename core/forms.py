# core/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm

class LoginForm(AuthenticationForm):
    """Tizimga kirish uchun standart forma."""
    username = forms.CharField(
        label="Login",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Login'})
    )
    password = forms.CharField(
        label="Parol",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Parol'})
    )