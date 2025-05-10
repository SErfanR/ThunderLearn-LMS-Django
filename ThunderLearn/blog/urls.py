from django.urls import path
from . import views

urlpatterns = [
    path('posts/', views.PostListView.as_view(), name='post_list'),
    path('posts/<int:pk>/', views.redirect_to_post, name='post_redirect'),
    path('posts/<int:pk>/<slug>/', views.PostDetailView.as_view(), name='post_detail'),
]