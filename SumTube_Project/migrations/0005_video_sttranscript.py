# Generated by Django 4.2.2 on 2023-06-20 14:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SumTube_Project', '0004_remove_video_sttranscript'),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='STtranscript',
            field=models.TextField(default='null'),
        ),
    ]
