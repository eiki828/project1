from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, F, Subquery, OuterRef, Max, Min
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, ListView, UpdateView, DetailView

from ..decorators import student_required
from ..forms import StudentlebelForm, StudentSignUpForm, TakeQuizForm
from ..models import Quiz, Student, TakenQuiz, User, Question, StudentAnswer
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
        # 本当はDistinctでQuizの単位で集約したかったが、
        # SQliteはDistinct未対応のため、仕方なくannotateで対応
        ids = self.request.user.student.taken_quizzes \
            .select_related('quiz', 'quiz__subject') \
            .values('student', 'quiz',) \
            .annotate(latest_id=Min('id')) \
            .order_by('quiz__name') \
            .values('latest_id')

        explanation_subquery = self.request.user \
            .student.taken_quizzes \
            .values('quiz') \
            .filter(quiz=OuterRef('quiz_id')) \
            .annotate(explanation_count=Count('quiz__questions__explanation'))

        queryset = self.request.user.student.taken_quizzes \
            .select_related('quiz', 'quiz__subject') \
            .filter(id__in=ids) \
            .annotate(explanation_count=Subquery(
                explanation_subquery.values('explanation_count'))) \
            .order_by('quiz__name')
        return queryset


class RetryQuizListView(StudentRequiredMixin, ListView):
    model = TakenQuiz
    context_object_name = 'retry_quizzes'
    template_name = 'classroom/students/retry_quiz_list.html'

    def get_queryset(self):
        student: Student = self.request.user.student

        subquery = self.request.user.student.taken_quizzes \
            .select_related('quiz') \
            .filter(quiz_id=OuterRef('quiz_id')) \
            .values('quiz') \
            .annotate(retry_num=Max('challenge_num')) \
            .order_by('quiz_id')

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
                try_num=Subquery(subquery.values('retry_num'))
            ) \
            .filter(challenge_num=F('try_num')).order_by('name')

        return queryset


class ExplanationListView(StudentRequiredMixin, ListView):
    model = Quiz
    context_object_name = 'questions'
    template_name = 'classroom/students/explanations_list.html'

    def get_queryset(self):
        queryset = Quiz.objects.get(pk=self.kwargs['pk']).questions.all()
        return queryset


class ExplanationDetailView(StudentRequiredMixin, DetailView):
    model = Question
    context_object_name = 'explanation'
    template_name = 'classroom/students/explanations_detail.html'

    def get_object(self, queryset=None):
        question = Question.objects.get(
            pk=self.kwargs['question_pk'])

        if hasattr(question, 'explanation'):
            return question.explanation

        return None


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
                    score = round((correct_answers / total_questions) * 100)
                    TakenQuiz.objects.create(
                        student=student, quiz=quiz, score=score)

                    if score < 50.0:
                        random_messages = [
                            "もう少し頑張ろう",
                            "調子を出していこう",
                            "頑張りが足りないみたいだね",
                        ]
                        random_message = random.choice(random_messages)
                        messages.warning(
                            request, f'{random_message} 点数は {score}')
                        random_message = ''

                    else:
                        random_messages = [
                            "頑張ったね、よくできました。",
                            "次のレベルに進んでみよう",
                            "満点目指してみよう！！",
                        ]
                        score = '-'
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


@login_required
@student_required
def retry_quiz(request, pk, challenge_num):
    quiz = get_object_or_404(Quiz, pk=pk)
    student: Student = request.user.student

    wrong_answers = student.get_latest_wrong_answers(quiz, challenge_num)
    total_questions = wrong_answers.count()

    answered_question = student.quiz_answers.filter(
        challenge_num=challenge_num+1,
        answer__question__quiz=quiz).values('answer__question')

    unanswered_questions = wrong_answers.exclude(
        answer__question__in=answered_question).order_by('?')

    # すべて回答済みの場合は再挑戦一覧に飛ばす
    if not unanswered_questions.exists():
        return redirect('students:retry_quiz_list')

    # 進捗
    total_unanswered_questions = unanswered_questions.count()
    progress = 100 - \
        round(((total_unanswered_questions - 1) / total_questions) * 100)

    if request.method == 'POST':
        # 回答がある問題を抽出
        question = Question.objects.filter(
            answers=request.POST.get('answer')).first()
        form = TakeQuizForm(question=question, data=request.POST)
        if form.is_valid():
            with transaction.atomic():
                student_answer = form.save(commit=False)
                student_answer.student = student
                student_answer.challenge_num = challenge_num + 1
                student_answer.save()
                if wrong_answers.exclude(
                        answer__question__in=answered_question).exists():
                    return redirect('students:retry_quiz', pk, challenge_num)
                else:
                    correct_answers = student.quiz_answers.filter(
                        challenge_num=challenge_num + 1,
                        answer__question__quiz=quiz,
                        answer__is_correct=True).count()
                    score = round((correct_answers / total_questions) * 100.0)
                    TakenQuiz.objects.create(
                        challenge_num=challenge_num+1,
                        student=student,
                        quiz=quiz,
                        score=score)

                    if score < 50.0:
                        random_messages = [
                            "もう少し頑張ろう",
                            "調子を出していこう",
                            "頑張りが足りないみたいだね",
                        ]
                        random_message = random.choice(random_messages)
                        messages.warning(
                            request, f'{random_message} 点数は {score}')
                    else:
                        random_message = ''
        else:
            random_messages = [
                "頑張ったね、よくできました。",
                "次のレベルに進んでみよう",
                "満点目指してみよう！！",
            ]
            random_message = random.choice(random_messages)
            score = '-'
        messages.success(request, f'{random_message}   点数は {score}')

        return redirect('students:retry_quiz_list')
    else:
        question = unanswered_questions.first().answer.question
        form = TakeQuizForm(question=question, order='?')

    return render(request, 'classroom/students/take_quiz_form.html', {
        'quiz': quiz,
        'question': question,
        'form': form,
        'progress': progress
    })
