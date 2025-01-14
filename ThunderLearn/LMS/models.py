from django.db import models
from django.contrib.auth.models import User


class Classroom(models.Model):
    name = models.CharField(max_length=250)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teacher_class')
    students = models.ManyToManyField(User, related_name='student_class')

    def add_student(self, user):  # adding a student (a user in student group to classroom)
        if user.groups.filter(name='student').exists():
            self.students.add(user)
