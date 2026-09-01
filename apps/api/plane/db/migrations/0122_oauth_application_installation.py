# Generated manually for the Community Edition OAuth provider.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0121_alter_estimate_type"),
        ("oauth2_provider", "0020_cimd_application_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="OAuthApplicationInstallation",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Last Modified At"),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Deleted At"),
                ),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("installed", "Installed"), ("revoked", "Revoked")],
                        default="installed",
                        max_length=16,
                    ),
                ),
                (
                    "application",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="plane_workspace_installations",
                        to="oauth2_provider.application",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "installed_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="oauth_application_installations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="oauth_application_installations",
                        to="db.workspace",
                    ),
                ),
            ],
            options={"db_table": "oauth_application_installations"},
        ),
        migrations.CreateModel(
            name="OAuthGrantContext",
            fields=[
                (
                    "grant",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="plane_workspace_context",
                        serialize=False,
                        to="oauth2_provider.grant",
                    ),
                ),
                (
                    "installation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="db.oauthapplicationinstallation",
                    ),
                ),
            ],
            options={"db_table": "oauth_grant_contexts"},
        ),
        migrations.CreateModel(
            name="OAuthTokenContext",
            fields=[
                (
                    "access_token",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="plane_workspace_context",
                        serialize=False,
                        to="oauth2_provider.accesstoken",
                    ),
                ),
                (
                    "installation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="db.oauthapplicationinstallation",
                    ),
                ),
                (
                    "refresh_token",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="plane_workspace_context",
                        to="oauth2_provider.refreshtoken",
                    ),
                ),
            ],
            options={"db_table": "oauth_token_contexts"},
        ),
        migrations.AddConstraint(
            model_name="oauthapplicationinstallation",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True)),
                fields=("application", "workspace"),
                name="unique_active_oauth_application_installation",
            ),
        ),
    ]
