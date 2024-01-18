from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.core.exceptions import ValidationError

from classroom.models import (Answer, Question, Student, StudentAnswer,
                              Subject, User, Explanation)


class TeacherSignUpForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_teacher = True
        if commit:
            user.save()
        return user


class Hoge(forms.CheckboxSelectMultiple):
    template_name = "classroom/students/multiple_input.html"
    option_template_name = "classroom/students/input_option.html"


class StudentSignUpForm(UserCreationForm):
    lebel = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.all(),
        widget=Hoge(attrs={'class': "reset"}),
        required=True
    )

    class Meta(UserCreationForm.Meta):
        model = User

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError(
                self.error_messages["password_mismatch"],
                code="password_mismatch",
            )
        return password2

    @transaction.atomic
    def save(self):
        user = super().save(commit=False)
        user.is_student = True
        user.save()
        student = Student.objects.create(user=user)
        student.lebel.add(*self.cleaned_data.get('lebel'))
        return user


class StudentSignUpUnConfirmationPasswordForm(UserCreationForm):
    lebel = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "password", "lebel")

    @transaction.atomic
    def save(self):
        user = super().save(commit=False)
        user.is_student = True
        user.save()
        student = Student.objects.create(user=user)
        student.lebel.add(*self.cleaned_data.get('lebel'))
        return user

    def clean_password2(self):
        ...  # 確認用パスワードは気にしないことにする


class StudentlebelForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ('lebel', )
        widgets = {
            'lebel': forms.CheckboxSelectMultiple
        }


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ('text', )


class BaseAnswerInlineFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()

        has_one_correct_answer = False
        for form in self.forms:
            if not form.cleaned_data.get('DELETE', False):
                if form.cleaned_data.get('is_correct', False):
                    has_one_correct_answer = True
                    break
        if not has_one_correct_answer:
            raise ValidationError('最低でも答えを1つ選んでください', code='no_correct_answer')


class TakeQuizForm(forms.ModelForm):
    answer = forms.ModelChoiceField(
        queryset=Answer.objects.none(),
        widget=forms.RadioSelect(),
        required=True,
        empty_label=None)

    class Meta:
        model = StudentAnswer
        fields = ('answer', )

    def __init__(self, *args, **kwargs):
        question = kwargs.pop('question')
        order = kwargs.pop('order', 'text')
        super().__init__(*args, **kwargs)
        self.fields['answer'].queryset = question.answers.order_by(order)


class ExplanationForm(forms.ModelForm):
    # image = forms.ImageField(label='イメージ画像', required=False) # 追加

    class Meta:

        model = Explanation
        fields = ('text', 'image')
        labels = {
            'text': '解説文入力',
        }
        widgets = {
            'text': forms.Textarea(attrs={'placeholder': '解説文をここに入力'}),
        }
