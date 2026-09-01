# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import SAFE_METHODS

from plane.db.models import OAuthTokenContext


class PlaneOAuth2Authentication(OAuth2Authentication):
    """Authenticate Bearer tokens and enforce their workspace and read/write scope."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, access_token = result
        required_scope = "read" if request.method.upper() in SAFE_METHODS else "write"
        if not access_token.is_valid([required_scope]):
            raise AuthenticationFailed(f"OAuth token does not grant the {required_scope} scope")

        resolver_match = getattr(request._request, "resolver_match", None)
        route_kwargs = resolver_match.kwargs if resolver_match else {}
        workspace_slug = route_kwargs.get("slug") or route_kwargs.get("workspace_slug")

        if workspace_slug:
            token_context = (
                OAuthTokenContext.objects.select_related("installation__workspace")
                .filter(
                    access_token=access_token,
                    installation__status="installed",
                    installation__deleted_at__isnull=True,
                )
                .first()
            )
            if token_context is None or token_context.installation.workspace.slug != workspace_slug:
                raise AuthenticationFailed("OAuth token is not authorized for this workspace")

        return user, access_token
