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

    # presentation-related URLs
    path('presentation/<int:pk>/', views.StudentPresentationView.as_view(), name='student_present_detail'),

    # teacher URLs
    # teacher dashboard
    path('dashboard/', views.TeacherDashboardView.as_view(), name='teacher_dashboard'),

    # teacher class-related URLs
    path('teacher/class/<int:id>/', views.TeacherClassView.as_view(), name='teacher_class'),
    path('teacher/class/delete/<int:pk>/', views.ClassDeleteView.as_view(), name='class_delete'),
    path('teacher/class/create/', views.ClassCreateView.as_view(), name='class_create'),
    path('teacher/class/<int:pk>/join-requests/', views.ClassJoinListView.as_view(), name='class_requests_list'),
    path('teacher/class/<int:pk>/join-requests/accept/<int:r_pk>/', views.ClassJoinAcceptView.as_view(), name='class_request_accept'),
    path('teacher/class/<int:pk>/join-requests/reject/<int:r_pk>/', views.ClassJoinRejectView.as_view(), name='class_request_reject'),

    # teacher exam-related URLs
    path('teacher/exam/', views.TeacherExamListView.as_view(), name='teacher_exams'),
    path('teacher/exam/delete/<int:pk>/', views.ExamDeleteView.as_view(), name='exam_delete'),
    path('teacher/exam/create/', views.ExamCreateView.as_view(), name='exam_create'),
    path('teacher/exam/<int:pk>/', views.TeacherExamDetailView.as_view(), name='teacher_exam'),

    # teacher exam-score-related URLs
    path('teacher/exam/<int:pk>/scores/', views.ExamScoresListView.as_view(), name='exam_scores'),
    path('teacher/exam/<int:pk>/scores/out/', views.exam_excel_output, name='exam_scores_out'),

    # part-related URLs
    path('teacher/part/delete/<int:pk>/', views.PartDeleteView.as_view(), name='part_delete'),
    path('teacher/<int:pk>/part/create/', views.PartCreateView.as_view(), name='part_create'),
    path('teacher/part/<int:pk>/update/', views.PartUpdateView.as_view(), name='part_update'),

    # question-related URLs
    path('teacher/question/delete/<int:pk>/', views.QuestionDeleteView.as_view(), name='question_delete'),
    path('teacher/<int:pk>/question/create/', views.QuestionCreateView.as_view(), name='question_create'),
    path('teacher/question/<int:pk>/update/', views.QuestionUpdateView.as_view(), name='question_update'),
    path('teacher/exam/<int:pk>/change_answer/<int:p>/<int:q>/', views.QuestionAnswerChange.as_view(), name='question_answer_change'),

    # choice-related URLs
    path('teacher/choice/delete/<int:pk>/', views.ChoiceDeleteView.as_view(), name='choice_delete'),
    path('teacher/<int:pk>/choice/create/', views.ChoiceCreateView.as_view(), name='choice_create'),
    path('teacher/choice/<int:pk>/update/', views.ChoiceUpdateView.as_view(), name='choice_update'),

    # way-related URLs
    path('teacher/class/<int:pk>/ways/', views.ClassWayListView.as_view(), name='class_ways'),
    path('teacher/way/<int:pk>/', views.WayDetailView.as_view(), name='teacher_way'),
    path('teacher/way/<int:pk>/add-exam/', views.WayAddExamView.as_view(), name='way_add_exam'),
    path('teacher/way/<int:pk>/add-present/', views.WayAddPresentView.as_view(), name='way_add_present'),
    path('teacher/way/<int:pk>/move/<str:move>/', views.WayMoveActivity.as_view(), name='way_move_up'),
    path('teacher/way/<int:pk>/delete/', views.WayDeleteActivity.as_view(), name='way_delete'),
    path('teacher/class/<int:pk>/way/create/', views.WayCreateView.as_view(), name='way_create'),
    path('teacher/way/delete/<int:pk>/', views.WayDeleteView.as_view(), name='way_delete_way'),

    # presentation-related URLs
    path('teacher/presentation/', views.TeacherPresentationsListView.as_view(), name='teacher_presents'),
    path('teacher/presentation/create/', views.PresentationCreateView.as_view(), name='present_create'),
    path('teacher/presentation/<int:pk>/delete/', views.PresentationDeleteView.as_view(), name='present_delete'),
    path('teacher/presentation/<int:pk>/', views.PresentationDetailView.as_view(), name='present_detail'),

    # slide-related URLs
    path('teacher/slide/<int:pk>/delete/', views.SlideDeleteView.as_view(), name='slide_delete'),
    path('teacher/presentation/<int:pk>/slide/create/', views.SlideCreateView.as_view(), name='slide_create'),
    path('teacher/slide/<int:pk>/update/', views.SlideUpdateView.as_view(), name='slide_update'),
]
