from django.db import migrations


def create_subjects(apps, schema_editor):
    Subject = apps.get_model('classroom', 'Subject')
    Subject.objects.create(name='初級-1', color='#355a40')
    Subject.objects.create(name='初級-2', color='#007bff')
    Subject.objects.create(name='中級-1', color='#28a745')
    Subject.objects.create(name='中級-2', color='#17a2b8')
    Subject.objects.create(name='上級', color='#ffc107')


class Migration(migrations.Migration):

    dependencies = [
        ('classroom', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_subjects),
    ]
