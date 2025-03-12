from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('class/<int:id>/', views.class_detail, name='class_detail'),
    path('way/<int:id>/', views.way_detail, name='way_detail'),
    path('exam/<int:id>/', views.exam_view, name='exam_view'),
    path('exam/<int:id>/question/<int:q>/', views.QuestionView.as_view(), name='question_view'),
    # path('exam/<int:id>/done/', views.ExamDoneView.as_view(), name='exam_done'),
    path('exam/<int:id>/score/', views.UserScoreView.as_view(), name='user_score'),
    path('dashboard/', views.TeacherDashboardView.as_view(), name='teacher_dashboard'),
    path('teacher/class/<int:id>/', views.TeacherClassView.as_view(), name='teacher_class'),
    path('teacher/class/delete/<int:pk>/', views.ClassDeleteView.as_view(), name='class_delete'),
    path('teacher/class/create/', views.ClassCreateView.as_view(), name='class_create'),
    path('class/<int:id>/join/', views.ClassJoinView.as_view(), name='class_join'),
    path('teacher/exam/', views.TeacherExamListView.as_view(), name='teacher_exams'),
    path('teacher/exam/delete/<int:pk>/', views.ExamDeleteView.as_view(), name='exam_delete'),
    path('teacher/exam/create/', views.ExamCreateView.as_view(), name='exam_create'),
    path('teacher/exam/<int:pk>/', views.TeacherExamDetailView.as_view(), name='teacher_exam'),
    path('teacher/part/delete/<int:pk>/', views.PartDeleteView.as_view(), name='part_delete'),
    path('teacher/<int:pk>/part/create/', views.PartCreateView.as_view(), name='part_create'),
    path('teacher/question/delete/<int:pk>/', views.QuestionDeleteView.as_view(), name='question_delete'),
    path('teacher/<int:pk>/question/create/', views.QuestionCreateView.as_view(), name='question_create'),
    path('teacher/choice/delete/<int:pk>/', views.ChoiceDeleteView.as_view(), name='choice_delete'),
]
