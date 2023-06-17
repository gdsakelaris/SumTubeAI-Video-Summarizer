# from django.urls import path, re_path
# # from django.contrib import admin
# from . import views

# app_name = 'SumTube_Project'

# urlpatterns = [
#     path('', views.index, name='index'),
#     re_path('results/', views.add_transcript, name='results'),
#     # path("", views.index),
#     # re_path('results/', views.add_transcript, name='results'),
#     # path('admin/', admin.site.urls),
#     # re_path('add_transcript/', views.add_transcript, name='add_transcript'),
#     # re_path('contact/', views.contact, name='contact'),
#     # re_path('post_ticket/', views.post_ticket, name='post_ticket'),
#     # re_path('get_contact/', views.get_contact, name='get_contact'),
#     # path("save_transcript/", views.save_transcript, name="save_transcript"),
# ]
from django.urls import path
from . import views

app_name = 'SumTube_Project'

urlpatterns = [
    path('', views.index, name='index'),
    path('results/', views.get_results, name='results'),
]
