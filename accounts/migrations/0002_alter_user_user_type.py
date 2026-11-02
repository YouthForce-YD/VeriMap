
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='user_type',
            field=models.CharField(choices=[('donor', 'Donor'), ('receiver', 'Receiver'), ('admin', 'Admin')], default='donor', max_length=15),
        ),
    ]
