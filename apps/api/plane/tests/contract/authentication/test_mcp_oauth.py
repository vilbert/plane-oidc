# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import base64
import hashlib
from datetime import timedelta
from io import StringIO
from urllib.parse import parse_qs, urlparse

import pytest
from django.core.management import call_command
from django.utils import timezone
from oauth2_provider.models import (
    AbstractApplication,
    get_access_token_model,
    get_application_model,
)

from plane.db.models import (
    OAuthApplicationInstallation,
    OAuthTokenContext,
    Workspace,
    WorkspaceMember,
)


pytestmark = pytest.mark.contract


def create_oauth_application(user, redirect_uri="https://mcp.example.com/http/auth/callback"):
    return get_application_model().objects.create(
        user=user,
        name="Plane MCP Server",
        client_id="mcp-client",
        client_secret="mcp-secret",
        client_type=AbstractApplication.CLIENT_CONFIDENTIAL,
        authorization_grant_type=AbstractApplication.GRANT_AUTHORIZATION_CODE,
        redirect_uris=redirect_uri,
    )


@pytest.mark.django_db
def test_register_mcp_oauth_application_outputs_one_time_credentials():
    output = StringIO()

    call_command(
        "register_mcp_oauth_application",
        redirect_uri="https://mcp.example.com/http/auth/callback",
        client_id="registered-mcp-client",
        client_secret="registered-mcp-secret",
        stdout=output,
    )

    application = get_application_model().objects.get(client_id="registered-mcp-client")
    assert application.redirect_uris == "https://mcp.example.com/http/auth/callback"
    assert application.client_secret != "registered-mcp-secret"
    assert "PLANE_OAUTH_PROVIDER_CLIENT_SECRET=registered-mcp-secret" in output.getvalue()


@pytest.mark.django_db
def test_authorization_code_flow_creates_workspace_scoped_bearer_token(api_client, create_user, workspace):
    redirect_uri = "https://mcp.example.com/http/auth/callback"
    application = create_oauth_application(create_user, redirect_uri)
    verifier = "a-secure-pkce-verifier-value-for-plane-mcp-connection"
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()

    api_client.force_login(create_user)
    authorize_url = "/auth/o/authorize-app/"
    authorize_params = {
        "response_type": "code",
        "client_id": application.client_id,
        "redirect_uri": redirect_uri,
        "scope": "read write",
        "state": "test-state",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    response = api_client.get(authorize_url, authorize_params)
    assert response.status_code == 200
    assert workspace.name.encode() in response.content

    response = api_client.post(
        authorize_url,
        {
            **authorize_params,
            "allow": "Authorize",
            "workspace_id": str(workspace.id),
        },
    )
    assert response.status_code == 302
    query = parse_qs(urlparse(response["Location"]).query)
    assert query["state"] == ["test-state"]

    api_client.logout()
    response = api_client.post(
        "/auth/o/token/",
        {
            "grant_type": "authorization_code",
            "code": query["code"][0],
            "redirect_uri": redirect_uri,
            "client_id": application.client_id,
            "client_secret": "mcp-secret",
            "code_verifier": verifier,
        },
    )
    assert response.status_code == 200
    token_payload = response.json()
    access_token_value = token_payload["access_token"]

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token_value}")
    assert api_client.get("/api/v1/users/me/").status_code == 200
    assert api_client.get(f"/api/v1/workspaces/{workspace.slug}/projects/").status_code == 200

    other_workspace = Workspace.objects.create(name="Other Workspace", slug="other-workspace", owner=create_user)
    WorkspaceMember.objects.create(workspace=other_workspace, member=create_user, role=20)
    assert api_client.get(f"/api/v1/workspaces/{other_workspace.slug}/projects/").status_code == 403

    response = api_client.get("/auth/o/app-installation/")
    assert response.status_code == 200
    assert response.json()[0]["workspace_detail"]["slug"] == workspace.slug

    api_client.credentials()
    response = api_client.post(
        "/auth/o/token/",
        {
            "grant_type": "refresh_token",
            "refresh_token": token_payload["refresh_token"],
            "client_id": application.client_id,
            "client_secret": "mcp-secret",
        },
    )
    assert response.status_code == 200
    refreshed_access_token = response.json()["access_token"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refreshed_access_token}")
    assert api_client.get("/auth/o/app-installation/").json()[0]["workspace_detail"]["slug"] == workspace.slug


@pytest.mark.django_db
def test_oauth_installation_endpoint_returns_only_token_workspace(api_client, create_user, workspace):
    application = create_oauth_application(create_user)
    installation = OAuthApplicationInstallation.objects.create(
        application=application,
        workspace=workspace,
        installed_by=create_user,
        status=OAuthApplicationInstallation.Status.INSTALLED,
    )
    access_token = get_access_token_model().objects.create(
        user=create_user,
        application=application,
        token="plane-oauth-access-token",
        scope="read write",
        expires=timezone.now() + timedelta(hours=1),
    )
    OAuthTokenContext.objects.create(access_token=access_token, installation=installation)
    api_client.credentials(HTTP_AUTHORIZATION="Bearer plane-oauth-access-token")

    response = api_client.get("/auth/o/app-installation/")

    assert response.status_code == 200
    assert response.json() == [
        {
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
            "status": "installed",
            "created_by": None,
            "updated_by": None,
            "workspace": str(workspace.id),
            "application": str(application.id),
            "installed_by": str(create_user.id),
            "app_bot": str(create_user.id),
            "webhook": None,
        }
    ]
