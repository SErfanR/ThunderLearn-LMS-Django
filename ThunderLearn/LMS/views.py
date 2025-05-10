# models and forms
from .models import (Classroom, Way, Exam, UserAnswer, UserScore, ExamAnswer,
                     Part, Question, Choice, ClassroomJoinRequest, Presentation, Slide)
from .forms import PresentationForm, SlideForm
# class-based views
from django.views import View
from django.views.generic.edit import DeleteView, CreateView
from django.views.generic import ListView, DetailView, TemplateView, UpdateView
from django.urls import reverse
from .default_views import DefaultUpdateView, DefaultCreateView
# redirecting and etc
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import HttpResponse
# messages
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
# login required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
# other modules
import json
import pandas as pd
import numpy as np


@login_required
def dashboard(request):
    """Route user to appropriate dashboard based on their group"""
    if request.user.groups.filter(name='Students').exists():
        return render(request, 'LMS/dashboard.html')
    return redirect('teacher_dashboard')


@login_required
def class_detail(request, id):
    """
    Show class details for students with permission checks.
    Uses get_object_or_404 to handle missing classes.
    """
    if not request.user.groups.filter(name='Students').exists():
        messages.error(request, 'شما به این صفحه دسترسی ندارید.')
        return redirect('dashboard')

    this_class = get_object_or_404(Classroom, id=id)

    return render(request, 'LMS/class_detail.html', {'class': this_class})


@login_required
def way_detail(request, id):
    """
    Show way details with activities for authorized students.
    Includes proper error handling for malformed activities JSON.
    """
    if not request.user.groups.filter(name='Students').exists():
        messages.error(request, 'شما به این صفحه دسترسی ندارید.')
        return redirect('dashboard')

    this_way = get_object_or_404(Way, id=id)

    try:
        way_activities = json.loads(this_way.activities)
    except json.JSONDecodeError:
        way_activities = []
        messages.warning(request, 'فعالیت‌های این مسیر به درستی فرمت نشده‌اند.')

    return render(request, 'LMS/way_detail.html', {
        'way': this_way,
        'activities': way_activities
    })


@login_required
def exam_view(request, id):
    """
    Handle exam access with comprehensive permission checks:
    - Student must be in at least one classroom associated with the exam
    - Student must not have already taken the exam
    """
    this_exam = get_object_or_404(Exam, id=id)

    # Check if user has already taken this exam
    if UserScore.objects.filter(user=request.user, exam=this_exam).exists():
        return redirect('user_score', this_exam.id)

    # Check if user is in any of the exam's classrooms
    user_classrooms = set(request.user.student_class.all())
    exam_classrooms = set(this_exam.classrooms.all())

    if not user_classrooms & exam_classrooms:  # No common classrooms
        messages.error(request, 'شما به این آزمون دسترسی ندارید.')
        return redirect('dashboard')

    return render(request, 'LMS/exam_view.html', {'exam': this_exam})


class QuestionView(LoginRequiredMixin, View):
    def setup(self, request, *args, **kwargs):
        # Retrieve exam or return 404 if not found
        self.this_exam = get_object_or_404(Exam, id=kwargs['id'])
        # Cache parts and full questions list to avoid duplicate queries
        self.exam_parts = list(self.this_exam.parts.all())
        self.questions_list = [
            question for part in self.exam_parts
            for question in part.questions.all()
        ]
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        # Use ORM filtering to check if the user belongs to any classroom associated with this exam
        if self.this_exam.classrooms.filter(students=request.user).exists():
            # Prevent re-taking the exam if a score already exists
            if UserScore.objects.filter(exam=self.this_exam, user=request.user).exists():
                messages.error(request, 'شما قبلا در این آزمون شرکت کرده اید')
                return redirect('user_score', kwargs['id'])
            return super().dispatch(request, *args, **kwargs)

        messages.error(request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def get_question_and_part(self, q):
        """
        Given a 1-indexed question number q, returns a tuple of (question, part_number)
        and None for both values if q is out of range.
        """
        index = q - 1  # Convert to 0-indexed
        if index < 0 or index >= len(self.questions_list):
            return None, None

        question = self.questions_list[index]
        try:
            part_index = self.exam_parts.index(question.part)
        except ValueError:
            part_index = -1
        # Part number is 1-indexed for the template
        return question, part_index + 1

    def get(self, request, id, q):
        try:
            q = int(q)
        except ValueError:
            messages.error(request, 'شماره سوال نامعتبر است')
            return redirect('dashboard')

        question, part_num = self.get_question_and_part(q)
        if question is None:
            # When the question number exceeds available questions, redirect to the result page
            return redirect('user_score', self.this_exam.id)

        context = {
            'question': question,
            'part': question.part,
            'exam': self.this_exam,
            'q_num': q,
            'part_num': part_num,
        }
        return render(request, 'LMS/question_view.html', context)

    def post(self, request, id, q):
        try:
            q = int(q)
        except ValueError:
            messages.error(request, 'شماره سوال نامعتبر است')
            return redirect('dashboard')

        answer = request.POST.get('answer')
        # Validate answer input, convert if possible
        try:
            answer_val = int(answer) if answer is not None and answer.isdigit() else 0
        except ValueError:
            answer_val = 0

        total_questions = len(self.questions_list)
        if q < 1 or q > total_questions:
            messages.error(request, 'سوال نامعتبر است')
            return redirect('user_score', id)

        # Use get_or_create to handle both existing and new answer instances
        user_answer_obj, created = UserAnswer.objects.get_or_create(
            exam=self.this_exam,
            user=request.user,
            defaults={'answers': [0] * total_questions},
        )

        # Ensure the answers list is properly initialized
        current_answers = user_answer_obj.answers
        if len(current_answers) != total_questions:
            current_answers = [0] * total_questions

        current_answers[q - 1] = answer_val
        user_answer_obj.answers = current_answers
        user_answer_obj.save()

        messages.success(request, 'پاسخ سوال با موفقیت ذخیره شد')

        # Redirect to the next question if available, otherwise show the scores
        if q < total_questions:
            return redirect('question_view', id, q + 1)
        else:
            return redirect('user_score', id)


class UserScoreView(View):
    def setup(self, request, *args, **kwargs):
        # Retrieve the exam or return a 404 if not found
        self.this_exam = get_object_or_404(Exam, id=kwargs.get('id'))
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        # Check if the user is in at least one classroom associated with the exam
        if self.this_exam.classrooms.filter(students=request.user).exists():
            return super().dispatch(request, *args, **kwargs)

        messages.error(request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def get(self, request, id):
        # Retrieve the exam's correct answers (using the latest instance)
        exam_answer_obj = ExamAnswer.objects.filter(exam=self.this_exam).last()
        if not exam_answer_obj:
            messages.error(request, 'پاسخ‌های صحیح آزمون یافت نشد.')
            return redirect('dashboard')

        try:
            exam_answers = json.loads(exam_answer_obj.answers)
        except Exception:
            messages.error(request, 'خطا در پردازش پاسخ‌های صحیح آزمون.')
            return redirect('dashboard')

        # Retrieve the user's answers (using the latest instance)
        user_answer_obj = UserAnswer.objects.filter(
            exam=self.this_exam,
            user=request.user
        ).last()
        if not user_answer_obj:
            messages.error(request, 'پاسخ‌های شما یافت نشد.')
            return redirect('dashboard')

        try:
            user_answers = json.loads(user_answer_obj.answers)
        except Exception:
            messages.error(request, 'خطا در پردازش پاسخ‌های شما.')
            return redirect('dashboard')

        # Calculate the user's score final score:
        total_questions = len(exam_answers)
        score_points = 0

        for i in range(len(exam_answers)):
            correct_answer = int(exam_answers[i])
            user_answer = int(user_answers[i])

            # Exclude removed questions from the total
            if correct_answer == 0:
                total_questions -= 1
            # If the answer is correct and not blank, award 3 points
            elif user_answer != 0 and user_answer == correct_answer:
                score_points += 3
            # Wrong or blank answers contribute nothing

        try:
            score_percentage = round((score_points / (3 * total_questions)) * 100, 2)
        except ZeroDivisionError:
            score_percentage = 100  # if all questions are removed, default to 100%

        # Update or create the user score record in one streamlined query
        user_score, _ = UserScore.objects.update_or_create(
            exam=self.this_exam,
            user=request.user,
            defaults={'score': score_percentage}
        )

        context = {
            'score': user_score,
            'exam_answers': exam_answers,
            'user_answers': user_answers,
        }
        return render(request, 'LMS/exam_score.html', context)


class TeacherDashboardView(View):
    def dispatch(self, request, *args, **kwargs):
        # Only allow access to users in the "Teachers" group
        if request.user.groups.filter(name='Teachers').exists():
            return super().dispatch(request, *args, **kwargs)
        messages.error(request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def get(self, request):
        return render(request, 'LMS/teacher_dashboard.html')


class TeacherClassView(View):
    def setup(self, request, *args, **kwargs):
        # Retrieve the classroom or return a 404 if not found
        self.this_class = get_object_or_404(Classroom, id=kwargs.get('id'))
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        # Allow only the teacher in charge to access this page
        if self.this_class.teacher == request.user:
            return super().dispatch(request, *args, **kwargs)
        messages.error(request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def get(self, request, id):
        context = {
            'class': self.this_class,
        }
        return render(request, 'LMS/teacher_class.html', context)


class ClassDeleteView(DeleteView):
    model = Classroom
    context_object_name = 'class'
    success_url = reverse_lazy('teacher_dashboard')
    template_name = 'LMS/class_confirm_delete.html'

    def setup(self, request, *args, **kwargs):
        # Use get_object_or_404 to safely retrieve the classroom
        self.this_class = get_object_or_404(Classroom, pk=kwargs.get('pk'))
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        # Only the teacher responsible for this classroom can delete it
        if self.this_class.teacher == request.user:
            return super().dispatch(request, *args, **kwargs)

        messages.error(request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def form_valid(self, form):
        messages.success(self.request, 'کلاس با موفقیت حذف شد')
        return super().form_valid(form)


class ClassCreateView(CreateView):
    model = Classroom
    fields = ['name']
    success_url = reverse_lazy('teacher_dashboard')
    template_name = 'LMS/class_create.html'

    def dispatch(self, request, *args, **kwargs):
        # Ensure that only users in the "Teachers" group can create a class.
        if request.user.groups.filter(name="Teachers").exists():
            return super().dispatch(request, *args, **kwargs)

        messages.error(request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def form_valid(self, form):
        # Set the teacher of the classroom to the current user
        form.instance.teacher = self.request.user
        messages.success(self.request, 'کلاس با موفقیت اضافه شد')
        return super().form_valid(form)


class ClassJoinView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """
    View to allow students to submit join requests for a classroom
    """
    model = ClassroomJoinRequest
    template_name = 'LMS/class_join.html'
    fields = []  # When there are no form fields, override form_valid to set values manually
    success_url = reverse_lazy('dashboard')
    success_message = 'درخواست شما برای عضویت در این کلاس، ثبت شد، منتظر نتیجه باشید.'

    def setup(self, request, *args, **kwargs):
        # Retrieve the targeted classroom; consider using get_object_or_404 for robustness
        self.this_class = get_object_or_404(Classroom, id=kwargs.get('id'))
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        # Ensure only users in the "Students" group can join a class.
        if request.user.groups.filter(name="Students").exists():
            # Check if the student is already a member of this class
            if self.this_class.students.filter(id=request.user.id).exists():
                messages.error(request, 'شما در این کلاس عضو هستید! نیازی به درخواست نیست.')
                return redirect('class_detail', id=kwargs.get('id'))
            # Check if a join request for this classroom has already been submitted
            elif ClassroomJoinRequest.objects.filter(student=request.user, classroom=self.this_class).exists():
                messages.error(request, 'شما قبلا برای عضویت در این کلاس درخواست ثبت کرده اید.')
                return redirect('class_detail', id=kwargs.get('id'))
            else:
                return super().dispatch(request, *args, **kwargs)
        messages.error(request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Passing classroom instead of using the reserved word "class"
        context['classroom'] = self.this_class
        return context

    def form_valid(self, form):
        # Automatically attach the current user as the student and set the classroom.
        form.instance.student = self.request.user
        form.instance.classroom = self.this_class
        return super().form_valid(form)


class ClassJoinListView(LoginRequiredMixin, SuccessMessageMixin, ListView):
    """
    View to display join requests for a given classroom to its teacher.
    """
    model = ClassroomJoinRequest
    template_name = 'LMS/class_join_requests.html'

    def setup(self, request, *args, **kwargs):
        # Retrieve the classroom using its primary key
        self.classroom = get_object_or_404(Classroom, pk=kwargs.get('pk'))
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        # Only the classroom teacher can view its join requests
        if self.classroom.teacher == request.user:
            return super().dispatch(request, *args, **kwargs)
        messages.error(request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add all join requests specific to this classroom to the context
        context['requests'] = ClassroomJoinRequest.objects.filter(classroom=self.classroom)
        context['classroom'] = self.classroom
        return context


class ClassJoinAcceptView(LoginRequiredMixin, SuccessMessageMixin, View):
    """
    View to allow a teacher to accept a student's join request.
    """
    success_message = 'دانش آموز، عضو شد.'

    def setup(self, request, *args, **kwargs):
        # Retrieve the join request using its primary key from URL parameter and associate the classroom.
        self.join_request = get_object_or_404(ClassroomJoinRequest, pk=kwargs.get('r_pk'))
        self.classroom = self.join_request.classroom
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        # Allow only the teacher of the classroom to accept join requests
        if self.classroom.teacher == request.user:
            return super().dispatch(request, *args, **kwargs)
        messages.error(request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def post(self, request, pk, r_pk):
        # Add the student to the classroom and remove the pending join request.
        self.classroom.students.add(self.join_request.student)
        self.classroom.save()
        self.join_request.delete()
        messages.success(request, self.success_message)
        return redirect('class_requests_list', pk=pk)


class ClassJoinRejectView(LoginRequiredMixin, SuccessMessageMixin, View):
    """
    View to reject a teacher to accept a student's join request.
    """
    success_message = 'درخواست دانش آموز، رد شد.'

    def setup(self, request, *args, **kwargs):
        # Retrieve the join request using its primary key from URL parameter and associate the classroom.
        self.join_request = get_object_or_404(ClassroomJoinRequest, pk=kwargs.get('r_pk'))
        self.classroom = self.join_request.classroom
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        # Allow only the teacher of the classroom to accept join requests
        if self.classroom.teacher == request.user:
            return super().dispatch(request, *args, **kwargs)
        messages.error(request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def post(self, request, pk, r_pk):
        # Add the student to the classroom and remove the pending join request.
        self.join_request.delete()
        messages.success(request, self.success_message)
        return redirect('class_requests_list', pk=pk)


class TeacherExamListView(LoginRequiredMixin, ListView):
    model = Exam
    template_name = 'LMS/teacher_exams.html'
    context_object_name = 'exams'

    def dispatch(self, request, *args, **kwargs):
        # Ensure the user is in the "Teacher" group.
        if request.user.groups.filter(name="Teachers").exists():
            return super().dispatch(request, *args, **kwargs)

        messages.error(request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def get_queryset(self):
        # Return only exams authored by the current user.
        return Exam.objects.filter(author=self.request.user)


class TeacherExamDetailView(LoginRequiredMixin, DetailView):
    model = Exam
    context_object_name = 'exam'
    template_name = 'LMS/teacher_exam.html'

    def setup(self, request, *args, **kwargs):
        # Retrieve the exam; using get_object_or_404 for safe lookup.
        self.this_exam = get_object_or_404(Exam, pk=kwargs.get('pk'))
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        # Allow access only if the current user is the author of the exam.
        if self.this_exam.author == request.user:
            return super().dispatch(request, *args, **kwargs)

        messages.error(request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            exam_answer = ExamAnswer.objects.get(exam=self.object)
            answers = json.loads(exam_answer.answers)
        except ExamAnswer.DoesNotExist:
            # Create an empty ExamAnswer if none exists.
            exam_answer = ExamAnswer.objects.create(
                exam=self.object,
                answers=json.dumps([])
            )
            answers = []
        context['answers'] = answers
        return context


class ExamDeleteView(LoginRequiredMixin, DeleteView):
    """
    ExamDeleteView: Allows a teacher to delete an exam.
    Only the exam's author is authorized to perform this action.
    """
    model = Exam
    context_object_name = 'exam'
    success_url = reverse_lazy('teacher_exams')
    template_name = 'LMS/exam_confirm_delete.html'

    def setup(self, request, *args, **kwargs):
        # Retrieve the exam safely using get_object_or_404
        self.this_exam = get_object_or_404(Exam, pk=kwargs.get('pk'))
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        # Allow only the exam's author to delete the exam.
        if not self.this_exam.author == request.user:
            messages.error(request, 'شما به این صفحه دسترسی ندارید')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Show a success message after deletion.
        messages.success(self.request, 'آزمون با موفقیت حذف شد')
        return super().form_valid(form)


class ExamCreateView(LoginRequiredMixin, CreateView):
    """
    ExamCreateView: Allows a teacher to create a new exam.
    The current user is automatically assigned as the exam's author.
    """
    model = Exam
    fields = ['title', 'des', 'classrooms']
    success_url = reverse_lazy('teacher_exams')
    template_name = 'LMS/exam_create.html'

    def dispatch(self, request, *args, **kwargs):
        # Check if the current user belongs to the "Teacher" group.
        # Note that the .exists() method should be called.
        if not request.user.groups.filter(name="Teachers").exists():
            messages.error(request, 'شما به این صفحه دسترسی ندارید')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Automatically assign the current user as the exam's author.
        form.instance.author = self.request.user
        messages.success(self.request, 'آزمون با موفقیت ایجاد شد')
        return super().form_valid(form)


class ExamScoresListView(LoginRequiredMixin, View):
    """
    ExamScoresListView: Displays the scores for an exam.
    Only the exam's author can view the scores.
    The view computes a color for each score based on thresholds.
    """
    template_name = 'LMS/teacher_exam_scores.html'

    def setup(self, request, *args, **kwargs):
        # Retrieve the exam; if not found, return a 404 error.
        self.exam = get_object_or_404(Exam, pk=kwargs.get('pk'))
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        # Ensure that only the exam's author can access this view.
        if self.exam.author != request.user:
            messages.error(request, 'شما به این صفحه دسترسی ندارید')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_color(self, score):
        """
        Assign a color based on the score:
         - Green for scores >= 80
         - Yellow for scores >= 60
         - Orange for scores >= 40
         - Red otherwise
        """
        if score >= 80:
            return "green"
        elif score >= 60:
            return "yellow"
        elif score >= 40:
            return "orange"
        else:
            return "red"

    def get(self, request, pk):
        # Retrieve all user score objects for the exam.
        user_scores = UserScore.objects.filter(exam=self.exam)

        # Prepare context data with user details, their scores,
        # corresponding colors based on the get_color function,
        # and the top 10 scores ordered descendingly.
        context = {
            'names': [score.user.username for score in user_scores],
            'pks': [score.user.pk for score in user_scores],
            'scores': [score.score for score in user_scores],
            'colors': [self.get_color(score.score) for score in user_scores],
            'exam': self.exam,
            'top10': user_scores.order_by('-score')[:10],
        }
        return render(request, self.template_name, context)


class PartDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Part
    context_object_name = 'part'
    template_name = 'LMS/part_delete_confirm.html'
    success_message = 'بخش با موفقیت حذف شد'

    def get_object(self, queryset=None):
        return get_object_or_404(Part, pk=self.kwargs['pk'])

    def dispatch(self, request, *args, **kwargs):
        part = self.get_object()
        if part.exam.author == request.user:
            return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def get_success_url(self):
        return reverse('teacher_exam', args=[self.get_object().exam.pk])


class PartCreateView(DefaultCreateView):
    model = Part
    fields = ['title', 'des']
    success_message = 'بخش با موفقیت ایجاد شد'

    def get_queryset(self):
        return Exam.objects.select_related('author').only('author__id')

    def is_user_authorized(self) -> bool:
        return self.obj.author == self.request.user

    def form_valid(self, form):
        form.instance.exam = self.obj
        return super().form_valid(form)

    def get_success_url_args(self) -> list:
        return [self.obj.pk]

    def get_success_url_fragment(self) -> str:
        return f'#part{self.object.pk}'


class PartUpdateView(DefaultUpdateView):
    model = Part
    fields = ['title', 'des']
    success_message = 'بخش با موفقیت تغییر کرد'  # message to show after changing the part
    error_message = 'بخش تغییری نکرده است'       # message if there is no changes

    def get_queryset(self):
        return Part.objects.select_related('exam__author').only('title', 'des', 'exam__author__id')

    def is_user_authorized(self):
        return self.object.exam.author == self.request.user

    def get_success_url_args(self) -> list:
        return [self.object.exam.pk]

    def get_success_url_fragment(self) -> str:
        return f'#part{self.object.pk}'


class QuestionDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Question
    context_object_name = 'question'
    template_name = 'LMS/question_delete_confirm.html'
    success_message = 'سوال با موفقیت حذف شد'

    def get_object(self, queryset=None):
        return get_object_or_404(Question, pk=self.kwargs['pk'])

    def dispatch(self, request, *args, **kwargs):
        question = self.get_object()
        if question.part.exam.author == request.user:
            return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def get_success_url(self):
        return reverse('teacher_exam', args=[self.get_object().part.exam.pk])


class QuestionCreateView(DefaultCreateView):
    model = Question
    success_message = 'سوال با موفقیت ایچاد شد'  # message to show after creating the question

    def get_queryset(self):
        return Part.objects.select_related('exam__author').only('exam__author__id')

    def is_user_authorized(self) -> bool:
        return self.obj.exam.author == self.request.user

    def get_index(self):
        count = 0
        p = self.obj
        for part in self.obj.exam.parts.all():
            if part != p:
                count += part.questions.count()
            else:
                break
        count += p.questions.count()
        return count

    def form_valid(self, form):
        form.instance.part = self.obj
        i = self.get_index()
        answer = ExamAnswer.objects.get(exam=self.obj.exam)
        a = answer.answers
        a = json.loads(a)
        a.insert(i, 0)
        answer.answers = json.dumps(a)
        answer.save()
        return super().form_valid(form)

    def get_success_url_args(self) -> list:
        return [self.obj.exam.pk]

    def get_success_url_fragment(self) -> str:
        return f'#question{self.obj.pk}'


class QuestionUpdateView(DefaultUpdateView):
    model = Question
    success_message = 'سوال با موفقیت تغییر کرد'  # message to show after changing the question
    error_message = 'بدنه سوال تغییر نکرده است'   # message if the body is not changed

    def get_queryset(self):
        return Question.objects.select_related('part__exam__author').only('body', 'part__exam__author__id')

    def is_user_authorized(self):
        return self.object.part.exam.author == self.request.user

    def get_success_url_args(self) -> list:
        return [self.object.part.exam.pk]

    def get_success_url_fragment(self) -> str:
        return f'#question{self.object.pk}'


class ChoiceDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Choice
    context_object_name = 'choice'
    template_name = 'LMS/choice_confirm_delete.html'
    success_message = 'گزینه با موفقیت حذف شد'

    def get_object(self, queryset=None):
        return get_object_or_404(Choice, pk=self.kwargs['pk'])

    def dispatch(self, request, *args, **kwargs):
        choice = self.get_object()
        if choice.question.part.exam.author == request.user:
            return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def get_success_url(self):
        return reverse('teacher_exam', args=[self.get_object().question.part.exam.pk])


class ChoiceCreateView(DefaultCreateView):
    model = Choice
    success_message = 'گزینه با موفقیت ایجاد شد'  # message to show after creating the choice

    def get_queryset(self):
        return Question.objects.select_related('part__exam__author').only('part__exam__author__id')

    def is_user_authorized(self) -> bool:
        return self.obj.part.exam.author == self.request.user

    def form_valid(self, form):
        form.instance.question = self.obj
        return super().form_valid(form)

    def get_success_url_args(self) -> list:
        return [self.obj.part.exam.pk]

    def get_success_url_fragment(self) -> str:
        return f'#question{self.obj.pk}'


class ChoiceUpdateView(DefaultUpdateView):
    model = Choice
    success_message = 'گزینه با موفقیت تغییر کرد'  # message to show after changing the choice
    error_message = 'بدنه گزینه تغییر نکرده است'   # message if the body is not changed

    def get_queryset(self):
        return Choice.objects.select_related('question__part__exam__author'
                                             ).only('body','question__part__exam__author__id')

    def is_user_authorized(self) -> bool:
        return self.object.question.part.exam.author == self.request.user

    def get_success_url_args(self) -> list:
        return [self.object.question.part.exam.pk]

    def get_success_url_fragment(self) -> str:
        return f'#question{self.object.question.pk}'


class QuestionAnswerChange(LoginRequiredMixin, View):
    def setup(self, request, *args, **kwargs):
        self.this_exam = get_object_or_404(Exam, pk=kwargs['pk'])
        self.this_answers = get_object_or_404(ExamAnswer, exam=self.this_exam)
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        for c in self.this_exam.classrooms.all():
            if request.user == c.teacher:
                return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def get_index(self, p, q):
        count = 0
        loop = 0
        for part in self.this_exam.parts.all():
            loop += 1
            if loop < p:
                count += part.questions.count()
        count += q
        return count

    def post(self, request, pk, p, q):
        new_answer = int(request.POST.get('answer'))
        answers = self.this_answers.answers
        answers = json.loads(answers)
        answers[self.get_index(p, q)-1] = new_answer
        self.this_answers.answers = json.dumps(answers)
        self.this_answers.save()
        # TODO: fragment
        return redirect('teacher_exam', pk=pk)


def exam_excel_output(request, pk):
    this_exam = get_object_or_404(Exam, pk=pk)
    correct_answers = get_object_or_404(ExamAnswer, exam=this_exam).answers
    correct_answers = json.loads(correct_answers)

    # checking permission
    classrooms = this_exam.classrooms.all()
    permission = any(request.user == classroom.teacher for classroom in classrooms)
    if not permission:
        messages.error(request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    # this exam scores
    all_scores = UserScore.objects.filter(exam=this_exam)
    usernames = []
    first_names = []
    last_names = []
    scores = []
    part_scores = []

    for_loop_counter = 0
    for score in all_scores:
        for_loop_counter += 1
        user = score.user
        usernames.append(user.username)
        first_names.append(user.first_name)
        last_names.append(user.last_name)
        scores.append(score.score)
        # user part report
        n = 0
        user_answers = get_object_or_404(UserAnswer, exam=this_exam, user=user).answers
        user_answers = json.loads(user_answers)
        this_user_part = []
        for part in this_exam.parts.all():
            c = 0
            t = 0
            for _ in part.questions.all():
                if correct_answers[n] != 0:
                    c += 1
                    if correct_answers[n] == user_answers[n]:
                        t += 1
                n += 1
            s = round(t / c * 100, 2)
            this_user_part.append(s)
        part_scores.append(this_user_part)

    # creating data dict
    data = {
        'ردیف': np.linspace(1, len(all_scores), num=len(all_scores)),
        'نام کاربری': usernames,
        'نام': first_names,
        'نام خانوادگی': last_names,
        'امتیاز کل': scores,
    }
    # adding part bt part report to data
    for_loop_counter = 0
    for part in this_exam.parts.all():
        s = []
        for p in part_scores:
            s.append(p[for_loop_counter])
        data[part.title] = s
        for_loop_counter += 1


    # converting to pandas dataframe
    df = pd.DataFrame(data)

    # defining the Excel file response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=out.xlsx'

    # converting to excel with pandas
    df.to_excel(response, index=False, engine='openpyxl')

    return response


class ClassWayListView(LoginRequiredMixin, TemplateView):
    template_name = 'LMS/class_ways.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.groups.filter(name="Teacher").exists:
            return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = Classroom.objects.prefetch_related('class_ways')
        this_classroom = get_object_or_404(queryset, pk=kwargs['pk'])
        context['classroom'] = this_classroom
        context['ways'] = this_classroom.class_ways.all()
        return context


class WayDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Way
    context_object_name = 'way'
    template_name = 'LMS/way_confirm_delete.html'
    success_message = 'مسیر با موفقیت حذف شد'

    def setup(self, request, *args, **kwargs):
        """Initialize the Way object and check permissions"""
        self.way = get_object_or_404(Way, pk=kwargs['pk'])
        self.classrooms = self.way.classrooms.select_related('teacher').all()
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        """Check if user has permission to delete activities"""
        permission = any(request.user == classroom.teacher for classroom in self.classrooms)
        if not permission:
            messages.error(request, 'شما به این صفحه دسترسی ندارید')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('dashboard')  # TODO: reversing to Teacher_Ways


class WayCreateView(DefaultCreateView):
    # TODO: costume View
    model = Way
    success_message = 'مسیر با موفقیت ایجاد شد'  # message to show after creating the way
    success_redirect_url = 'teacher_way'
    template_name = 'LMS/way_create.html'
    fields = ['title', 'classrooms']

    def get_queryset(self):
        return Classroom.objects.all()

    def is_user_authorized(self) -> bool:
        return self.request.user.groups.filter(name="Teachers").exists()

    def form_valid(self, form):
        form.instance.activities = json.dumps([])
        return super().form_valid(form)

    def get_success_url_args(self) -> list:
        return [self.object.pk]

    def get_success_url_fragment(self) -> str:
        return ''


class WayDetailView(LoginRequiredMixin, DetailView):
    model = Way
    context_object_name = 'way'
    template_name = 'LMS/teacher_way.html'

    def dispatch(self, request, *args, **kwargs):
        self.way = get_object_or_404(Way, pk=kwargs['pk'])
        classrooms = self.way.classrooms.all()
        teachers = []
        for classroom in classrooms:
            teachers.append(classroom.teacher)
        if request.user in teachers:
            return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        activities = self.way.activities
        context['activities'] = json.loads(activities)
        return context


class WayAddExamView(LoginRequiredMixin, View):
    def setup(self, request, *args, **kwargs):
        self.way = get_object_or_404(Way, pk=kwargs['pk'])
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        classrooms = self.way.classrooms.all()
        teachers = []
        for classroom in classrooms:
            teachers.append(classroom.teacher)
        if request.user in teachers:
            return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def get(self, request, pk):
        classrooms = self.way.classrooms.all()
        exams = []
        for classroom in classrooms:
            exams.append(classroom.class_exams.all())
        return render(request, 'LMS/way_add_exam.html', context={
            'way': self.way,
            'exams': exams,
        })

    def post(self, request, pk):
        exam = int(request.POST.get('exam'))
        text = request.POST.get('text')
        new = [1, exam, f"{text}"]
        activities = self.way.activities
        activities = json.loads(activities)
        activities.append(new)
        self.way.activities = json.dumps(activities)
        self.way.save()
        return redirect('teacher_way', pk=pk)


class WayAddPresentView(LoginRequiredMixin, View):
    def setup(self, request, *args, **kwargs):
        self.way = get_object_or_404(Way, pk=kwargs['pk'])
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        classrooms = self.way.classrooms.all()
        teachers = []
        for classroom in classrooms:
            teachers.append(classroom.teacher)
        if request.user in teachers:
            return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def get(self, request, pk):
        classrooms = self.way.classrooms.all()
        presents = []
        for classroom in classrooms:
            presents.append(classroom.class_presents.all())
        return render(request, 'LMS/way_add_present.html', context={
            'way': self.way,
            'presents': presents,
        })

    def post(self, request, pk):
        present = int(request.POST.get('exam'))
        text = request.POST.get('text')
        new = [2, present, f"{text}"]
        activities = self.way.activities
        activities = json.loads(activities)
        activities.append(new)
        self.way.activities = json.dumps(activities)
        self.way.save()
        return redirect('teacher_way', pk=pk)


class WayMoveActivity(LoginRequiredMixin, View):
    def setup(self, request, *args, **kwargs):
        self.way = get_object_or_404(Way, pk=kwargs['pk'])
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        classrooms = self.way.classrooms.all()
        teachers = []
        for classroom in classrooms:
            teachers.append(classroom.teacher)
        if request.user in teachers:
            return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def get(self, request, pk, move):
        # getting the queries
        index = int(request.GET.get('index'))
        index -= 1  # decreasing one from index because it should start from 0 not 1
        # getting activities list from Way
        activities = self.way.activities
        activities = json.loads(activities)
        # checking if it should move up or down (backward or forward)
        if move == 'up':
            # it should go backward
            try:
                activities[index], activities[index - 1] = activities[index - 1], activities[index]
            except:
                return redirect('teacher_way', pk=pk)
        elif move == 'down':
            # it should go forward
            try:
                activities[index], activities[index + 1] = activities[index + 1], activities[index]
            except:
                return redirect('teacher_way', pk=pk)
        # saving the changes to Way
        self.way.activities = json.dumps(activities)
        self.way.save()
        # redirecting to Way page
        return redirect('teacher_way', pk=pk)


class WayDeleteActivity(LoginRequiredMixin, View):
    """View for deleting an activity from a Way"""

    def setup(self, request, *args, **kwargs):
        """Initialize the Way object and check permissions"""
        self.way = get_object_or_404(Way, pk=kwargs['pk'])
        self.classrooms = self.way.classrooms.select_related('teacher').all()
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        """Check if user has permission to delete activities"""
        permission = any(request.user == classroom.teacher for classroom in self.classrooms)
        if not permission:
            messages.error(request, 'شما به این صفحه دسترسی ندارید')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        """Render confirmation page for activity deletion"""
        return render(request, 'LMS/way_activity_confirm_delete.html')

    def post(self, request, pk):
        """Handle activity deletion"""
        try:
            # getting the queries
            index = int(request.GET.get('index')) - 1  # decreasing one from index because it should start from 0 not 1

            # getting activities list from Way
            activities = self.way.activities
            activities = json.loads(activities)

            if not 0 <= index < len(activities):
                messages.error(request, 'فعالیت پیدا نشد')
                return redirect('teacher_way', pk=pk)

            # deleting the activity
            del activities[index]

            # saving the changes to Way
            self.way.activities = json.dumps(activities)
            self.way.save()

            messages.success(request, 'فعالیت با موفقیت حذف شد')

        except:  # if there is any errors
            messages.error(request, 'حذف فعالیت با خطا مواجه شد')

        # redirecting to Way page
        return redirect('teacher_way', pk=pk)


class TeacherPresentationsListView(TemplateView):
    template_name = 'LMS/teacher-presentations/presents_list.html'


class PresentationCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Presentation
    success_message = 'ارائه با موفقیت ایجاد شد'  # message to show after creating the presentation
    success_redirect_url = 'teacher_presents'
    template_name = 'LMS/teacher-presentations/present_create.html'
    form_class = PresentationForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.groups.filter(name="Teacher").exists:
            return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class PresentationDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Presentation
    context_object_name = 'presentation'
    template_name = 'LMS/teacher-presentations/present_confirm_delete.html'
    success_message = 'ارائه با موفقیت حذف شد'

    def setup(self, request, *args, **kwargs):
        """Initialize the Way object and check permissions"""
        self.presentation = get_object_or_404(Presentation, pk=kwargs['pk'])
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        """Check if user has permission to delete activities"""
        permission = request.user == self.presentation.author
        if not permission:
            messages.error(request, 'شما به این صفحه دسترسی ندارید')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('teacher_presents')


class PresentationDetailView(TemplateView):
    template_name = 'LMS/teacher-presentations/present_detail.html'

    def setup(self, request, *args, **kwargs):
        self.presentation = get_object_or_404(Presentation, pk=kwargs['pk'])
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        permission = request.user == self.presentation.author
        if not permission:
            messages.error(request, 'شما به این صفحه دسترسی ندارید')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        presentation = get_object_or_404(Presentation, pk=kwargs['pk'])
        context = super().get_context_data()
        context['presentation'] = presentation
        return context


class SlideDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Slide
    context_object_name = 'slide'
    template_name = 'LMS/teacher-presentations/slide_confirm_delete.html'
    success_message = 'اسلاید با موفقیت حذف شد'

    def setup(self, request, *args, **kwargs):
        """Initialize the Slide object and check permissions"""
        self.slide = get_object_or_404(Slide, pk=kwargs['pk'])
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        """Check if user has permission to delete slide"""
        permission = request.user == self.slide.presentation.author
        if not permission:
            messages.error(request, 'شما به این صفحه دسترسی ندارید')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('present_detail', args=[self.slide.presentation.pk])


class SlideCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Presentation
    success_message = 'اسلاید با موفقیت ایجاد شد'  # message to show after creating the presentation
    template_name = 'LMS/teacher-presentations/slide_create.html'
    form_class = SlideForm

    def setup(self, request, *args, **kwargs):
        """Initialize the Presentation object and check permissions"""
        self.presentation = get_object_or_404(Presentation, pk=kwargs['pk'])
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        """Check if user has permission to create slide"""
        permission = request.user == self.presentation.author
        if not permission:
            messages.error(request, 'شما به این صفحه دسترسی ندارید')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.presentation = self.presentation
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('present_detail', args=[self.presentation.pk])


class SlideUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Slide
    success_message = 'اسلاید با موفقیت تغییر شد'  # message to show after creating the presentation
    template_name = 'LMS/teacher-presentations/slide_update.html'
    form_class = SlideForm
    context_object_name = 'slide'

    def setup(self, request, *args, **kwargs):
        """Initialize the Presentation object and check permissions"""
        self.slide = get_object_or_404(Slide, pk=kwargs['pk'])
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        """Check if user has permission to create slide"""
        permission = request.user == self.slide.presentation.author
        if not permission:
            messages.error(request, 'شما به این صفحه دسترسی ندارید')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.presentation = self.slide.presentation
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('present_detail', args=[self.slide.presentation.pk])


class StudentPresentationView(TemplateView):
    template_name = 'LMS/student-presentations/presentation_detail.html'

    def setup(self, request, *args, **kwargs):
        """Initialize the Presentation object and check permissions"""
        self.presentation = get_object_or_404(Presentation, pk=kwargs['pk'])
        self.classrooms = self.presentation.classroom.all()
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        """Check if user has permission to create slide"""
        permission = any(request.user in classroom.students.all() for classroom in self.classrooms)
        if not permission:
            messages.error(request, 'شما به این صفحه دسترسی ندارید')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        presentation = get_object_or_404(Presentation, pk=kwargs['pk'])
        context = super().get_context_data()
        context['presentation'] = presentation
        return context

