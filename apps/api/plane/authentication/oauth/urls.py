# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path
from oauth2_provider import views as oauth2_views

from plane.authentication.oauth.views import OAuthApplicationInstallationEndpoint, PlaneAuthorizationView


urlpatterns = [
    path("authorize-app/", PlaneAuthorizationView.as_view(), name="oauth-authorize-app"),
    path("token/", oauth2_views.TokenView.as_view(), name="oauth-token"),
    path("revoke-token/", oauth2_views.RevokeTokenView.as_view(), name="oauth-revoke-token"),
    path(
        "app-installation/",
        OAuthApplicationInstallationEndpoint.as_view(),
        name="oauth-app-installation",
    ),
]
