from django import template
from classroom.models import Student, Question
from datetime import timedelta
register = template.Library()  # Djangoのテンプレートタグライブラリ

# カスタムフィルタとして登録する


@register.simple_tag
def get_latest_answer(student: Student, question: Question):
    return student.quiz_answers.filter(answer__question=question).order_by('-challenge_num').first()


@register.simple_tag
def timedelta_diplay(td: timedelta):
    total_sec = td.total_seconds()
    # 時間
    hours = total_sec // 3600
    # 残り分
    remain = total_sec - (hours * 3600)
    # 分
    minutes = remain // 60
    # 残り秒
    seconds = remain - (minutes * 60)
    # 合計時間
    result = ''
    if hours >= 1:
        result += f'{int(hours)}時間'

    if result != '' or minutes >= 1:
        result += f' {int(minutes)}分'

    if result != '' or seconds >= 1:
        result += f' {int(seconds)}秒'

    return result
