# Generated by Django 4.2.2 on 2023-06-20 13:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SumTube_Project', '0002_delete_ticket_rename_gptraw_video_straw_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='YTtranscript',
            field=models.TextField(default='null'),
        ),
    ]
