from django.urls import path, re_path
from django.contrib import admin
from django.shortcuts import redirect
from . import views

app_name = 'SumTube_Project'

urlpatterns = [
    path("", views.index, name='index'),
    path("add_transcript/", views.add_transcript, name="add_transcript"),
    path("", views.index),
    path('admin/', admin.site.urls),
    re_path('results/', views.add_transcript, name='results'),
    re_path('post_ticket/', views.post_ticket, name='post_ticket'), 
    # path('', lambda request: redirect('/accounts/login/?next=/'), name='root-redirect'),
]

