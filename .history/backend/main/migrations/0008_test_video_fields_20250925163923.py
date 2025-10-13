from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0007_question_semester'),
    ]

    operations = [
        migrations.AddField(
            model_name='test',
            name='video_url',
            field=models.URLField(blank=True, max_length=500, null=True, verbose_name='Video URL (ixtiyoriy)'),
        ),
        migrations.AddField(
            model_name='test',
            name='video_file',
            field=models.FileField(blank=True, null=True, upload_to='test_videos/', verbose_name='Video fayl (ixtiyoriy)'),
        ),
    ]
