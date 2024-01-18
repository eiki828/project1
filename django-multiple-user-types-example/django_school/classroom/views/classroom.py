from django.shortcuts import redirect, render
from django.views.generic import TemplateView
from django.contrib.auth import authenticate, login

from ..forms import StudentSignUpForm


class SignUpView(TemplateView):
    template_name = 'registration/signup.html'


def home(request):
    context = {}
    if request.method == 'POST':
        if 'login' in request.POST:
            user = _login(request)
            if user is None:
                context['error_message'] = 'ユーザーIDまたは、パスワードが誤っています。'
        if 'signup' in request.POST:
            form = StudentSignUpForm(request.POST)
            context['signup_form'] = form  # アカウント作成に失敗したらフォームを画面に返したいので
            if form.is_valid():
                form.save()
                user = authenticate(
                    request,
                    username=form.cleaned_data['username'],
                    password=form.cleaned_data['password1'])
                login(request, user)

    else:
        context['signup_form'] = StudentSignUpForm()

    if request.user.is_authenticated:
        if request.user.is_teacher:
            return redirect('teachers:quiz_change_list')
        else:
            return redirect('students:quiz_list')

    return render(request, 'classroom/home.html', context)


def _login(request):
    username = request.POST["username"]
    password = request.POST["password"]
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        # Redirect to a success page.
        return user
    else:
        # Return an 'invalid login' error message.
        ...
