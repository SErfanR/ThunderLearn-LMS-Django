from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from ckeditor.fields import RichTextField


# manager
class PublishedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=Post.Status.PUBLISHED)

# Post model
class Post(models.Model):
    # author
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_posts")
    # main part
    title = models.CharField(max_length=250)
    description = models.TextField()
    body = RichTextField(blank=True)
    slug = models.SlugField(max_length=250)
    # date
    created_time = models.DateTimeField(auto_now_add=True)
    publish_time = models.DateTimeField(default=timezone.now)
    updated_time = models.DateTimeField(auto_now=True)

    # status
    class Status(models.TextChoices):
        DRAFT = 'DF', 'Draft'
        PUBLISHED = 'PB', 'Published'
        ARCHIVED = 'AR', 'Archived'

    status = models.CharField(max_length=2, choices=Status.choices, default=Status.DRAFT)

    objects = models.Manager()
    published = PublishedManager()

    class Meta:
        ordering = ['-publish_time']
        indexes = [
            models.Index(fields=['-publish_time'])
        ]

    def __str__(self):
        return self.title
