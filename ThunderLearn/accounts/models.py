from django.db import models
from django.contrib.auth.models import User

class UserAvatar(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='avatar')
    avatar = models.ImageField(upload_to='static/avatars/')
