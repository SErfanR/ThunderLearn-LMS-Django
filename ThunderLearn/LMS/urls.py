from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('class/<id>/', views.class_detail, name='class_detail'),
    path('way/<id>/', views.way_detail, name='way_detail'),
]

