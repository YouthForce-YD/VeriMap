
import django.core.validators
import projects.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0002_alter_demand_problem_image_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='demand',
            name='problem_image',
            field=models.ImageField(blank=True, null=True, upload_to=projects.models.get_demand_image_path, validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']), projects.models.validate_max_file_size, projects.models.validate_image_content]),
        ),
        migrations.AlterField(
            model_name='demand',
            name='supporting_document',
            field=models.FileField(blank=True, null=True, upload_to=projects.models.get_demand_doc_path, validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png']), projects.models.validate_max_file_size, projects.models.validate_document_content]),
        ),
        migrations.AlterField(
            model_name='projectprogress',
            name='proof_image',
            field=models.ImageField(blank=True, null=True, upload_to=projects.models.get_proof_image_path, validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']), projects.models.validate_max_file_size, projects.models.validate_image_content]),
        ),
    ]
