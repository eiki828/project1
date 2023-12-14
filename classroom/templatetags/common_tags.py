from django import template
from classroom.models import Student, Question
register = template.Library()  # Djangoのテンプレートタグライブラリ

# カスタムフィルタとして登録する


@register.simple_tag
def get_latest_answer(student: Student, question: Question):
    return student.quiz_answers.filter(answer__question=question).order_by('-challenge_num').first()
