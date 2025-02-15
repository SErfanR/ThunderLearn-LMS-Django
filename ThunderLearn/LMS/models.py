from django.db import models
from django.contrib.auth.models import User
import json


class Classroom(models.Model):
    name = models.CharField(max_length=150, unique=True)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teacher_class')
    students = models.ManyToManyField(User, related_name='student_class', blank=True)
    assistants = models.ManyToManyField(User, related_name='assistant_class', blank=True)

    def add_student(self, user):  # adding a student (a user in student group) to classroom
        if user.groups.filter(name='Students').exists():
            self.students.add(user)  # TODO: return and else statement

    def remove_student(self, user):  # removing a student
        try:  # if the student is in self.student remove it else pass
            self.students.remove(user)
        finally:
            pass  # TODO: return and except statement

    def add_assistant(self, user):
        if user.groups.filter(name='Teachers').exists() or user.groups.filter(name='Assistants').exists():
            self.assistants.add(user)  # TODO: return and else statement

    def remove_assistant(self, user):
        try:
            self.assistants.remove(user)
        finally:
            pass  # TODO: return and except statement


class Way(models.Model):
    title = models.CharField(max_length=250)
    classrooms = models.ManyToManyField(Classroom, related_name='class_ways')
    activities = models.TextField()

    def add_activity(self, q):  # adding a activity to a Way with help of json # TODO: index of appending
        a = self.activities
        a = json.loads(a)
        a.append(q)
        self.activities = json.dumps(a)


# Exams models
class Exam(models.Model):
    title = models.CharField(max_length=50)
    des = models.TextField()
    author = models.ForeignKey(User, related_name='user_exams', on_delete=models.CASCADE)
    classrooms = models.ManyToManyField(Classroom, related_name='class_exams')
    # TODO: timed exam options and start and finish date_time


class Part(models.Model):
    title = models.CharField(max_length=50)
    des = models.TextField()
    exam = models.ForeignKey(Exam, related_name='parts', on_delete=models.CASCADE)


class Question(models.Model):
    body = models.TextField()  # TODO: RichTextField
    part = models.ForeignKey(Part, related_name='questions', on_delete=models.CASCADE)


class Choice(models.Model):
    body = models.TextField()
    question = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE)


class ExamAnswer(models.Model):
    exam = models.ForeignKey(Exam, related_name='exam_answer', on_delete=models.CASCADE)
    answers = models.TextField()

    def dump_answer(self, a):  # gets a dict and dumps it and puts it in answers as a str
        self.answers = json.dumps(a)  # TODO: return

    def load_answer(self):  # reads self.answers and returns it as a dict for calculations or ...
        return json.loads(self.answers)


class UserAnswer(models.Model):
    exam = models.ForeignKey(Exam, related_name='exam_user_answers', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='user_answers', on_delete=models.CASCADE)
    answers = models.TextField()

    def add_or_change_answer(self, q, a):  # gets a question number and user answer for it and puts them in self.answers
        answers_dict = json.loads(self.answers)
        answers_dict[q] = a
        self.answers = json.dumps(answers_dict)


class UserScore(models.Model):
    exam = models.ForeignKey(Exam, related_name='exam_scores', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='user_scores', on_delete=models.CASCADE)
    score = models.IntegerField()


# TODO: Lessons models
# TODO: Homeworks models
# TODO: Questionnaire models
