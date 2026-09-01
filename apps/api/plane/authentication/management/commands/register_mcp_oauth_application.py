# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.core.management.base import BaseCommand, CommandError
from oauth2_provider.models import AbstractApplication, get_application_model


class Command(BaseCommand):
    help = "Register a confidential OAuth application for a Plane MCP server"

    def add_arguments(self, parser):
        parser.add_argument("--redirect-uri", required=True, help="The MCP server's Plane callback URL")
        parser.add_argument("--name", default="Plane MCP Server")
        parser.add_argument("--client-id")
        parser.add_argument("--client-secret")

    def handle(self, *args, **options):
        redirect_uri = options["redirect_uri"].strip()
        if not redirect_uri.startswith(("https://", "http://localhost", "http://127.0.0.1")):
            raise CommandError("Redirect URI must use HTTPS (localhost HTTP is allowed for development)")

        application_model = get_application_model()
        application = application_model(
            name=options["name"],
            client_type=AbstractApplication.CLIENT_CONFIDENTIAL,
            authorization_grant_type=AbstractApplication.GRANT_AUTHORIZATION_CODE,
            redirect_uris=redirect_uri,
        )
        if options.get("client_id"):
            application.client_id = options["client_id"]
        if options.get("client_secret"):
            application.client_secret = options["client_secret"]

        raw_secret = application.client_secret
        application.save()

        self.stdout.write(self.style.SUCCESS("Registered Plane MCP OAuth application"))
        self.stdout.write(f"PLANE_OAUTH_PROVIDER_CLIENT_ID={application.client_id}")
        self.stdout.write(f"PLANE_OAUTH_PROVIDER_CLIENT_SECRET={raw_secret}")
        self.stdout.write(f"Redirect URI: {redirect_uri}")
        self.stdout.write("Store the client secret now; Plane keeps only its hash.")
