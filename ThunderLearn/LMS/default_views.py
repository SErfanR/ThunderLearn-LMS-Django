# mixins
from django.contrib.auth.mixins import LoginRequiredMixin

# messages imports + mixins
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages

# redirecting, rendering and etc
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy

# views imports
from django.views.generic.edit import DeleteView, CreateView
from django.views.generic import UpdateView


class DefaultCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """
    A default CreateView that has many futures and is a child class of LoginRequiredMixin, SuccessMessageMixin and CreateView

    Attributes:
        fields (list[str]): List of fields to be displayed in the form.
        success_message (str): Message to display when the object is successfully updated.
        unauthorized_message (str): Message to display when the user is not authorized to update the object.
        error_redirect_url (str): URL to redirect to if the user is not authorized.
        success_redirect_url (str): Base URL to redirect to after a successful update.
    """

    fields = ['body']
    success_message = 'آیتم با موفقیت ایجاد شد'
    unauthorized_message = 'شما به این صفحه دسترسی ندارید'
    error_redirect_url = 'dashboard'
    success_redirect_url = 'teacher_exam'

    def get_queryset(self):
        """
        Optimize database queries by using select_related and only to fetch necessary fields
        this method must be overridden in child classes
        """
        raise NotImplementedError('get_queryset is a necessary method and should be overridden')

    def setup(self, request, *args, **kwargs):
        """
        Retrieve the object using an optimized queryset and raising 404 if it does not exist.
        """

        # Store the object in self.object to avoid redundant calls.
        queryset = self.get_queryset()
        self.obj = get_object_or_404(queryset, pk=kwargs['pk'])

        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        """
        Check if the user has permission to create this object.
        """

        if not self.is_user_authorized():
            messages.error(self.request, message=self.unauthorized_message)
            return redirect(self.error_redirect_url)
        return super().dispatch(request, *args, **kwargs)

    def is_user_authorized(self) -> bool:
        """
        Checking if the user is authorized to change this objects.
        this method must be overridden in child classes.
        """
        raise NotImplementedError('is_user_authorized is a necessary method and should be overridden')

    def get_success_url(self) -> str:
        """
        Redirect to a page with a fragment pointing to the related question.
        """
        url = reverse_lazy(self.success_redirect_url, args=self.get_success_url_args())
        fragment = self.get_success_url_fragment()
        return f'{url}{fragment}'

    def get_success_url_args(self) -> list:
        """
        Returning the args to get_success_url.
        """
        return []

    def get_success_url_fragment(self) -> str:
        """
        Returning the fragment to get_success_url.
        """
        return ''


class DefaultUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """
    A default UpdateView that has many futures and is a child class of LoginRequiredMixin, SuccessMessageMixin and UpdateView

    Attributes:
        fields (list[str]): List of fields to be displayed in the form.
        success_message (str): Message to display when the object is successfully updated.
        error_message (str): Message to display when no changes are made to the object.
        unauthorized_message (str): Message to display when the user is not authorized to update the object.
        error_redirect_url (str): URL to redirect to if the user is not authorized.
        success_redirect_url (str): Base URL to redirect to after a successful update.
    """

    fields = ['body']
    success_message = 'آیتم با موفقیت تغییر کرد'
    error_message = 'بدنه آیتم تغییری نکرده است'
    unauthorized_message = 'شما به این صفحه دسترسی ندارید'
    error_redirect_url = 'dashboard'
    success_redirect_url = 'teacher_exam'

    def get_queryset(self):
        """
        Optimize database queries by using select_related and only to fetch necessary fields
        this method must be overridden in child classes
        """
        raise NotImplementedError('get_queryset is a necessary method and should be overridden')

    def setup(self, request, *args, **kwargs):
        """
        Retrieve the object using an optimized queryset and raising 404 if it does not exist.
        """

        # Store the object in self.object to avoid redundant calls.
        queryset = self.get_queryset()
        self.object = get_object_or_404(queryset, pk=kwargs['pk'])

        # Store the object data in self.data to compare with form data
        self.data = {field: str(getattr(self.object, field)).strip() for field in self.fields}

        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        """
        Check if the user has permission to update this object.
        """
        if not self.is_user_authorized():
            messages.error(self.request, message=self.unauthorized_message)
            return redirect(self.error_redirect_url)
        return super().dispatch(request, *args, **kwargs)

    def is_user_authorized(self) -> bool:
        """
        Checking if the user is authorized to change this objects.
        this method must be overridden in child classes.
        """
        raise NotImplementedError('is_user_authorized is a necessary method and should be overridden')

    def form_valid(self, form):
        """
        Check if the new body is the same as the current body.
        If they are the same, show an error message and do not save the changes.
        """
        new_data = form.cleaned_data

        # checking if data is not changed
        if new_data == self.data:
            messages.error(self.request, message=self.error_message)
            url = self.get_success_url()
            return redirect(url)
        return super().form_valid(form)

    def get_success_url(self) -> str:
        """
        Redirect to a page with a fragment pointing to the related question.
        """
        url = reverse_lazy(self.success_redirect_url, args=self.get_success_url_args())
        fragment = self.get_success_url_fragment()
        return f'{url}{fragment}'

    def get_success_url_args(self) -> list:
        """
        Returning the args to get_success_url.
        """
        return []

    def get_success_url_fragment(self) -> str:
        """
        Returning the fragment to get_success_url.
        """
        return ''
