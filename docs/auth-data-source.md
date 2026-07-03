# 🔑 Authenticated Idleon Data Source

This document defines the authenticated data source direction for HA Idleon.

The long-term user setup should match how users already access Legends of
Idleon: sign in with an Idleon-supported identity provider and let Home
Assistant fetch the read-only cloud save data directly.

Authenticated login is now the primary setup path. The UI asks users to choose
`google`, `apple`, `email`, `steam`, or `local_file` directly. Authenticated
entries are stored internally as `idleon_cloud` with an auth provider.
`remote_url` remains available internally for development and tests, but it is
not presented as a primary user setup option.

## 🎯 Goal

Use the first setup choice:

```txt
google
apple
email
steam
local_file
```

The source should:

- Authenticate using an Idleon-supported login method.
- Fetch the user's raw Idleon cloud save data.
- Feed the existing parser and coordinator models.
- Avoid browser/session scraping.
- Avoid write actions.
- Avoid requiring manual JSON downloads.

## 🔐 Supported Login Direction

Provider order:

1. Email and password
2. Google device flow
3. Steam OpenID handoff
4. Apple sign-in

Email/password, Google device flow, and Steam OpenID handoff are implemented.
Email/password is a direct Firebase auth exchange. Google device flow works
without embedding a browser in the config flow: Home Assistant shows a Google
user code, then exchanges the completed Google authorization for Firebase
credentials.

Steam is implemented with a manual OpenID handoff: Home Assistant shows a Steam
sign-in link, the user signs in through Steam, then copies the final returned
browser URL back into the config flow. Apple is still more awkward in a Home
Assistant server context because it requires provider-specific browser handoff
pages.

## ☁️ Data Shape

IdleonToolbox currently signs into the `idlemmo` Firebase project and reads:

- Realtime Database `_uid/{uid}` for character names.
- Firestore `_data/{uid}` for cloud save data.
- Realtime Database `_comp/{uid}` for companion data.
- Realtime Database `_usgu/{uid}/g` and `_guild/{guild_id}` for guild data.
- Firestore `_vars/_vars` for server variables.
- Tournament documents for tournament-specific data.

HA Idleon should start with the minimum required account data:

- `_uid/{uid}`
- `_data/{uid}`

Additional companion, guild, server variable, or tournament reads can be added
later when the parser exposes entities or attributes that need them.

## 🏠 Home Assistant Design

The config flow offers:

```txt
data_source_type:
  - google
  - apple
  - email
  - steam
  - local_file
```

Cloud login selections are normalized to stored `idleon_cloud` entries with an
`auth_provider` value.

Expected fields by provider:

- `email`: email address and password. Implemented.
- `google`: device-code flow state and verification URL. Implemented.
- `steam`: Steam redirect URL pasted by the user after signing in. Implemented.
- `apple`: Apple handoff state and verification URL.

Stored config must be explicit:

- Provider type.
- User ID once authenticated.
- Refresh token or equivalent long-lived auth material if required.
- Scan interval.

Passwords should not be stored after a successful token exchange unless the
chosen API cannot refresh without them.

## 🔄 Coordinator Behavior

For `idleon_cloud`, the coordinator should:

1. Refresh or validate the auth token if needed.
2. Fetch the current cloud save document.
3. Fetch character names.
4. Build a raw payload shaped like the existing wrapped export where practical:

   ```json
   {
     "saveData": {},
     "charNameData": []
   }
   ```

5. Parse once through the existing parser.
6. Mark entities unavailable on failed auth or fetch without crashing HA.

Auth failures should be distinguishable from schema and network failures in
diagnostics and config flow errors.

## 🧪 Test Strategy

Do not hit Firebase or identity providers in tests.

Use mocked responses for:

- Email/password success.
- Email/password invalid credentials.
- Token refresh success.
- Token refresh failure.
- Cloud save fetch success.
- Cloud save missing account data.
- Character-name fetch failure.

Parser tests should continue to use local fixtures.

## ⚖️ Licensing Boundary

IdleonToolbox is useful prior art for understanding the cloud data shape and
login flow, but HA Idleon must not copy GPL-licensed implementation code into
this MIT repository.

Implementation should be written independently against provider/Firebase HTTP
APIs and covered with tests.

## 🚫 Non-Goals

Do not implement:

- Browser cookie scraping.
- Browser local/session storage scraping.
- Manual session token paste fields.
- Write actions to Idleon/Firebase data.
- Cloud profile uploads.
- Leaderboards or public profile publishing.

## 🚧 Migration Plan

1. Add `idleon_cloud` constants, model fields, config-flow shell, and docs.
   Done.
2. Implement email/password authentication and cloud save fetch behind mocks.
   Done.
3. Add diagnostics redaction for auth fields. Done.
4. Add repair/config-flow errors for auth failures. Config-flow errors are
   implemented; repairs are still pending.
5. Add Google device flow. Done.
6. Add Steam OpenID handoff. Done.
7. Decide whether Apple is viable inside HA without external helper services.
8. Move `local_file` and `remote_url` under advanced/development wording.
