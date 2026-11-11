import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('directory', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='KnowledgeEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('body', models.TextField()),
                ('entry_type', models.CharField(choices=[('policy', 'Policy'), ('qna', 'Q&A')], default='qna', max_length=20)),
                ('visibility_departments', models.JSONField(blank=True, default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='knowledge_entries', to='directory.employee')),
            ],
            options={
                'verbose_name_plural': 'knowledge entries',
                'ordering': ['-created_at'],
            },
        ),
    ]
