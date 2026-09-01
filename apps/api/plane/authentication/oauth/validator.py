# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import hashlib

from django.core.cache import cache
from oauth2_provider.models import get_grant_model
from oauth2_provider.oauth2_validators import OAuth2Validator

from plane.db.models import OAuthGrantContext, OAuthTokenContext


def authorization_context_cache_key(client_id, user_id, state):
    value = f"{client_id}:{user_id}:{state or ''}".encode()
    return f"plane_oauth_authorization:{hashlib.sha256(value).hexdigest()}"


class PlaneOAuth2Validator(OAuth2Validator):
    """Carry the selected Plane workspace from a grant into issued tokens."""

    def validate_refresh_token(self, refresh_token, client, request, *args, **kwargs):
        is_valid = super().validate_refresh_token(
            refresh_token,
            client,
            request,
            *args,
            **kwargs,
        )
        if not is_valid:
            return False

        # django-oauth-toolkit revokes the previous access token before it creates
        # the rotated pair. Preserve the installation ID on the request before that
        # cascade deletes our old token context.
        request.plane_oauth_installation_id = (
            OAuthTokenContext.objects.filter(
                refresh_token=request.refresh_token_instance,
            )
            .values_list("installation_id", flat=True)
            .first()
        )
        return True

    def save_authorization_code(self, client_id, code, request, *args, **kwargs):
        super().save_authorization_code(client_id, code, request, *args, **kwargs)

        cache_key = authorization_context_cache_key(client_id, request.user.id, request.state)
        installation_id = cache.get(cache_key)
        cache.delete(cache_key)
        if not installation_id:
            return

        grant = get_grant_model().objects.filter(code=code["code"], application=request.client).first()
        if grant:
            OAuthGrantContext.objects.create(grant=grant, installation_id=installation_id)

    def _create_access_token(self, expires, request, token, source_refresh_token=None):
        access_token = super()._create_access_token(expires, request, token, source_refresh_token)

        installation_id = getattr(request, "plane_oauth_installation_id", None)
        if not installation_id and source_refresh_token:
            previous_context = (
                OAuthTokenContext.objects.select_related("installation")
                .filter(refresh_token=source_refresh_token)
                .first()
            )
            if previous_context:
                installation_id = previous_context.installation_id
        elif getattr(request, "code", None):
            grant = get_grant_model().objects.filter(code=request.code, application=request.client).first()
            if grant:
                grant_context = OAuthGrantContext.objects.select_related("installation").filter(grant=grant).first()
                if grant_context:
                    installation_id = grant_context.installation_id

        if installation_id:
            OAuthTokenContext.objects.create(
                access_token=access_token,
                installation_id=installation_id,
            )
        return access_token

    def _create_refresh_token(self, request, refresh_token_code, access_token, previous_refresh_token):
        refresh_token = super()._create_refresh_token(
            request,
            refresh_token_code,
            access_token,
            previous_refresh_token,
        )
        OAuthTokenContext.objects.filter(access_token=access_token).update(refresh_token=refresh_token)
        return refresh_token
