<br /><br />

<p align="center">
<a href="https://plane.so">
  <img src="https://media.docs.plane.so/logo/plane_github_readme.png" alt="Plane Logo" width="400">
</a>
</p>
<p align="center"><b>Modern project management for all teams</b></p>

<p align="center">
    <a href="https://plane.so/"><b>Website</b></a> •
    <a href="https://forum.plane.so"><b>Forum</b></a> •
    <a href="https://x.com/planepowers"><b>X</b></a> •
    <a href="https://docs.plane.so/"><b>Documentation</b></a>
</p>

> This is a fork of [makeplane/plane](https://github.com/makeplane/plane) with OIDC/SSO support added to the Community Edition. For general Plane documentation, see the [official docs](https://docs.plane.so/).
>
> This fork is based on [jiyang1018/plane-oidc](https://github.com/jiyang1018/plane-oidc).

## 🔐 What's different in this fork

### OIDC / SSO Authentication
Plane Community Edition does not support OIDC/SSO. This fork adds it.

- OIDC login button on the login page (configurable display name and icon)
- OIDC configuration page in God Mode (`/god-mode/authentication/oidc/`)
- OIDC users bypass the signup restriction — existing accounts log in normally, new accounts are created automatically
- Works with any OIDC-compliant provider: Authentik, Keycloak, Nextcloud, Azure AD, etc.

### OAuth for the Plane MCP server
This fork also exposes Plane's OAuth authorization-server endpoints to Community Edition, so a remote
[Plane MCP server](https://github.com/makeplane/plane-mcp-server) can authenticate each user without a shared PAT.

- Authorization, token, revocation, and installation endpoints under `/auth/o/`
- Authorization-code flow with PKCE and rotating refresh tokens
- A consent screen that binds every token to one workspace
- Bearer-token support on `/api/v1/`, restricted to the authorized workspace
- CLI-based confidential client registration (the client secret is shown only once)

### God Mode enhancements
- **Members page** (`/god-mode/members/`) — list all users, activate/deactivate/delete
- **Auto Assign workspaces** — in the Workspaces page, check which workspaces new OIDC users are automatically added to (supports multiple). Only visible when "Prevent workspace creation" is enabled.

---

## 🐳 Docker images

Pre-built images on GitHub Container Registry, updated on every push to `preview`:

| Service | Image |
|---|---|
| Backend | `ghcr.io/vilbert/plane-backend-oidc:preview` |
| Web | `ghcr.io/vilbert/plane-web-oidc:preview` |
| Admin | `ghcr.io/vilbert/plane-admin-oidc:preview` |
| Space | `ghcr.io/vilbert/plane-space-oidc:preview` |
| Live | `ghcr.io/vilbert/plane-live-oidc:preview` |

Use the official `makeplane` images for `proxy`, `db`, `redis`, `minio`, and `mq` — they are unchanged.

---

## 🚀 Setup

### 1. Deploy Plane
Follow the [official self-hosting guide](https://developers.plane.so/self-hosting/methods/docker-compose), then replace the `makeplane/*` images in your `docker-compose.yml` with the images above.

### 2. Configure OIDC
Go to `https://your-plane-domain/god-mode/authentication/oidc/` and fill in:

| Field | Description |
|---|---|
| Discovery URL | Your provider's `.well-known/openid-configuration` URL |
| Client ID | From your OIDC provider |
| Client Secret | From your OIDC provider |
| Display Name | Label on the login button (e.g. `SSO`, `Authentik`, `Nextcloud`) |
| Icon URL | Optional — URL to a custom icon for the login button |

Enable the toggle and save. Then register the callback URL with your OIDC provider:
```
https://your-plane-domain/auth/oidc/callback/
```

### 3. NAT hairpinning (self-hosted OIDC providers)
If your OIDC provider is on the same local network as Plane, add `extra_hosts` to all backend services in `docker-compose.yml`:
```yaml
    extra_hosts:
      - "your-oidc-domain.com:your-server-ip"
```

### 4. Bundle the MCP server (optional)

The [upstream `makeplane/plane-mcp-server`](https://github.com/makeplane/plane-mcp-server) (MIT) is included as a pre-built sidecar container. It starts automatically with `docker compose up` and is reachable at the same domain under `/http/`:

| Transport | URL |
|---|---|
| OAuth (per-user) | `https://plane.example.com/http/mcp` |
| Personal Access Token | `https://plane.example.com/http/api-key/mcp` |

#### 4a. Register the OAuth client (once)

Fill in the three MCP URL vars in `.env` first, then run:

```bash
docker compose exec api python manage.py register_mcp_oauth_application \
  --name "Plane MCP Server" \
  --redirect-uri "${MCP_OAUTH_PROVIDER_BASE_URL}/auth/callback"
```

Copy the emitted client ID and client secret into `.env`:

```dotenv
PLANE_OAUTH_PROVIDER_CLIENT_ID=<client-id>
PLANE_OAUTH_PROVIDER_CLIENT_SECRET=<client-secret>
MCP_PLANE_PUBLIC_URL=https://plane.example.com
MCP_PLANE_INTERNAL_URL=http://api:8000
MCP_OAUTH_PROVIDER_BASE_URL=https://plane.example.com/http
```

Then restart the container to pick up the new env:

```bash
docker compose up -d mcp-server
```

#### 4b. Connect an MCP client

Point your MCP client at the OAuth endpoint:

```json
{
  "mcpServers": {
    "plane": {
      "command": "npx",
      "args": ["mcp-remote@latest", "https://plane.example.com/http/mcp"]
    }
  }
}
```

The browser will open the Plane OAuth consent screen where the user picks one of their workspaces. The access token is workspace-scoped and rotated automatically.

For PAT-based auth (no browser flow, no OAuth), use the `/http/api-key/mcp` endpoint instead and supply your [Plane API token](https://docs.plane.so/) in the request headers:

```json
{
  "mcpServers": {
    "plane": {
      "command": "npx",
      "args": ["mcp-remote@latest", "https://plane.example.com/http/api-key/mcp"],
      "headers": {
        "Authorization": "Bearer <your-pat>",
        "X-Workspace-slug": "<your-workspace-slug>"
      }
    }
  }
}
```

> **Upgrading the MCP server:** pin the image tag in `docker-compose.yml` (`image: makeplane/plane-mcp-server:<tag>`) for reproducible deploys. To upgrade, change the tag and `docker compose pull mcp-server && docker compose up -d mcp-server`.
>
> **Self-hosted OIDC alongside:** if your OIDC provider is on the same local network as Plane, add `extra_hosts` to the `mcp-server` service in `docker-compose.yml`:
> ```yaml
>     extra_hosts:
>       - "your-oidc-domain.com:your-server-ip"
> ```

---

## ✅ Tested with
- Nextcloud (with OIDC provider app)
- Authentik
- Keycloak

---

## 🔄 Keeping up to date with upstream

```bash
git remote add upstream https://github.com/makeplane/plane.git
git fetch upstream
git merge upstream/preview
git push origin preview
```

---

## 📄 License

[GNU Affero General Public License v3.0](https://github.com/makeplane/plane/blob/master/LICENSE.txt)
