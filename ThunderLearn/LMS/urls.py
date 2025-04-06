from django.urls import path
from . import views

urlpatterns = [
    # student URLs
    # student dashboard
    path('', views.dashboard, name='dashboard'),

    # student class-related URLs
    path('class/<int:id>/', views.class_detail, name='class_detail'),
    path('class/<int:id>/join/', views.ClassJoinView.as_view(), name='class_join'),

    # student way-related URLs
    path('way/<int:id>/', views.way_detail, name='way_detail'),

    # student exam-related URLs
    path('exam/<int:id>/', views.exam_view, name='exam_view'),
    path('exam/<int:id>/question/<int:q>/', views.QuestionView.as_view(), name='question_view'),
    path('exam/<int:id>/score/', views.UserScoreView.as_view(), name='user_score'),

    # teacher URLs
    # teacher dashboard
    path('dashboard/', views.TeacherDashboardView.as_view(), name='teacher_dashboard'),

    # teacher class-related URLs
    path('teacher/class/<int:id>/', views.TeacherClassView.as_view(), name='teacher_class'),
    path('teacher/class/delete/<int:pk>/', views.ClassDeleteView.as_view(), name='class_delete'),
    path('teacher/class/create/', views.ClassCreateView.as_view(), name='class_create'),

    # teacher exam-related URLs
    path('teacher/exam/', views.TeacherExamListView.as_view(), name='teacher_exams'),
    path('teacher/exam/delete/<int:pk>/', views.ExamDeleteView.as_view(), name='exam_delete'),
    path('teacher/exam/create/', views.ExamCreateView.as_view(), name='exam_create'),
    path('teacher/exam/<int:pk>/', views.TeacherExamDetailView.as_view(), name='teacher_exam'),

    # part-related URLs
    path('teacher/part/delete/<int:pk>/', views.PartDeleteView.as_view(), name='part_delete'),
    path('teacher/<int:pk>/part/create/', views.PartCreateView.as_view(), name='part_create'),
    path('teacher/part/<int:pk>/update/', views.PartUpdateView.as_view(), name='part_update'),

    # question-related URLs
    path('teacher/question/delete/<int:pk>/', views.QuestionDeleteView.as_view(), name='question_delete'),
    path('teacher/<int:pk>/question/create/', views.QuestionCreateView.as_view(), name='question_create'),
    path('teacher/question/<int:pk>/update/', views.QuestionUpdateView.as_view(), name='question_update'),

    # choice-related URLs
    path('teacher/choice/delete/<int:pk>/', views.ChoiceDeleteView.as_view(), name='choice_delete'),
    path('teacher/<int:pk>/choice/create/', views.ChoiceCreateView.as_view(), name='choice_create'),
    path('teacher/choice/<int:pk>/update/', views.ChoiceUpdateView.as_view(), name='choice_update'),

    # way-related URLs
    path('teacher/class/<int:pk>/ways/', views.ClassWayListView.as_view(), name='class_ways'),
    path('teacher/way/<int:pk>/', views.WayDetailView.as_view(), name='teacher_way'),
    path('teacher/way/<int:pk>/add-exam/', views.WayAddExamView.as_view(), name='way_add_exam'),
    path('teacher/way/<int:pk>/move/<str:move>/', views.WayMoveActivity.as_view(), name='way_move_up'),
    path('teacher/way/<int:pk>/delete/', views.WayDeleteActivity.as_view(), name='way_delete'),
]
