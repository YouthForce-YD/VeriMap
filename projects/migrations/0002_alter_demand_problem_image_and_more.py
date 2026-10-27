import django.core.validators
import projects.models
from decimal import Decimal
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='demand',
            name='problem_image',
            field=models.ImageField(blank=True, null=True, upload_to='demands/images/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']), projects.models.validate_max_file_size]),
        ),
        migrations.AlterField(
            model_name='demand',
            name='requested_amount',
            field=models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('1000.00')), django.core.validators.MaxValueValidator(Decimal('50000000.00'))]),
        ),
        migrations.AlterField(
            model_name='demand',
            name='supporting_document',
            field=models.FileField(blank=True, null=True, upload_to='demands/docs/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png']), projects.models.validate_max_file_size]),
        ),
        migrations.AlterField(
            model_name='projectprogress',
            name='proof_image',
            field=models.ImageField(blank=True, null=True, upload_to='progress/proofs/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']), projects.models.validate_max_file_size]),
        ),
    ]
