from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import render, redirect, get_object_or_404
from .models import Classroom, Way, Exam, UserAnswer, UserScore, ExamAnswer, Part, Question, Choice
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.views import View
from django.views.generic.edit import DeleteView, CreateView
from django.views.generic import ListView, DetailView, UpdateView
from django.urls import reverse
import json

from .default_views import DefaultUpdateView

@login_required
def dashboard(request):
    if request.user.groups.filter(name='Students').exists():
        return render(request, 'LMS/dashboard.html')
    else:
        return redirect('teacher_dashboard')


@login_required
def class_detail(request, id):
    if request.user.groups.filter(name='Students').exists():
        this_class = Classroom.objects.get(id=id)
        return render(request, 'LMS/class_detail.html', {'class': this_class})


@login_required
def way_detail(request, id):
    if request.user.groups.filter(name='Students').exists():
        this_way = Way.objects.get(id=id)
        a = this_way.activities
        way_activities = json.loads(a)
        return render(request, 'LMS/way_detail.html', {'way': this_way, 'activities': way_activities})


@login_required
def exam_view(request, id):
    this_exam = Exam.objects.get(id=id)
    for c in this_exam.classrooms.all():
        if request.user in c.students.all():
            return render(request, 'LMS/exam_view.html', {'exam': this_exam})


class QuestionView(LoginRequiredMixin, View):
    def setup(self, request, *args, **kwargs):
        self.this_exam = Exam.objects.get(id=kwargs['id'])
        return super(QuestionView, self).setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        for c in self.this_exam.classrooms.all():
            if request.user in c.students.all():
                if UserScore.objects.filter(exam=self.this_exam, user=request.user).exists():
                    messages.error(self.request, 'شما قبلا در این آزمون شرکت کرده اید')
                    return redirect('user_score', kwargs['id'])
                else:
                    return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def get(self, request, id, q):
        questions_list = []
        for part in self.this_exam.parts.all():
            questions_list = questions_list + list(part.questions.all())
        try:
            this_question = questions_list[q-1]
        except IndexError:
            return redirect('user_score', self.this_exam.id)
        this_part = this_question.part
        part_num = list(self.this_exam.parts.all()).index(this_part)+1
        context = {
            'question': this_question,
            'part': this_part,
            'exam': self.this_exam,
            'q_num': q,
            'part_num': part_num,
        }
        messages.success(request, 'پاسخ سوال با موفقیت ذخیره شد')
        return render(request, 'LMS/question_view.html', context)

    def post(self, request, id, q):
        answer = request.POST.get('answer')
        if UserAnswer.objects.filter(exam=self.this_exam, user=request.user).exists():
            this_user_answer = UserAnswer.objects.get(exam=self.this_exam, user=request.user)
            a = json.loads(this_user_answer.answers)
            a[q-1] = int(answer) if answer is not None else 0
            this_user_answer.answers = a
            this_user_answer.save()
            return redirect('question_view', id, q+1)
        else:
            questions_list = []
            for part in self.this_exam.parts.all():
                questions_list = questions_list + list(part.questions.all())
            a = []
            for i in range(len(questions_list)):
                a.append(0)
            a[q-1] = int(answer) if answer is not None else 0
            this_user_answer = UserAnswer.objects.create(
                exam=self.this_exam,
                user=request.user,
                answers=a,
            )
            return redirect('question_view', id, q+1)


# class ExamDoneView(LoginRequiredMixin, View):
#     def setup(self, request, *args, **kwargs):
#         self.this_exam = Exam.objects.get(id=kwargs['id'])
#         return super(ExamDoneView, self).setup(request, *args, **kwargs)
#
#     def dispatch(self, request, *args, **kwargs):
#         for c in self.this_exam.classrooms.all():
#             if request.user in c.students.all():
#                 if UserScore.objects.filter(exam=self.this_exam, user=request.user).exists():
#                     messages.error(self.request, 'شما قبلا در این آزمون شرکت کرده اید')
#                     return redirect('user_score', kwargs['id'])
#                 else:
#                     return super().dispatch(request, *args, **kwargs)
#
#         messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
#         return redirect('dashboard')
#
#     def get(self, request, id):
#         return render(request, 'LMS/exam_done.html', {'id': id, 'exam': self.this_exam})


class UserScoreView(View):
    def setup(self, request, *args, **kwargs):
        self.this_exam = Exam.objects.get(id=kwargs['id'])
        return super(UserScoreView, self).setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        for c in self.this_exam.classrooms.all():
            if request.user in c.students.all():
                return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def get(self, request, id):
        # finding the exam's TRUE answers
        exam_answers = ExamAnswer.objects.filter(exam=self.this_exam).last()
        exam_answers_a = exam_answers.answers  # answers field of exam_answers
        exam_answers = json.loads(exam_answers_a)  # converting it to list

        # finding the user's last answers to the exam
        user_answers = UserAnswer.objects.filter(exam=self.this_exam, user=request.user).last()
        user_answers_a = user_answers.answers  # answers field of user_answers
        user_answers = json.loads(user_answers_a)  # converting it to list

        # calculating the score:
        questions_number = len(exam_answers)
        score_int = 0  # default score is 0

        for i in range(len(exam_answers)):
            # if the question is removed from the exam:
            if int(exam_answers[i]) == 0:
                questions_number -= 1
            # if answer is true and is not 0 (not answered):
            elif int(exam_answers[i]) == int(user_answers[i]) and int(user_answers[i]) != 0:
                score_int += 3
            # if the answer is blank:
            elif int(user_answers[i]) == 0:
                pass
            # if the answer is wrong:
            else:
                pass

        score_p = score_int / (3 * questions_number) * 100

        if UserScore.objects.filter(exam=self.this_exam, user=request.user).exists():
            user_score = UserScore.objects.filter(exam=self.this_exam, user=request.user).last()
            # updating the score
            user_score.score = score_p
            user_score.save()

        else:
            # creating Score
            user_score = UserScore.objects.create(exam=self.this_exam, user=request.user, score=score_p)

        context = {
            'score': user_score,
            'exam_answers': exam_answers,
            'user_answers': user_answers,
        }
        return render(request, 'LMS/exam_score.html', context)


class TeacherDashboardView(View):
    def dispatch(self, request, *args, **kwargs):
        if request.user.groups.filter(name='Teachers').exists():
            return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def get(self, request):
        return render(request, 'LMS/teacher_dashboard.html')


class TeacherClassView(View):
    def setup(self, request, *args, **kwargs):
        self.this_class = Classroom.objects.get(id=kwargs['id'])
        super().setup(TeacherClassView, request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        if self.this_class.teacher == request.user:
            return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def get(self, request, id):
        exams = self.this_class.class_exams.all()
        index = min(len(exams), 5)
        exams = exams[len(exams)-index:]
        return render(request, 'LMS/teacher_class.html', {'class': self.this_class})


class ClassDeleteView(DeleteView):
    def setup(self, request, *args, **kwargs):
        self.this_class = Classroom.objects.get(pk=kwargs['pk'])
        super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        if self.this_class.teacher == request.user:
            return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    model = Classroom
    context_object_name = 'class'
    success_url = reverse_lazy('teacher_dashboard')
    template_name = 'LMS/class_confirm_delete.html'

    def form_valid(self, form):
        messages.success(self.request, 'کلاس با موفقیت حذف شد')
        return super(ClassDeleteView, self).form_valid(form)


class ClassCreateView(CreateView):
    def dispatch(self, request, *args, **kwargs):
        if request.user.groups.filter(name="Teacher").exists:
            return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    model = Classroom
    fields = ['name']
    success_url = reverse_lazy('teacher_dashboard')
    template_name = 'LMS/class_create.html'

    def form_valid(self, form):
        form.instance.teacher = self.request.user
        messages.success(self.request, 'کلاس با موفقیت اضافه شد')
        return super(ClassCreateView, self).form_valid(form)


class ClassJoinView(LoginRequiredMixin, View):
    def setup(self, request, *args, **kwargs):
        self.this_class = Classroom.objects.get(id=kwargs['id'])
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        if request.user.groups.filter(name="Students").exists():
            if not self.this_class.students.filter(id=request.user.id).exists():
                return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def get(self, request, id):
        return HttpResponse(f'join class {id}')


class TeacherExamListView(LoginRequiredMixin, ListView):
    def dispatch(self, request, *args, **kwargs):
        if request.user.groups.filter(name="Teacher").exists:
            return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    model = Exam
    template_name = 'LMS/teacher_exams.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['exams'] = Exam.objects.filter(author=self.request.user)
        return context


class TeacherExamDetailView(LoginRequiredMixin, DetailView):
    def setup(self, request, *args, **kwargs):
        self.this_exam = Exam.objects.get(pk=kwargs['pk'])
        super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        if self.this_exam.author == request.user:
            return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    model = Exam
    context_object_name = 'exam'
    template_name = 'LMS/teacher_exam.html'


class ExamDeleteView(LoginRequiredMixin, DeleteView):
    def setup(self, request, *args, **kwargs):
        self.this_exam = Exam.objects.get(pk=kwargs['pk'])
        super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        if self.this_exam.author == request.user:
            return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    model = Exam
    context_object_name = 'exam'
    success_url = reverse_lazy('teacher_exams')
    template_name = 'LMS/exam_confirm_delete.html'

    def form_valid(self, form):
        messages.success(self.request, 'آزمون با موفقیت حذف شد')
        return super(ExamDeleteView, self).form_valid(form)


class ExamCreateView(LoginRequiredMixin, CreateView):
    def dispatch(self, request, *args, **kwargs):
        if request.user.groups.filter(name="Teacher").exists:
            return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    model = Exam
    fields = ['title', 'des', 'classrooms']
    success_url = reverse_lazy('teacher_exams')
    template_name = 'LMS/exam_create.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        messages.success(self.request, 'آزمون با موفقیت ایجاد شد')
        return super(ExamCreateView, self).form_valid(form)


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


class PartCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Part
    fields = ['title', 'des']
    success_message = 'بخش با موفقیت اضافه شد'

    def get_object(self, queryset=None):
        return get_object_or_404(Exam, pk=self.kwargs['pk'])

    def dispatch(self, request, *args, **kwargs):
        self.exam = self.get_object()
        if self.exam.author == request.user:
            return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def form_valid(self, form):
        form.instance.exam = self.exam
        return super(PartCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('teacher_exam', args=[self.exam.pk])


class PartUpdateView(DefaultUpdateView):
    model = Part
    fields = ['title', 'des']
    success_message = 'بخش با موفقیت تغییر کرد'  # message to show after changing the choice
    error_message = 'بخش تغییری نکرده است'       # message if the body is not changed

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


class QuestionCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Question
    fields = ['body']
    success_message = 'سوال با موفقیت اضافه شد'

    def get_object(self, queryset=None):
        return get_object_or_404(Part, pk=self.kwargs['pk'])

    def dispatch(self, request, *args, **kwargs):
        self.part = self.get_object()
        if self.part.exam.author == request.user:
            return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def form_valid(self, form):
        form.instance.part = self.part
        return super(QuestionCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('teacher_exam', args=[self.part.exam.pk])


class QuestionUpdateView(DefaultUpdateView):
    model = Question
    fields = ['body']
    success_message = 'سوال با موفقیت تغییر کرد'  # message to show after changing the choice
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


class ChoiceCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Choice
    fields = ['body']
    success_message = 'گزینه با موفقیت اضافه شد'

    def get_object(self, queryset=None):
        return get_object_or_404(Question, pk=self.kwargs['pk'])

    def dispatch(self, request, *args, **kwargs):
        self.question = self.get_object()
        if self.question.part.exam.author == request.user:
            return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def form_valid(self, form):
        form.instance.question = self.question
        return super(ChoiceCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('teacher_exam', args=[self.question.part.exam.pk])


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
