from django.shortcuts import render
from .models import Classroom, Way
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
import json


@login_required
def dashboard(request):
    if request.user.groups.filter(name='Students').exists():
        return render(request, 'LMS/dashboard.html')
    else:
        return reverse_lazy('/home')


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
