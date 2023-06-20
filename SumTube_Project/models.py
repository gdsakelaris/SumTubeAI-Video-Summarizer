from django.db import models

from django.contrib.auth.models import User

# Create your models here.


class Video(models.Model):
    ytId = models.TextField(max_length=20, default='null')
    url = models.CharField(max_length=200, default='null')
    lang = models.CharField(max_length=30, default='null')
    title = models.CharField(max_length=200, default='null')
    description = models.TextField(default='null')
    published_date = models.DateField(default='null')
    STtranscript = models.TextField(default='null')
    YTtranscript = models.TextField(default='null')
    STRaw = models.TextField(default='null')
    STSummary = models.TextField(default='null')
    STRec1 = models.TextField(default='null')
    STRec2 = models.TextField(default='null')

    def __str__(self):
        return self.ytId + " | " + self.lang + " | " + self.title


# class Ticket(models.Model):
#     name = models.CharField(max_length=100)
#     surname = models.CharField(max_length=100)
#     email = models.EmailField()
#     message = models.TextField()

#     def __str__(self):
#         return f"{self.name} {self.surname}"
