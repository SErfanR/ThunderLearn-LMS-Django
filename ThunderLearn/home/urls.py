from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('about_us/', views.AboutUsView.as_view(), name='about_us'),
    path('contact_us/', views.ContactUsView.as_view(), name='contact_us'),
    path('guide/', views.GuideView.as_view(), name='guide'),
]