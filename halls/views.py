from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import generic
from django.contrib.auth.forms import UserCreationForm
from .models import Hall, Video
from django.contrib.auth import authenticate, login
from .form import VideoForm, SearchForm
# from django.forms import formset_factory
from django.http import Http404, JsonResponse
import urllib
import requests
from django.forms.utils import ErrorList
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
import local_loading
import os

YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')

def home(request):
    recent_halls = Hall.objects.all().order_by('-id')[:3]
    # popular_halls = [Hall.objects.get(pk=2), Hall.objects.get(pk=3), Hall.objects.get(pk=4)]
    popular_halls = []

    return render(request, 'halls/home.html', {'recent_halls':recent_halls, 'popular_halls':popular_halls})


@login_required
def dashboard(request):
    halls = Hall.objects.filter(user=request.user)

    return render(request, 'halls/dashboard.html', {'halls':halls})

@login_required
def add_video(request, pk):
    form = VideoForm()
    search_form = SearchForm()
    hall = Hall.objects.get(pk = pk)

    if not hall.user == request.user:
        raise Http404

    if request.method == 'POST':
        #Create
        form = VideoForm(request.POST)
        if form.is_valid():
            video = Video()
            video.hall = hall
            video.url = form.cleaned_data['url']

            parse_url = urllib.parse.urlparse(video.url)
            video_id = urllib.parse.parse_qs(parse_url.query).get('v')
            if video_id:
                video.youtube_id = video_id[0]

                endpoint = 'https://www.googleapis.com/youtube/v3/videos?part=snippet&id={}&key={}'.format(video_id[0], YOUTUBE_API_KEY)
                response = requests.get(endpoint)
                json = response.json()
                title = json['items'][0]['snippet']['title']
                video.title = title

                video.save()

                return redirect('detail_hall', pk)
            else:
                errors = form._errors.setdefault('url', ErrorList())
                errors.append('Need to be a YouTube URL')


    return render(request, 'halls/add_video.html', {'form':form, 'search_form':search_form, 'hall':hall})

@login_required
def video_search(request):
    search_form = SearchForm(request.GET)
    if search_form.is_valid():
        encoded_search_term = urllib.parse.quote(search_form.cleaned_data['search_term'])
        # print(encoded_search_term)
        endpoint = 'https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=6&q={}&key={}'.format(encoded_search_term, YOUTUBE_API_KEY)
        response = requests.get(endpoint)
        return JsonResponse(response.json())
    return JsonResponse({'error':'Not able to validate form'})

class DeleteVideo(LoginRequiredMixin, generic.DeleteView):
    model = Video
    template_name = 'halls/delete_video.html'
    success_url = reverse_lazy('dashboard')

    def get_object(self):
        video = super().get_object()
        if not video.hall.user == self.request.user:
            raise Http404
        return video

class Signup(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('home')
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        view = super(Signup, self).form_valid(form)
        username, password = form.cleaned_data.get('username'), form.cleaned_data.get('password1')
        user = authenticate(username=username, password=password)
        login(self.request, user)
        return view

class CreateHall(LoginRequiredMixin, generic.CreateView):
    model = Hall
    fields = ['title']
    template_name = 'halls/create_hall.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        form.instance.user = self.request.user
        super(CreateHall, self).form_valid(form)
        return redirect('dashboard')

class DetailHall(generic.DetailView):
    model = Hall
    template_name = 'halls/detail_hall.html'

class UpdateHall(LoginRequiredMixin, generic.UpdateView):
    model = Hall
    template_name = 'halls/update_hall.html'
    fields = ['title']
    success_url = reverse_lazy('dashboard')

    def get_object(self):
        hall = super().get_object()
        if not hall.user == self.request.user:
            raise Http404
        return hall

class DeleteHall(LoginRequiredMixin, generic.DeleteView):
    model = Hall
    template_name = 'halls/delete_hall.html'
    success_url = reverse_lazy('dashboard')

    def get_object(self):
        hall = super().get_object()
        if not hall.user == self.request.user:
            raise Http404
        return hall