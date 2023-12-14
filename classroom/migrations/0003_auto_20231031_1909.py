from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('classroom', '0002_create_initial_subjects'),
    ]

    operations = [
        migrations.AlterField(
            model_name='student',
            name='lebel',
            field=models.ManyToManyField(related_name='interested_students', to='classroom.Subject'),
        ),
    ]
