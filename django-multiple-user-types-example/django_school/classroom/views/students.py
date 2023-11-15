from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, F
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, ListView, UpdateView

from ..decorators import student_required
from ..forms import StudentlebelForm, StudentSignUpForm, TakeQuizForm
from ..models import Quiz, Student, TakenQuiz, User
from ..mixins import StudentRequiredMixin

import random
import math


class StudentSignUpView(CreateView):
    model = User
    form_class = StudentSignUpForm
    template_name = 'registration/signup_form.html'

    def get_context_data(self, **kwargs):
        kwargs['user_type'] = 'student'
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect('students:quiz_list')


class StudentlebelView(StudentRequiredMixin, UpdateView):
    model = Student
    form_class = StudentlebelForm
    template_name = 'classroom/students/lebel_form.html'
    success_url = reverse_lazy('students:quiz_list')

    def get_object(self):
        return self.request.user.student

    def form_valid(self, form):
        messages.success(self.request, 'レベル変更完了!')
        return super().form_valid(form)


class QuizListView(StudentRequiredMixin, ListView):
    model = Quiz
    ordering = ('name', )
    context_object_name = 'quizzes'
    template_name = 'classroom/students/quiz_list.html'

    def get_queryset(self):
        student = self.request.user.student
        student_lebel = student.lebel.values_list('pk', flat=True)
        taken_quizzes = student.quizzes.values_list('pk', flat=True)
        queryset = Quiz.objects.filter(subject__in=student_lebel) \
            .exclude(pk__in=taken_quizzes) \
            .annotate(questions_count=Count('questions')) \
            .filter(questions_count__gt=0)
        return queryset


class TakenQuizListView(StudentRequiredMixin, ListView):
    model = TakenQuiz
    context_object_name = 'taken_quizzes'
    template_name = 'classroom/students/taken_quiz_list.html'

    def get_queryset(self):
        queryset = self.request.user.student.taken_quizzes \
            .select_related('quiz', 'quiz__subject') \
            .order_by('quiz__name')
        return queryset


class RetryQuizListView(StudentRequiredMixin, ListView):
    model = TakenQuiz
    context_object_name = 'retry_quizzes'
    template_name = 'classroom/students/retry_quiz_list.html'

    def get_queryset(self):
        student: Student = self.request.user.student
        # クイズごとに集約を行う
        queryset = student.quiz_answers.\
            filter(answer__is_correct=False)\
            .values(
                'answer__question__quiz',
                'answer__question__quiz__name',
                'answer__question__quiz__subject__color',
                'answer__question__quiz__subject__name') \
            .annotate(  # 集約したときは親のテーブルのオブジェクトを取得できないので、各項目を出力していく
                not_corrected_count=Count('answer'),
                name=F('answer__question__quiz__name'),
                quiz_id=F('answer__question__quiz'),
                subject_color=F('answer__question__quiz__subject__color'),
                subject_name=F('answer__question__quiz__subject__name'),
            ) \
            .all().order_by('name')

        return queryset


@login_required
@student_required
def take_quiz(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk)
    student = request.user.student

    if student.quizzes.filter(pk=pk).exists():
        return render(request, 'students/taken_quiz.html')

    total_questions = quiz.questions.count()
    unanswered_questions = student.get_unanswered_questions(quiz)
    total_unanswered_questions = unanswered_questions.count()
    progress = 100 - \
        round(((total_unanswered_questions - 1) / total_questions) * 100)
    question = unanswered_questions.first()

    if request.method == 'POST':
        form = TakeQuizForm(question=question, data=request.POST)
        if form.is_valid():
            with transaction.atomic():
                student_answer = form.save(commit=False)
                student_answer.student = student
                student_answer.save()
                if student.get_unanswered_questions(quiz).exists():
                    return redirect('students:take_quiz', pk)
                else:
                    correct_answers = student.quiz_answers.filter(
                        answer__question__quiz=quiz, answer__is_correct=True).count()
                    score = round((correct_answers / total_questions) * 100.0)
                    TakenQuiz.objects.create(
                        student=student, quiz=quiz, score=score)

                    if score < 50.0:
                        random_messages = [
                            "もう少し頑張ろう",
                            "調子を出していこう",
                            "頑張りが足りないみたいだね",
                        ]
                    random_message = random.choice(random_messages)
                    messages.warning(request, f'{random_message} 点数は {score}')
        else:
            random_messages = [
                "頑張ったね、よくできました。",
                "次のレベルに進んでみよう",
                "満点目指してみよう！！",
            ]
        random_message = random.choice(random_messages)
        messages.success(request, f'{random_message}   点数は {score}')

        return redirect('students:quiz_list')
    else:
        form = TakeQuizForm(question=question)

    return render(request, 'classroom/students/take_quiz_form.html', {
        'quiz': quiz,
        'question': question,
        'form': form,
        'progress': progress
    })
