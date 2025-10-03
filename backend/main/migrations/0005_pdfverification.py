from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_test_pass_percent'),
    ]

    operations = [
        migrations.CreateModel(
            name='PdfVerification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hash_code', models.CharField(max_length=32, unique=True, verbose_name='QR hash')),
                ('subject_name', models.CharField(max_length=255, verbose_name='Fan nomi')),
                ('record_count', models.PositiveIntegerField(default=0, verbose_name='Qatorlar soni')),
                ('payload', models.TextField(verbose_name="Asl ma'lumot")),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('generated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pdf_verifications', to='main.user')),
            ],
            options={
                'verbose_name': 'PDF tasdiq (QR)',
                'verbose_name_plural': 'PDF tasdiqlar (QR)',
                'ordering': ['-created_at'],
            },
        ),
    ]
