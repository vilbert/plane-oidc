# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.conf import settings
from django.db import models

from .base import BaseModel


class OAuthApplicationInstallation(BaseModel):
    """A workspace that a user authorized an OAuth application to access."""

    class Status(models.TextChoices):
        INSTALLED = "installed", "Installed"
        REVOKED = "revoked", "Revoked"

    application = models.ForeignKey(
        "oauth2_provider.Application",
        related_name="plane_workspace_installations",
        on_delete=models.CASCADE,
    )
    workspace = models.ForeignKey(
        "db.Workspace",
        related_name="oauth_application_installations",
        on_delete=models.CASCADE,
    )
    installed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="oauth_application_installations",
        on_delete=models.CASCADE,
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.INSTALLED)

    class Meta:
        db_table = "oauth_application_installations"
        constraints = [
            models.UniqueConstraint(
                fields=["application", "workspace"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_oauth_application_installation",
            )
        ]


class OAuthGrantContext(models.Model):
    """Temporary workspace context attached to an authorization code."""

    grant = models.OneToOneField(
        "oauth2_provider.Grant",
        primary_key=True,
        related_name="plane_workspace_context",
        on_delete=models.CASCADE,
    )
    installation = models.ForeignKey(OAuthApplicationInstallation, on_delete=models.CASCADE)

    class Meta:
        db_table = "oauth_grant_contexts"


class OAuthTokenContext(models.Model):
    """Workspace boundary carried by an OAuth access/refresh token pair."""

    access_token = models.OneToOneField(
        "oauth2_provider.AccessToken",
        primary_key=True,
        related_name="plane_workspace_context",
        on_delete=models.CASCADE,
    )
    refresh_token = models.OneToOneField(
        "oauth2_provider.RefreshToken",
        related_name="plane_workspace_context",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    installation = models.ForeignKey(OAuthApplicationInstallation, on_delete=models.CASCADE)

    class Meta:
        db_table = "oauth_token_contexts"
