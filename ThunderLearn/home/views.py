from django.views.generic import TemplateView

class HomeView(TemplateView):
    template_name = 'home/home.html'


class AboutUsView(TemplateView):
    template_name = 'home/about_us.html'


class ContactUsView(TemplateView):
    template_name = 'home/contact_us.html'


class GuideView(TemplateView):
    template_name = 'home/guide.html'
