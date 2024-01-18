from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.query import QuerySet
from django.utils.html import escape, mark_safe


class User(AbstractUser):
    is_student = models.BooleanField(default=False)
    is_teacher = models.BooleanField(default=False)


class Subject(models.Model):
    name = models.CharField(max_length=30)
    color = models.CharField(max_length=7, default='#007bff')

    def __str__(self):
        return self.name

    def get_html_badge(self):
        name = escape(self.name)
        color = escape(self.color)
        html = '<span class="badge badge-primary" style="background-color: %s">%s</span>' % (
            color, name)
        return mark_safe(html)


class Quiz(models.Model):
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='quizzes')
    name = models.CharField(max_length=255)
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name='quizzes')

    def __str__(self):
        return self.name


class Question(models.Model):
    quiz = models.ForeignKey(
        Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.CharField('Question', max_length=255)

    def __str__(self):
        return self.text


class Answer(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name='answers')
    text = models.CharField('Answer', max_length=255)
    is_correct = models.BooleanField('Correct answer', default=False)

    def __str__(self):
        return self.text


class Student(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, primary_key=True)
    quizzes = models.ManyToManyField(Quiz, through='TakenQuiz')
    lebel = models.ManyToManyField(Subject, related_name='interested_students')

    def get_unanswered_questions(self, quiz):
        answered_questions = self.quiz_answers \
            .filter(answer__question__quiz=quiz) \
            .values_list('answer__question__pk', flat=True)
        questions = quiz.questions.exclude(
            pk__in=answered_questions).order_by('text')
        return questions

    def get_latest_wrong_answers(self, quiz, challenge_num) -> 'QuerySet[StudentAnswer]':
        # 最後に挑戦した問題のうち間違えた問題のみを抽出する
        return self.quiz_answers.filter(
            challenge_num=challenge_num,
            answer__question__quiz=quiz,
            answer__is_correct=False)

    def __str__(self):
        return self.user.username


class TakenQuiz(models.Model):
    challenge_num = models.IntegerField(default=1)
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='taken_quizzes')
    quiz = models.ForeignKey(
        Quiz, on_delete=models.CASCADE, related_name='taken_quizzes')
    score = models.FloatField()
    date = models.DateTimeField(auto_now_add=True)

    @property
    def taken_time(self):
        """ 問題を解くのにかかった時間 """
        try:
            taken_time = TakenTime.objects.get(
                student=self.student, quiz=self.quiz)
            if taken_time.take_end is not None and taken_time.take_start is not None:
                return taken_time.take_end - taken_time.take_start
            else:
                return None
        except TakenTime.DoesNotExist:
            return None


class StudentAnswer(models.Model):
    challenge_num = models.IntegerField(default=1)
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='quiz_answers')
    answer = models.ForeignKey(
        Answer, on_delete=models.CASCADE, related_name='+')


class TakenTime(models.Model):
    take_start = models.DateTimeField(null=True, blank=True)
    take_end = models.DateTimeField(null=True, blank=True)
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='taken_time')
    quiz = models.ForeignKey(
        Quiz, on_delete=models.CASCADE, related_name='taken_time')


class Explanation(models.Model):
    """ 設問の解説 """
    question = models.OneToOneField(
        Question, on_delete=models.CASCADE, related_name='explanation')
    text = models.TextField()
