from django.urls import path, re_path
from django.contrib import admin
from . import views

app_name = 'SumTube_Project'

urlpatterns = [
    path("", views.index),
    path("", views.index, name='index'),
    path('admin/', admin.site.urls),
    re_path('results/', views.add_transcript, name='results'),
    # re_path('add_transcript/', views.add_transcript, name='add_transcript'),
    path("add_transcript/", views.add_transcript, name="add_transcript"),
    re_path('post_ticket/', views.post_ticket, name='post_ticket'),
    
]

# urlpatterns = [
#     path("", views.index),
#     path('', views.index, name='index'),
#     path('results/', views.get_results, name='results'),
# ]
