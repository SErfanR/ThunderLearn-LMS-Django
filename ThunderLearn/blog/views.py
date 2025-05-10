from .models import Post
from django.views.generic import ListView, DetailView
from django.http import Http404
from django.shortcuts import redirect


class PostListView (ListView):
    queryset = Post.published.all()
    context_object_name = 'posts'
    paginate_by = 3
    template_name = "blog/post_list.html"


class PostDetailView (DetailView):
    model = Post
    template_name = 'blog/post_detail.html'


def redirect_to_post(request, pk):
    try:
        this_post = Post.published.get(pk=pk)
    except:
        raise Http404
    return redirect('post_detail', pk=pk, slug=this_post.slug)

