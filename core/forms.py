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

class QuestionImportForm(forms.Form):
    """
    Test savollarini matn formatida import qilish uchun ishlatiladigan forma.
    """
    # Testga tegishli savollarni joylashtirish uchun katta matn maydoni
    import_data = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 20, 'cols': 120, 'placeholder': 'Savollarni matn formatida shu yerga nusxalash va joylashtirish.\nHar bir savol # raqami bilan, ball #ball: bilan va to\'g\'ri javob + belgisidan boshlanishi kerak (Masalan, +A) 8)'}),
        label="Savol va Variantlar Matni"
    )