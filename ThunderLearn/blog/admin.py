from django.contrib import admin
from .models import Post

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'created_time', 'publish_time', 'status']
    list_filter = ['status', 'author']
    list_editable = ['status']
    search_fields = ['title', 'description']
    prepopulated_fields = {"slug": ['title']}
