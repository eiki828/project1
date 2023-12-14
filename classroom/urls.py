from django.urls import include, path

from .views import classroom, students, teachers


urlpatterns = [
     path('', classroom.home, name='home'),

     path('students/', include(([
        path('', students.QuizListView.as_view(), name='quiz_list'),
        path('lebel/', students.StudentlebelView.as_view(), name='student_lebel'),
        path('taken/', students.TakenQuizListView.as_view(),
             name='taken_quiz_list'),
        path('retry/', students.RetryQuizListView.as_view(),
             name='retry_quiz_list'),
        path('quiz/<int:pk>/', students.take_quiz, name='take_quiz'),
        path('quiz/<int:pk>/explanation/',
             students.ExplanationListView.as_view(),
             name='quiz_explanation'),
        path('quiz/<int:pk>/explanation/<int:question_pk>/',
             students.ExplanationDetailView.as_view(),
             name='quiz_explanation_detail'),

        path('retry_quiz/<int:pk>/<int:challenge_num>',
             students.retry_quiz, name='retry_quiz'),
    ], 'classroom'), namespace='students')),

    path('teachers/', include(([
        path('', teachers.QuizListView.as_view(), name='quiz_change_list'),
        path('quiz/add/', teachers.QuizCreateView.as_view(), name='quiz_add'),
        path('quiz/<int:pk>/', teachers.QuizUpdateView.as_view(), name='quiz_change'),
        path('quiz/<int:pk>/delete/',
             teachers.QuizDeleteView.as_view(), name='quiz_delete'),
        path('quiz/<int:pk>/results/',
             teachers.QuizResultsView.as_view(), name='quiz_results'),
        path('quiz/<int:pk>/question/add/',
             teachers.question_add, name='question_add'),
        path('quiz/<int:quiz_pk>/question/<int:question_pk>/',
             teachers.question_change, name='question_change'),
        path('quiz/<int:quiz_pk>/question/<int:question_pk>/delete/',
             teachers.QuestionDeleteView.as_view(), name='question_delete'),
        path('quiz/<int:quiz_pk>/question/<int:question_pk>/explanation',
             teachers.ExplanationView.as_view(), name='explanation'),
        path('quiz/<int:quiz_pk>/question/<int:question_pk>/explanation/delete',
             teachers.ExplanationDeleteView.as_view(), name='explanation_delete'),
    ], 'classroom'), namespace='teachers')),
]
