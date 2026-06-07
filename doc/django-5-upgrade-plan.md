# Django 5.x upgrade plan

This branch tracks the work to lift the project from `Django<4` (currently
resolves to 3.2.x) to Django 5.2 LTS.

## Why now

- Django 3.2 reached end of extended support 2024-04-01 — no more security
  patches.
- Several deps in `pyproject.toml` carry workaround pins added to keep
  Django 3.2 alive against modern Python:
  - `django-import-export<=3.3.9` (search_help_text + strftime regression
    on Django 3.2 + py3.12)
  - `python-memcached==1.59` (Django 3.x memcached backend AttributeError
    on py3.12)
  - `legacy-cgi; python_version >= '3.13'` (Django 3.2 imports the cgi
    module which was removed from py3.13 stdlib)
  - `django-admin-lazy-load-alexforks` (private fork to work around
    upstream incompatibility — verify if still needed on Django 5)
- The 2026-05 deploy already hit one Django 3.2 + RabbitMQ 4.x mismatch
  (`transient_nonexcl_queues` deprecation, fixed separately by pinning
  rabbitmq:3.13). Continuing to defer the Django upgrade keeps stacking
  these compat workarounds.

## Target

Django 5.2 LTS (released April 2025, supported through April 2028).

## Scope of the upgrade

### Code changes (in this repo)

| Area | Likely change | Risk |
|---|---|---|
| `pyproject.toml` Django pin | `Django<4` → `Django~=5.2.0` | low (mechanical) |
| `pyproject.toml` Python pin | `>=3.8` → `>=3.10` (Django 5 dropped py3.8/3.9) | low |
| `shadowsocks_manager/shadowsocks_manager/settings.py` | Drop `USE_L10N` (removed in 5.0); review `USE_TZ`, `TIME_ZONE`; replace any `pytz` usage with `zoneinfo` | medium |
| `shadowsocks_manager/*/urls.py` | `url()` deprecated since 4.0, removed; use `re_path()` / `path()` | low (mechanical, check actual usage) |
| `models.py` across apps | `Meta.default_auto_field` may need explicit BigAutoField; check `null=True` on TextField/CharField (warning in 4.x) | medium |
| `admin.py` across apps | django-admin-easy + django-admin-lazy-load-alexforks compatibility | medium-high (the forks may be tied to Django 3.x admin internals) |
| `forms.py`, views | `ugettext*` → `gettext*` (removed in 4.0); class-based view changes | low |
| `signals.py` | dispatch_uid pattern unchanged but check for any deprecated signal connect kwargs | low |
| Test suite | tests reference `assertContains`, `Client.force_login`, etc. — most stay; verify `assertRedirects` URL formatting | low |
| `requirements*.txt`, `tox.ini` envlist | Django version envs (`py310-django52`, etc.); drop py38/py39 | low (mechanical) |

### Transitive dep upgrades (need pinning re-evaluation)

| Dep | Current pin | Target |
|---|---|---|
| `django-import-export` | `<=3.3.9` (workaround) | latest (≥4.x supports Django 5; the AccountAdmin.search_help_text bug we worked around is fixed) |
| `django-celery-beat` | unpinned | latest (already supports Django 5) |
| `django-celery-results` | unpinned | latest |
| `django-admin-easy` | unpinned | needs verification — last release Sept 2023, may not support Django 5 cleanly; could be a blocker |
| `django-admin-lazy-load-alexforks` | unpinned | likely needs re-fork or replacement; the upstream `django-admin-lazy-load` is dormant. Possibly drop the lazy-load admin enhancement entirely if the new admin's async views provide equivalent UX. |
| `django-allowedsites-dynamic` | unpinned | check compat |
| `django-cache-lock` | unpinned | check compat |
| `django-enumfield` | unpinned | check compat |
| `django-filter` | unpinned | latest supports 5 |
| `djangorestframework` | unpinned | ≥3.15 supports Django 5 |
| `python-memcached==1.59` | workaround pin | drop pin or replace with `pymemcache` (Django 4.1+ has `django.core.cache.backends.memcached.PyMemcacheCache`) |
| `legacy-cgi; python_version>=3.13` | py3.13 workaround | drop (Django 5 doesn't import cgi) |

### Other repos that may need follow-up

- `alexzhangs/aws-cfn-vpn`: the EC2 userdata pulls SSM_VERSION from PyPI.
  Once Django-5 image is published, deploys will pick it up. No change
  needed unless we want to pin a known-good SSMVersion.
- `alexzhangs/django-admin-lazy-load-alexforks`: re-fork or merge if the
  base project moves; OR retire the dependency.

## Phased rollout

### Phase 1 — Mechanical lift (this branch)

- Bump Django to 5.2; update Python floor to 3.10
- Remove `USE_L10N`
- Fix the simplest URL/template/forms deprecations
- Drop the py3.13 cgi workaround (no longer needed)
- Run `tox -e py310,py311,py312,py313` and triage failures

### Phase 2 — Dep cascade

- Triage each transitive dep; bump or replace as needed
- `django-admin-easy` + `django-admin-lazy-load-alexforks` likely the
  hardest blockers — may need fork updates
- Bump `django-import-export` to latest, drop the `<=3.3.9` workaround
- Replace `python-memcached` with `pymemcache`

### Phase 3 — Async views (optional)

- Convert long-poll endpoints (port heartbeat, change-IP REST endpoints)
  to async views — Django 4.1+ supports
- Async ORM (`Model.aobjects`) where it pays off
- Defer until phase 1+2 stabilize

### Phase 4 — Image rebuild + deploy

- New Docker image with Django 5.2; published as next PyPI release
- The `alexzhangs/shadowsocks-manager:slim-latest` tag picks it up via the
  existing CI workflow
- Live cluster upgrades by simply restarting the SSM container (pulls new
  image)

## Definition of done

- [ ] `tox -e py310,py311,py312,py313` green on this branch
- [ ] `docker build -f docker/slim/Dockerfile .` succeeds; container boots
- [ ] All Django admin pages render
- [ ] Save through admin works without 500/403 (including modifying Node,
      Account, Record, NodeAccount)
- [ ] Celery beat + worker continue running tasks (`port_heartbeat`,
      `statistic`, `node_change_ips_softly`)
- [ ] Smoke test: a new SS user account can be created + bound to nodes,
      DNS records update via dns-lexicon
- [ ] PR opened against `develop` with the diff size + breaking-change
      notes
