# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from urllib.parse import urlencode

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseRedirect
from oauth2_provider.contrib.rest_framework import OAuth2Authentication, TokenHasReadWriteScope
from oauth2_provider.models import get_application_model
from oauth2_provider.views import AuthorizationView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from plane.authentication.oauth.validator import authorization_context_cache_key
from plane.db.models import OAuthApplicationInstallation, OAuthTokenContext, WorkspaceMember


class PlaneAuthorizationView(AuthorizationView):
    """OAuth consent screen that binds the grant to one Plane workspace."""

    template_name = "oauth2_provider/plane_authorize.html"

    def handle_no_permission(self):
        query_params = urlencode({"next_path": self.request.build_absolute_uri()})
        return HttpResponseRedirect(f"{settings.WEB_URL}/login?{query_params}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["workspace_memberships"] = (
            WorkspaceMember.objects.select_related("workspace")
            .filter(
                member=self.request.user,
                is_active=True,
                workspace__deleted_at__isnull=True,
            )
            .order_by("workspace__name")
        )
        return context

    def form_valid(self, form):
        if form.cleaned_data.get("allow"):
            membership = (
                WorkspaceMember.objects.select_related("workspace")
                .filter(
                    member=self.request.user,
                    workspace_id=self.request.POST.get("workspace_id"),
                    is_active=True,
                    workspace__deleted_at__isnull=True,
                )
                .first()
            )
            if membership is None:
                form.add_error(None, "Select a workspace you currently belong to.")
                return self.form_invalid(form)

            application = get_application_model().objects.get(client_id=form.cleaned_data["client_id"])
            installation, created = OAuthApplicationInstallation.objects.get_or_create(
                application=application,
                workspace=membership.workspace,
                defaults={
                    "installed_by": self.request.user,
                    "status": OAuthApplicationInstallation.Status.INSTALLED,
                },
            )
            if not created and installation.status != OAuthApplicationInstallation.Status.INSTALLED:
                installation.status = OAuthApplicationInstallation.Status.INSTALLED
                installation.save(update_fields=["status", "updated_at"])
            cache.set(
                authorization_context_cache_key(
                    application.client_id,
                    self.request.user.id,
                    form.cleaned_data.get("state"),
                ),
                str(installation.id),
                timeout=300,
            )

        return super().form_valid(form)


class OAuthApplicationInstallationEndpoint(APIView):
    """Return the workspace installation associated with the current token."""

    authentication_classes = [OAuth2Authentication]
    permission_classes = [TokenHasReadWriteScope]
    required_scopes = []

    def get(self, request):
        token_context = (
            OAuthTokenContext.objects.select_related(
                "installation__workspace",
                "installation__application",
                "installation__installed_by",
            )
            .filter(
                access_token=request.auth,
                installation__status=OAuthApplicationInstallation.Status.INSTALLED,
                installation__deleted_at__isnull=True,
            )
            .first()
        )
        if token_context is None:
            return Response([], status=status.HTTP_200_OK)

        installation = token_context.installation
        requested_id = request.query_params.get("id")
        if requested_id and str(installation.id) != requested_id:
            return Response([], status=status.HTTP_200_OK)

        workspace = installation.workspace
        data = {
            "id": str(installation.id),
            "workspace_detail": {
                "name": workspace.name,
                "slug": workspace.slug,
                "id": str(workspace.id),
                "logo_url": workspace.logo_url,
            },
            "created_at": installation.created_at.isoformat(),
            "updated_at": installation.updated_at.isoformat(),
            "deleted_at": None,
            "status": installation.status,
            "created_by": str(installation.created_by_id) if installation.created_by_id else None,
            "updated_by": str(installation.updated_by_id) if installation.updated_by_id else None,
            "workspace": str(workspace.id),
            "application": str(installation.application_id),
            "installed_by": str(installation.installed_by_id),
            # The official MCP server validates this field but performs calls as
            # the authorizing user. CE therefore exposes that user as the actor.
            "app_bot": str(installation.installed_by_id),
            "webhook": None,
        }
        return Response([data], status=status.HTTP_200_OK)
