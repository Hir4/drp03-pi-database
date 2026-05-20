from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_task_completion_workflow"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="is_archived",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="project",
            name="manager",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="managed_projects", to="core.user"),
        ),
        migrations.AddField(
            model_name="task",
            name="is_archived",
            field=models.BooleanField(default=False),
        ),
    ]