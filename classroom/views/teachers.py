from typing import Any
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Count
from django.forms import inlineformset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  UpdateView, FormView)

from ..decorators import teacher_required
from ..forms import (BaseAnswerInlineFormSet, QuestionForm, TeacherSignUpForm,
                     ExplanationForm)
from ..models import Answer, Question, Quiz, User, Explanation
from ..mixins import TeacherRequiredMixin


class TeacherSignUpView(CreateView):
    model = User
    form_class = TeacherSignUpForm
    template_name = 'registration/signup_form.html'

    def get_context_data(self, **kwargs):
        kwargs['user_type'] = 'teacher'
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect('teachers:quiz_change_list')


class QuizListView(TeacherRequiredMixin, ListView):
    model = Quiz
    ordering = ('name', )
    context_object_name = 'quizzes'
    template_name = 'classroom/teachers/quiz_change_list.html'

    def get_queryset(self):
        queryset = self.request.user.quizzes \
            .select_related('subject') \
            .annotate(questions_count=Count('questions', distinct=True)) \
            .annotate(taken_count=Count('taken_quizzes', distinct=True))
        return queryset


class QuizCreateView(TeacherRequiredMixin, CreateView):
    model = Quiz
    fields = ('name', 'subject', )
    template_name = 'classroom/teachers/quiz_add_form.html'

    def form_valid(self, form):
        quiz = form.save(commit=False)
        quiz.owner = self.request.user
        quiz.save()
        messages.success(
            self.request, 'The quiz was created with success! Go ahead and add some questions now.')
        return redirect('teachers:quiz_change', quiz.pk)


class QuizUpdateView(TeacherRequiredMixin, UpdateView):
    model = Quiz
    fields = ('name', 'subject', )
    context_object_name = 'quiz'
    template_name = 'classroom/teachers/quiz_change_form.html'

    def get_context_data(self, **kwargs):
        kwargs['questions'] = self.get_object().questions.annotate(
            answers_count=Count('answers'))
        return super().get_context_data(**kwargs)

    def get_queryset(self):
        '''
        This method is an implicit object-level permission management
        This view will only match the ids of existing quizzes that belongs
        to the logged in user.
        '''
        return self.request.user.quizzes.all()

    def get_success_url(self):
        return reverse('teachers:quiz_change', kwargs={'pk': self.object.pk})


class QuizDeleteView(TeacherRequiredMixin, DeleteView):
    model = Quiz
    context_object_name = 'quiz'
    template_name = 'classroom/teachers/quiz_delete_confirm.html'
    success_url = reverse_lazy('teachers:quiz_change_list')

    def delete(self, request, *args, **kwargs):
        quiz = self.get_object()
        messages.success(
            request, 'The quiz %s was deleted with success!' % quiz.name)
        return super().delete(request, *args, **kwargs)

    def get_queryset(self):
        return self.request.user.quizzes.all()


class QuizResultsView(TeacherRequiredMixin, DetailView):
    model = Quiz
    context_object_name = 'quiz'
    template_name = 'classroom/teachers/quiz_results.html'

    def get_context_data(self, **kwargs):
        quiz = self.get_object()
        taken_quizzes = quiz.taken_quizzes.select_related(
            'student__user').order_by('-date')
        total_taken_quizzes = taken_quizzes.count()
        quiz_score = quiz.taken_quizzes.aggregate(average_score=Avg('score'))
        extra_context = {
            'taken_quizzes': taken_quizzes,
            'total_taken_quizzes': total_taken_quizzes,
            'quiz_score': quiz_score
        }
        kwargs.update(extra_context)
        return super().get_context_data(**kwargs)

    def get_queryset(self):
        return self.request.user.quizzes.all()


@login_required
@teacher_required
def question_add(request, pk):
    # By filtering the quiz by the url keyword argument `pk` and
    # by the owner, which is the logged in user, we are protecting
    # this view at the object-level. Meaning only the owner of
    # quiz will be able to add questions to it.
    quiz = get_object_or_404(Quiz, pk=pk, owner=request.user)

    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.quiz = quiz
            question.save()
            messages.success(request, '問題を追加')
            return redirect('teachers:question_change', quiz.pk, question.pk)
    else:
        form = QuestionForm()

    return render(request, 'classroom/teachers/question_add_form.html', {'quiz': quiz, 'form': form})


@login_required
@teacher_required
def question_change(request, quiz_pk, question_pk):
    # Simlar to the `question_add` view, this view is also managing
    # the permissions at object-level. By querying both `quiz` and
    # `question` we are making sure only the owner of the quiz can
    # change its details and also only questions that belongs to this
    # specific quiz can be changed via this url (in cases where the
    # user might have forged/player with the url params.
    quiz = get_object_or_404(Quiz, pk=quiz_pk, owner=request.user)
    question = get_object_or_404(Question, pk=question_pk, quiz=quiz)

    AnswerFormSet = inlineformset_factory(
        Question,  # parent model
        Answer,  # base model
        formset=BaseAnswerInlineFormSet,
        fields=('text', 'is_correct'),
        min_num=2,
        validate_min=True,
        max_num=10,
        validate_max=True
    )

    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        formset = AnswerFormSet(request.POST, instance=question)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                formset.save()
            messages.success(request, '問題データのセーブ完了！')
            return redirect('teachers:quiz_change', quiz.pk)
    else:
        form = QuestionForm(instance=question)
        formset = AnswerFormSet(instance=question)

    return render(request, 'classroom/teachers/question_change_form.html', {
        'quiz': quiz,
        'question': question,
        'form': form,
        'formset': formset
    })


class QuestionDeleteView(TeacherRequiredMixin, DeleteView):
    model = Question
    context_object_name = 'question'
    template_name = 'classroom/teachers/question_delete_confirm.html'
    pk_url_kwarg = 'question_pk'

    def get_context_data(self, **kwargs):
        question = self.get_object()
        kwargs['quiz'] = question.quiz
        return super().get_context_data(**kwargs)

    def delete(self, request, *args, **kwargs):
        question = self.get_object()
        messages.success(
            request, 'The question %s was deleted with success!' % question.text)
        return super().delete(request, *args, **kwargs)

    def get_queryset(self):
        return Question.objects.filter(quiz__owner=self.request.user)

    def get_success_url(self):
        question = self.get_object()
        return reverse('teachers:quiz_change', kwargs={'pk': question.quiz_id})


class ExplanationView(TeacherRequiredMixin, FormView):
    template_name = 'classroom/teachers/explanation_form.html'
    form_class = ExplanationForm

    def _get_question(self) -> Question:
        return Question.objects.get(
            pk=self.kwargs['question_pk'])

    def get_success_url(self):
        question = self._get_question()
        return reverse('teachers:question_change', kwargs={'quiz_pk': question.quiz.pk, 'question_pk': question.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        question = Question.objects.get(
            pk=self.kwargs['question_pk'])
        context['question'] = question

        return context

    def form_valid(self, form):
        explanation = form.save(commit=False)
        if explanation.pk is None:
            explanation.question = self._get_question()
        explanation.save()

        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        question = Question.objects.get(
            pk=self.kwargs['question_pk'])

        # 解説がすでにある場合は、引っ張ってくる
        if hasattr(question, 'explanation'):
            kwargs.update({
                'instance': question.explanation
            })

        return kwargs


class ExplanationDeleteView(TeacherRequiredMixin, DeleteView):
    model = Explanation
    context_object_name = 'explanation'
    template_name = 'classroom/teachers/explanation_delete_confirm.html'
    pk_url_kwarg = 'question_pk'

    def get_object(self, queryset=None):
        question = Question.objects.get(pk=self.kwargs['question_pk'])

        if hasattr(question, 'explanation'):
            return question.explanation

        return None

    def get_context_data(self, **kwargs):
        explanation = self.get_object()
        kwargs['quiz'] = explanation.question.quiz
        return super().get_context_data(**kwargs)

    def get(self, request, *args, **kwargs):
        explanation = self.get_object()
        form = ExplanationForm(
            initial={
                'text': explanation.text,
            }
        )

        return render(request, 'classroom/teachers/explanation_form.html', {
            'form': form,
            'explanation': explanation,
        })

    def post(self, request, *args, **kwargs):
        form = ExplanationForm(request.POST, request.FILES)

        if form.is_valid():
            explanation = self.get_object()
            explanation.text = form.cleaned_data['text']
            if request.FILES:
                explanation.image = request.FILES.get('image')
            explanation.save()
            messages.success(request, 'The question explanation was updated with success!')
            return redirect('teachers:question_change', quiz_pk=explanation.question.quiz.pk, question_pk=explanation.question.pk)

        return render(request, 'classroom/teachers/explanation_form.html', {
            'form': form,
            'explanation': self.get_object(),
        })

    def delete(self, request, *args, **kwargs):
        messages.success(
            request, 'The question explanation was deleted with success!')
        return super().delete(request, *args, **kwargs)

    def get_queryset(self):
        return Question.objects.filter(quiz__owner=self.request.user)

    def get_success_url(self):
        explanation = self.get_object()
        return reverse('teachers:question_change', kwargs={'quiz_pk': explanation.question.quiz.pk, 'question_pk': explanation.question.pk})

