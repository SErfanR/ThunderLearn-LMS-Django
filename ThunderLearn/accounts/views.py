from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import FormView
from .forms import RegisterForm
from .models import Settings
from django.contrib.auth import login
from django.shortcuts import redirect


class UserLoginView(LoginView):
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('dashboard')

    def form_invalid(self, form):
        messages.error(self.request, 'نام کاربری یا رمز عبور اشتباه است')
        return self.render_to_response(self.get_context_data(form=form))


class RegisterView(FormView):
    template_name = 'accounts/register.html'
    form_class = RegisterForm
    redirect_authenticated_user = True
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        user = form.save()
        if user:
            login(self.request, user)

        return super(RegisterView, self).form_valid(form)


def change_theme(request):
    if request.user.settings.exists():  # Fixed typo from 'exsits' to 'exists'
        settings = request.user.settings.first()  # Need to get the first object
        if settings.theme:
            settings.theme = False
        else:
            settings.theme = True
        settings.save()
    else:
        settings = Settings.objects.create(user=request.user, theme=True)  # Fixed 'object' to 'objects'

    # Redirect to the previous page
    return redirect(request.META.get('HTTP_REFERER', '/'))  # Fallback to home if no referer

