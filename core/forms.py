from django import forms
from django.contrib.auth.models import User
from .models import UserProfile, Session, Review


class RegisterForm(forms.Form):
    fullName = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    confirmPassword = forms.CharField(widget=forms.PasswordInput)
    role = forms.ChoiceField(choices=[('learner', 'Learner'), ('tutor', 'Tutor')])

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm = cleaned_data.get('confirmPassword')
        if password and confirm and password != confirm:
            raise forms.ValidationError("Passwords do not match.")
        email = cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return cleaned_data


class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    role = forms.ChoiceField(choices=[('learner', 'Learner'), ('tutor', 'Tutor')], required=False)


class OTPForm(forms.Form):
    otp = forms.CharField(max_length=6, min_length=6)


class ProfileEditForm(forms.ModelForm):
    full_name = forms.CharField(max_length=150, required=False)

    class Meta:
        model = UserProfile
        fields = ['bio', 'expertise', 'demo_video', 'linkedin', 'github', 'skills']
        widgets = {
            'skills': forms.CheckboxSelectMultiple,
        }


class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ['title', 'description', 'skill', 'level', 'date', 'start_time', 'end_time',
                  'credits_required', 'session_type', 'max_participants']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
