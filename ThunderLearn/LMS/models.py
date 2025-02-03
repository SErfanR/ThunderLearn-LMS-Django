from django.db import models
from django.contrib.auth.models import User


class Classroom(models.Model):
    name = models.CharField(max_length=150, unique=True)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teacher_class')
    students = models.ManyToManyField(User, related_name='student_class', blank=True)
    assistants = models.ManyToManyField(User, related_name='assistant_class', blank=True)

    def add_student(self, user):  # adding a student (a user in student group to classroom)
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


# Exams models
class Exam(models.Model):
    title = models.CharField(max_length=50)
    des = models.TextField()
    author = models.ForeignKey(User, related_name='user_exams', on_delete=models.CASCADE)
    classrooms = models.ManyToManyField(Classroom, related_name='class_exams')
    # TODO: timed exm options and start and finish date_time


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


# TODO: lessons models
