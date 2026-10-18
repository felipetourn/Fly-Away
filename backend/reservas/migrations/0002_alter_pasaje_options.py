from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reservas', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='pasaje',
            options={'ordering': ['codigo_pasaje']},
        ),
    ]
