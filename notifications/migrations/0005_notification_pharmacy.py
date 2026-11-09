import django.db.models.deletion
from django.db import migrations, models


def assign_notifications_to_recipient_pharmacy(apps, schema_editor):
    database = schema_editor.connection.alias
    Notification = apps.get_model('notifications', 'Notification')
    notifications = Notification.objects.using(database).select_related('recipient')
    for notification in notifications.iterator():
        notification.pharmacy_id = notification.recipient.pharmacy_id
        notification.save(update_fields=['pharmacy'])


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0006_pharmacy_tenant_scoping'),
        ('notifications', '0004_alter_notification_actor_alter_notification_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='pharmacy',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='%(class)s_records',
                to='app.pharmacy',
            ),
        ),
        migrations.RunPython(
            assign_notifications_to_recipient_pharmacy,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='notification',
            name='pharmacy',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='%(class)s_records',
                to='app.pharmacy',
            ),
        ),
    ]
