from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_studenttest_overridden_at_studenttest_overridden_by_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='test',
            name='pass_percent',
            field=models.PositiveIntegerField(default=56, help_text="Talabaning foiz natijasi shu qiymatdan >= bo'lsa o'tgan hisoblanadi", verbose_name="O'tish foizi"),
        ),
    ]
