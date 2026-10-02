# Deployment

The app is deployed with [Kamal](https://kamal-deploy.org) to a DigitalOcean droplet and served at
**https://houses.kmaster.app**.

## Overview

| | |
|---|---|
| Server | DigitalOcean droplet `209.38.93.10` (1 vCPU, 2 GB RAM, 2 GB swap; SSH as `root`) |
| URL | `https://houses.kmaster.app` |
| Kamal service | `house-price-estimator` |
| Image | `ghcr.io/rpazevedo/house-price-estimator` (private GHCR package) |
| Container port | `8501` (Streamlit) |
| Healthcheck | `GET /_stcore/health` → `ok` |
| Database | `property_valuation`, user `property_valuation` (staging: `property_valuation_staging`, user `property_valuation_staging`), on the DigitalOcean Managed PostgreSQL cluster |

### A shared server

The droplet hosts several independently deployed apps. Each has its own repository, its own
`config/deploy.yml` and its own Kamal service name, and each is deployed on its own schedule.

What they share is **kamal-proxy**, which Kamal installs once per server and which owns ports 80
and 443. Every app registers a host name with it. The proxy routes each request to the right
container by its `Host` header, and obtains a separate Let's Encrypt certificate for each host.

```
                               ┌─────────────── droplet 209.38.93.10 ──────────────┐
https://houses.kmaster.app ────┤                    ┌─► house-price-estimator (:8501)
                               │  kamal-proxy ──────┤                               │
https://<other host> ──────────┤  (:80 / :443)      └─► other apps' containers      │
                               └───────────────────────────────────────────────────┘
```

This has four consequences:

- **Each app needs its own host.** kamal-proxy refuses to let two services claim the same one,
  which is why this app lives on the `houses.` subdomain.
- **Deploys are isolated.** `kamal deploy` here only replaces this app's container. Other apps'
  containers and configuration are not touched.
- **The proxy is not this app's to remove.** See [Removing the app](#removing-the-app).
- **Memory is shared.** The apps share 2 GB of RAM and 2 GB of swap, and no container has a
  memory limit. During a deploy the old and new containers run side by side until the new one is
  healthy. Keep an eye on `free -m` (see [Operations](#operations)) as apps are added.

## Prerequisites

- Docker running locally (Docker Desktop or OrbStack). Kamal builds the image on your machine.
- Kamal 2.11+ installed as a global gem: `gem install kamal`, then check with `kamal version`.
  Kamal is not added to this project's dependencies. It's a Ruby tool, and this is a Python
  project.
- SSH access to the droplet as `root` with your key: `ssh root@209.38.93.10`.
- A GitHub personal access token for GHCR (see [One-time setup: GHCR](#one-time-setup-ghcr)),
  in your environment before running Kamal. Either export it:

  ```sh
  export KAMAL_REGISTRY_PASSWORD=ghp_your_token_here
  ```

  or copy `.env.example` to `.env` (gitignored), fill it in, and load it into the shell:

  ```sh
  set -a; source .env; set +a
  ```

  `.kamal/secrets-common` reads the token from the environment; never commit it. Kamal also logs the
  droplet in to ghcr.io with it, so the token is stored in `root`'s `~/.docker/config.json` on the
  server. Every deploy logs in again, so after rotating the token just load the new one and deploy.
- The database users' passwords (see [One-time setup: database](#one-time-setup-database)), in
  `.env` or exported as `PROPERTY_VALUATION_DB_PASSWORD` (production) and
  `PROPERTY_VALUATION_STAGING_DB_PASSWORD` (staging). `.kamal/secrets` and `.kamal/secrets.staging`
  pass them to the containers as `PGPASSWORD`. Each deploy only needs its own environment's.

## Files

| File | Purpose |
|---|---|
| `Dockerfile` | Production image: `python:3.13-slim` + `uv sync --frozen --no-dev`. Applies database migrations (`python -m db`), then runs Streamlit on `0.0.0.0:8501` as a non-root user. |
| `.dockerignore` | Keeps tests, scripts, docs, `.venv`, `.git`, CI output and local secrets out of the build context. |
| `config/deploy.yml` | Kamal config: server, proxy host, app port, healthcheck, registry, builder arch, database. |
| `config/deploy.staging.yml` | Staging overrides (`kamal deploy -d staging`): its own service, image, host, database and database user. |
| `.kamal/secrets-common` | Secrets passed to Kamal for every destination. Only `KAMAL_REGISTRY_PASSWORD` (the GHCR token), read from your environment. |
| `.kamal/secrets` | Production-only secrets (read without `-d`): `PGPASSWORD` from `PROPERTY_VALUATION_DB_PASSWORD`. |
| `.kamal/secrets.staging` | Staging-only secrets (read with `-d staging`): `PGPASSWORD` from `PROPERTY_VALUATION_STAGING_DB_PASSWORD`. |
| `bin/setup-database` | One-time creation of an environment's database and user on the cluster (see [database](#one-time-setup-database)). |
| `.env.example` | Template for a local, gitignored `.env` holding the token and database passwords. |

Key settings in `config/deploy.yml`:

- **`proxy.host: houses.kmaster.app`, `proxy.ssl: true`**: kamal-proxy routes this host to the
  app and issues a Let's Encrypt certificate for it.
- **`proxy.app_port: 8501`**: Streamlit's port. The default is 80, which Streamlit doesn't listen
  on.
- **`proxy.healthcheck.path: /_stcore/health`**: Streamlit's built-in health endpoint.
  kamal-proxy only switches traffic to a new container after this returns 200.
- **`registry.server: ghcr.io`**: images are pushed to a private package on GitHub Container
  Registry. Kamal runs `docker login ghcr.io` on your machine (to push) and on the server (to
  pull) with `username: rpazevedo` and `KAMAL_REGISTRY_PASSWORD`. The Dockerfile's
  `org.opencontainers.image.source` label links the package to the GitHub repo.
- **`builder.arch: amd64`**: the droplet is x86_64, so the image is built for amd64 even on
  Apple Silicon.
- **`env.clear.PG*` and `env.secret: PGPASSWORD`**: the standard libpq variables, which psycopg
  reads directly. `PGSSLMODE: require` because DigitalOcean only accepts TLS connections.

Key lines in the `Dockerfile`:

- **`ghcr.io/astral-sh/uv:0.12.17@sha256:…`**: uv is pinned by version and digest, so rebuilding
  the same commit always uses the same uv. To upgrade, change the tag and take the new digest
  from `docker buildx imagetools inspect ghcr.io/astral-sh/uv:<version>`.

- **`uv sync --frozen`**: installs exactly the versions in `uv.lock`, and fails instead of
  re-resolving if the lock is out of date. This matters more than usual here: the saved models in
  `estimator/ml/saved_models/` only load reliably in the scikit-learn version that pickled them,
  which `pyproject.toml` pins.
- **`xgboost-cpu` on Linux** (`pyproject.toml`): the regular xgboost wheel for Linux bundles CUDA
  and depends on NVIDIA's NCCL, a 250 MB wheel used only for GPU training. The droplet has no GPU,
  so Linux installs, both the image and the CI containers, get the 6 MB CPU-only build. macOS
  keeps the regular package, which has no GPU extras.
- **uv cache mount, no `chown -R`**: the cache mount keeps uv's download cache out of the install
  layer, while still reusing it on the next build. A recursive `chown` would copy every file into
  a new layer. Either one adds about 1 GB. The files stay owned by root, which the non-root
  `streamlit` user can read, and the app never writes to `/app`. The image comes to about 820 MB,
  mostly pyarrow, scipy and pandas.
- **`GIT_SHA` / `GIT_COMMITTED_AT` last**: they change on every commit, so declaring them any
  earlier would rebuild every layer below them.
- **`COPY estimator/ data/`**: the code finds the models and the training CSV relative to its own
  files, so the image keeps the repository's layout.

## One-time setup: GHCR

There's nothing to set up on GHCR itself. The package `ghcr.io/rpazevedo/house-price-estimator`
is created on the first push. You only need a token:

1. On GitHub, go to **Settings → Developer settings → Personal access tokens → Tokens (classic)**.
2. Generate a token with the **`write:packages`** scope (it includes `read:packages`). Use a
   classic token: GHCR doesn't accept fine-grained tokens. Set an expiry.
3. Put it in your environment as `KAMAL_REGISTRY_PASSWORD` (see [Prerequisites](#prerequisites)).

After the first deploy:

- **Visibility:** packages under a personal account start out private. Confirm under your profile
  → **Packages → house-price-estimator → Package settings**.
- **Storage:** private packages use your account's Packages storage allowance, and every deploy
  adds a tag. Delete old versions from the package settings now and then.

## One-time setup: DNS

`kmaster.app` is hosted on DigitalOcean DNS (`ns1/ns2/ns3.digitalocean.com`).

1. In the DigitalOcean control panel, go to **Networking → Domains → kmaster.app**.
2. Add an **A record**: hostname `houses` (and `houses-staging` for staging), value `209.38.93.10`.
3. Check the authoritative nameserver answers:

   ```sh
   dig @ns1.digitalocean.com +short houses.kmaster.app   # → 209.38.93.10
   ```

No propagation wait is needed for a new record: Let's Encrypt queries the authoritative
nameservers directly, so `kamal setup` can obtain the certificate as soon as the `dig` above
returns the IP. If you looked the name up *before* creating the record, your local resolver may
cache the "does not exist" answer for up to 30 minutes. Wait it out or flush the macOS DNS cache:

```sh
sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder
```

## One-time setup: database

Each environment keeps its accounts in its own database on the DigitalOcean Managed PostgreSQL
cluster (`db-postgresql-syd1-66096-do-user-7536526-0.h.db.ondigitalocean.com:25060`) and connects
as its own user, not as `doadmin`, so neither can touch the other's data or the other databases on
the cluster:

| Environment | Database and user | Password env var | Jenkins credential |
|---|---|---|---|
| Production | `property_valuation` | `PROPERTY_VALUATION_DB_PASSWORD` | `property-valuation-db-password` |
| Staging | `property_valuation_staging` | `PROPERTY_VALUATION_STAGING_DB_PASSWORD` | `property-valuation-staging-db-password` |

Tables come from [migrations](../README.md#schema-changes), which each container applies on every
start, so the only one-time step is creating the database and the user:

```sh
doctl auth init              # once, with a DigitalOcean API token (read + write on databases)
bin/setup-database           # production
bin/setup-database staging   # staging
```

[`bin/setup-database`](../bin/setup-database) reads the host, database and user from the Kamal
config, finds the cluster with `doctl`, and:

1. creates the user and the database, unless they exist;
2. as `doadmin`, grants the user `CREATE` on the `public` schema and `CONNECT` on the database, and
   revokes `CONNECT` from everyone else. psql runs on the droplet (over SSH, in a `postgres`
   container) because the droplet is already a trusted source of the cluster;
3. warns if the cluster's PostgreSQL major version differs from the `postgres` image the
   Jenkinsfile tests against;
4. prints the user's password: save it in `.env` and as the Jenkins credential (Secret text, in the
   pipeline's own store).

It's safe to re-run, e.g. to see a password again.

### Managing accounts

There is no admin screen. To list or remove accounts, connect from the droplet with the `doadmin`
connection string from the cluster's **Overview → Connection details**:

```sh
ssh root@209.38.93.10
docker run --rm -it postgres:17 psql 'postgresql://doadmin:...@db-postgresql-syd1-66096-do-user-7536526-0.h.db.ondigitalocean.com:25060/property_valuation?sslmode=require'
```

```sql
SELECT username, created_at FROM users ORDER BY created_at;
DELETE FROM users WHERE username = 'someone';
```

Deleting an account doesn't end a session that's already logged in; it ends when that browser tab
is closed or refreshed.

## First deploy

```sh
# 1. Check the image builds and serves locally, against your local PostgreSQL
docker build --platform linux/amd64 -t house-price-estimator .
docker run --rm -p 8501:8501 -e PGHOST=host.docker.internal -e PGUSER=$USER house-price-estimator
curl localhost:8501/_stcore/health          # → ok  (then Ctrl-C the container)

# 2. Check the Kamal config parses
kamal config

# 3. Check DNS and set up the database (see above)
dig @ns1.digitalocean.com +short houses.kmaster.app
bin/setup-database

# 4. Deploy
kamal setup
```

`kamal setup` runs these steps in order:

1. Checks Docker is installed on the server (it already is).
2. Logs in to GHCR on your machine, builds the image, and pushes it.
3. Logs the server in to GHCR and pulls the image.
4. Ensures kamal-proxy is running on the server. It already is, so this leaves it alone.
5. Boots the app container and registers `houses.kmaster.app` with the proxy.
6. Prunes this app's old containers and images.

## Subsequent deploys

Commit your changes, then:

```sh
kamal deploy
```

Kamal tags the image with the current git commit SHA. Uncommitted changes are *not* included, so
commit first.

## Staging

Staging runs on the same droplet at **https://houses-staging.kmaster.app**, as its own Kamal
service (`property_valuation_staging`) and image. `config/deploy.staging.yml` is merged over
`config/deploy.yml`. It isn't just another destination of the production service because Kamal
prunes containers and images by service label only, so staging deploys would delete production's
rollback containers.

```sh
kamal deploy -d staging
```

Every other command takes `-d staging` too, e.g. `kamal logs -d staging`. The first deploy needs
the `houses-staging` A record (see [One-time setup: DNS](#one-time-setup-dns)) and its database
(`bin/setup-database staging`, see [database](#one-time-setup-database)).

On `main`, Jenkins builds the image once and pushes it to GHCR under both services' images,
tagged with the commit SHA. The two differ only in their `service` label, which Kamal checks on
pull. It then deploys to staging with `--skip-push`, smoke-tests `/_stcore/health`, and deploys the
same image to production the same way. A failing staging deploy or smoke test stops the pipeline
before production. Each deploy stage gets only its own environment's database password.

The `Tests` stage starts a throwaway `postgres:17` container, waits up to 2 minutes for it to
accept connections (printing its logs and failing if it doesn't), and runs `pytest` in the uv image
linked to it (`PGHOST=postgres`).

## Operations

```sh
kamal logs                     # tail app logs (alias for `kamal app logs -f`)
kamal app details              # container status
kamal shell                    # bash inside the running container
kamal app images               # list app images on the server (tags are the git SHAs)
kamal app containers           # list app containers, including stopped previous versions
kamal rollback <version>       # switch back to a previous version (its container must still exist)
kamal app boot                 # restart the current version
ssh root@209.38.93.10 free -m  # memory headroom on the shared server
ssh root@209.38.93.10 docker stats --no-stream   # memory per container, all apps
```

### Removing the app

Use **`kamal app remove`**. It removes only this app's containers, images and app directory.

Don't run top-level `kamal remove` or `kamal proxy remove`. Those act on the whole server: they
also try to remove kamal-proxy and any accessories, which the other apps on the droplet depend on.
kamal-proxy refuses to be removed while other apps are still registered, so `kamal remove` fails
partway, after this app is already gone.

## Verification checklist

After each deploy:

- [ ] `curl -I https://houses.kmaster.app` returns `200` with a valid certificate.
- [ ] Open https://houses.kmaster.app: the **Log in** / **Sign up** tabs show. Log in (or sign
      up), load `data/sample_property.csv` from the sidebar and press **Estimate price**. All four
      cards should show a price. This proves the app reaches the database, the models load and the
      Streamlit websocket works through kamal-proxy.
- [ ] The other hosts on the droplet still respond.
- [ ] `kamal app details` shows the container running.

## Troubleshooting

- **Certificate isn't issued / TLS errors right after `kamal setup`:** DNS wasn't live when Let's
  Encrypt checked. Confirm with `dig @ns1.digitalocean.com houses.kmaster.app`, then run
  `kamal deploy` again. kamal-proxy retries issuance on new requests.
- **Deploy fails with "target failed to become healthy":** the container didn't answer
  `/_stcore/health` on port 8501 in time. Check `kamal logs`. A `psycopg.OperationalError` means
  `python -m db` couldn't reach the database, so Streamlit never started (see the next item). Any
  other traceback from `db.py` is a failing migration: it was rolled back, so fix it and deploy
  again. Otherwise make sure Streamlit binds to `0.0.0.0:8501` (set in the Dockerfile `CMD`).
- **`password authentication failed for user "property_valuation"`** (or
  `"property_valuation_staging"`): the password env var or its Jenkins credential is missing or
  wrong. **`connection timeout`:** the droplet isn't in the cluster's Trusted sources.
  **`permission denied for schema public`:** the grants weren't applied; re-run
  `bin/setup-database` (or `bin/setup-database staging`).
- **`Secret 'PGPASSWORD' not found`:** the environment's own secrets file (`.kamal/secrets` or
  `.kamal/secrets.staging`) is missing its `PGPASSWORD` line.
- **Page loads but hangs on "Please wait…" / keeps reconnecting:** the websocket
  (`/_stcore/stream`) is failing. kamal-proxy supports websockets by default. Check the browser
  console and `kamal logs` for XSRF/CORS errors.
- **Every estimate card fails:** the saved models didn't load, usually because scikit-learn in the
  image differs from the version that pickled them. `uv sync --frozen` should prevent this; check
  `kamal logs` for the unpickling error.
- **"host is used by another service":** another Kamal service already claims the host. Each app
  on the droplet needs its own `proxy.host`.
- **`unauthorized` / `denied` when pushing or pulling from ghcr.io:** `KAMAL_REGISTRY_PASSWORD`
  is missing, expired, or lacks `write:packages`. Check with `kamal registry login`.
- **A container was killed or the server is sluggish:** the droplet is short of memory. Check
  `free -m` and `docker stats --no-stream` on the server.
- **Build is slow on Apple Silicon:** building for `amd64` runs under emulation. That's expected.
