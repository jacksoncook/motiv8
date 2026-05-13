# Apple Sign In Integration

## Prerequisites (Apple Developer Portal)

Before any code runs in production, you need:

1. **App ID** — enable "Sign In with Apple" capability for your App ID
2. **Services ID** — create a Services ID (e.g., `io.motiv8me.web`) and configure:
   - Description: Motiv8me Web
   - Return URL: `https://api.motiv8me.io/auth/apple/callback`
3. **Key** — create a new key with "Sign In with Apple" enabled, download the `.p8` file
4. **Note your:**
   - `Team ID` (top-right of Apple Developer portal)
   - `Key ID` (shown after creating the key)
   - `Client ID` = your Services ID (e.g., `io.motiv8me.web`)
   - `Private Key` = contents of the downloaded `.p8` file

---

## Environment Variables to Add

```bash
# motiv8-be/.env (and production secrets)
APPLE_CLIENT_ID=io.motiv8me.web         # Services ID from Apple Developer
APPLE_TEAM_ID=XXXXXXXXXX                # 10-char Team ID
APPLE_KEY_ID=XXXXXXXXXX                 # 10-char Key ID
APPLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
APPLE_REDIRECT_URI=https://api.motiv8me.io/auth/apple/callback
```

> In dev, set `APPLE_REDIRECT_URI=http://localhost:8000/auth/apple/callback` and add
> `http://localhost:8000/auth/apple/callback` to the Services ID return URLs in Apple Developer.

---

## Apple vs Google: Key Differences

| | Google | Apple |
|---|---|---|
| Callback method | `GET` | **`POST`** (`response_mode=form_post`) |
| User info source | `userinfo` in token | Claims in `id_token` (JWT) |
| Email | Always present | Only on first login (may be relay address) |
| User name | Always in userinfo | **Only on first login** in `user` form field |
| Client secret | Static string | **Short-lived JWT you sign** with your `.p8` key |
| Token verification | Authlib handles | Must fetch Apple's JWKS and verify RS256 manually |
| CSRF state | Session-based | Same, but state comes back in POST body |

---

## New Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/auth/apple/login` | Build Apple auth URL, store state in session, redirect |
| `POST` | `/auth/apple/callback` | Receive `code`+`user`+`state` from Apple, exchange for tokens, issue JWT |
| `POST` | `/auth/apple/notifications` | Server-to-server notifications (consent revoked, account deleted) |

---

## Files to Change

### Backend

| File | Change |
|------|--------|
| `models.py` | Add `apple_id` column to `User` |
| `auth.py` | Add Apple config vars, `generate_apple_client_secret()`, `get_apple_public_keys()`, `verify_apple_token()`, update `get_or_create_user()` to accept `apple_id` and optional `email` |
| `main.py` | Add `Form` import, Apple endpoint imports, 3 new endpoints |
| `migrate.py` | Add `apple_id` VARCHAR column migration (SQLite + PostgreSQL) |

### Frontend

| File | Change |
|------|--------|
| `AuthContext.tsx` | Add `loginWithApple: () => void` to interface + implementation |
| `Login.tsx` | Add "Continue with Apple" button |
| `Login.css` | Add `.apple-login-button` styles (black, per Apple HIG) |

---

## Apple Client Secret Generation

Apple's client secret is a JWT *you* sign with your `.p8` key — not a static string:

```
Header: { "alg": "ES256", "kid": "<APPLE_KEY_ID>" }
Payload: {
  "iss": "<APPLE_TEAM_ID>",
  "iat": <now>,
  "exp": <now + 3600>,          # max 6 months; 1h is fine per auth flow
  "aud": "https://appleid.apple.com",
  "sub": "<APPLE_CLIENT_ID>"
}
```

Signed with ES256 using the `.p8` private key.

---

## Token Exchange

After receiving `code` in the callback, POST to Apple:

```
POST https://appleid.apple.com/auth/token
Content-Type: application/x-www-form-urlencoded

client_id=<APPLE_CLIENT_ID>
&client_secret=<generated_jwt>
&code=<authorization_code>
&grant_type=authorization_code
&redirect_uri=<APPLE_REDIRECT_URI>
```

Response includes `id_token` (RS256 JWT). Verify it against Apple's JWKS:
`https://appleid.apple.com/auth/keys`

Claims in `id_token`:
- `sub` — stable Apple user ID (store as `apple_id`)
- `email` — present on first login only
- `email_verified` — boolean

---

## Server-to-Server Notifications

Apple POSTs to your notification URL with `payload=<jwt>`. The JWT is signed
by Apple (verify via same JWKS). Payload `events` field is a JSON string:

```json
{ "type": "account-delete", "sub": "<apple_user_id>", ... }
```

| Event type | Our action |
|------------|-----------|
| `email-disabled` | Log only |
| `email-enabled` | Log only |
| `consent-revoked` | Clear `apple_id` from user (forces re-auth) |
| `account-delete` | Delete user record |

> Always return HTTP 200 to prevent Apple from retrying.

---

## Register the Notification URL

In Apple Developer portal → Services ID → Sign In with Apple → Configure:
set the **Server to Server Notification Endpoint** to:

```
https://api.motiv8me.io/auth/apple/notifications
```
