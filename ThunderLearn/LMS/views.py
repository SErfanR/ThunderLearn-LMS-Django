from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import render, redirect, get_object_or_404
from .models import (Classroom, Way, Exam, UserAnswer, UserScore, ExamAnswer,
                     Part, Question, Choice, ClassroomJoinRequest, Presentation, Slide)
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.views import View
from django.views.generic.edit import DeleteView, CreateView
from django.views.generic import ListView, DetailView, TemplateView, UpdateView
from django.urls import reverse
import json
from .default_views import DefaultUpdateView, DefaultCreateView
from .forms import PresentationForm, SlideForm

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

        try:
            score_p = round(score_int / (3 * questions_number) * 100, 2)
        except ZeroDivisionError:
            score_p = 100

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


class ClassJoinView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = ClassroomJoinRequest
    template_name = 'LMS/class_join.html'
    fields = []
    success_url = reverse_lazy('dashboard')
    success_message = 'درخواست شما برای عضویت در این کلاس، ثبت شد، منتظر نتیجه باشید.'

    def setup(self, request, *args, **kwargs):
        self.this_class = Classroom.objects.get(id=kwargs['id'])
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        if request.user.groups.filter(name="Students").exists():

            if self.this_class.students.filter(id=request.user.id).exists():
                messages.error(self.request, 'شما در این کلاس عضو هستید! نیازی به درخواست نیست.')
                return redirect('class_detail', id=kwargs['id'])

            elif ClassroomJoinRequest.objects.filter(student=request.user).exists():
                messages.error(self.request, 'شما قبلا برای عضویت در این کلاس درخواست ثبت کرده اید.')
                return redirect('class_detail', id=kwargs['id'])

            else:
                return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['class'] = self.this_class
        return context

    def form_valid(self, form):
        form.instance.student = self.request.user
        form.instance.classroom = self.this_class
        return super().form_valid(form)


class ClassJoinListView(LoginRequiredMixin, SuccessMessageMixin, ListView):
    model = ClassroomJoinRequest
    template_name = 'LMS/class_join_requests.html'

    def setup(self, request, *args, **kwargs):
        self.classroom = get_object_or_404(Classroom, pk=kwargs['pk'])
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        if self.classroom.teacher == request.user:
            return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['requests'] = ClassroomJoinRequest.objects.filter(classroom=self.classroom)
        context['classroom'] = self.classroom
        return context


class ClassJoinAcceptView(LoginRequiredMixin, SuccessMessageMixin, View):
    success_message = 'دانش آموز، عضو شد.'

    def setup(self, request, *args, **kwargs):
        self.join_request = get_object_or_404(ClassroomJoinRequest, pk=kwargs['r_pk'])
        self.classroom = self.join_request.classroom
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        if self.classroom.teacher == request.user:
            return super().dispatch(request, *args, **kwargs)

        messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
        return redirect('dashboard')

    def post(self, request, pk, r_pk):
        self.classroom.students.add(self.join_request.student)
        self.classroom.save()
        self.join_request.delete()
        return redirect('class_requests_list', pk=pk)


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        try:
            answers = ExamAnswer.objects.get(exam=self.object).answers
            answers = json.loads(answers)
        except:
            answers = ExamAnswer.objects.create(exam=self.object)
            answers.answers = json.dumps([])
            answers.save()
            answers = []
        context['answers'] = answers
        return context

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


class ExamScoresListView(LoginRequiredMixin, View):
    template_name = 'LMS/teacher_exam_scores.html'

    def setup(self, request, *args, **kwargs):
        self.exam = get_object_or_404(Exam, pk=kwargs['pk'])
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        if not request.user == self.exam.author:
            messages.error(self.request, 'شما به این صفحه دسترسی ندارید')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_color(self, score):
        if score >= 80:
            return "green"
        elif score >= 60:
            return "yellow"
        elif score >= 40:
            return "orange"
        else:
            return "red"

    def get(self, requset, pk):
        user_scores = UserScore.objects.filter(exam=self.exam)
        context = {
            'names': [score.user.username for score in user_scores],
            'pks': [score.user.pk for score in user_scores],
            'scores': [score.score for score in user_scores],
            'colors': [self.get_color(score.score) for score in user_scores],
            'exam': self.exam,
            'top10': user_scores.order_by('-score')[:10],
        }
        return render(requset, self.template_name, context)


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

    # TODO: dispatch
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

    # TODO: dispatch
    def get_context_data(self, **kwargs):
        presentation = get_object_or_404(Presentation, pk=kwargs['pk'])
        context = super().get_context_data()
        context['presentation'] = presentation
        return context

