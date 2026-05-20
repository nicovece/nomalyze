# Nomalyze — Django Backend

> Recipe management and analytics web app. **Django 5.2 + Django REST Framework** with JWT auth, PostgreSQL, deployed on Render with Cloudflare R2 image hosting. Serves both a Django template site and a [Vue 3 SPA](https://github.com/nicovece/nomalyze-frontend) against the same data. Lighthouse 91 (Django) / 97 (Vue).

[![CI](https://github.com/nicovece/cf-recipe-app/actions/workflows/ci.yml/badge.svg)](https://github.com/nicovece/cf-recipe-app/actions/workflows/ci.yml)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Django site](https://img.shields.io/badge/Django_site-live-success)
![Vue SPA](https://img.shields.io/badge/Vue_SPA-live-success)

**Live demos:** [🍴 Django template site](https://nomalyze.com) · [⚡ Vue 3 SPA](https://nomalyze.netlify.app) — both backed by this repo, same demo account: `demo` / `example123` (Render free tier — first request after idle takes ~30 sec to wake)

---

## About this project

Nomalyze started as a Django monolith built during a CareerFoundry full-stack course. It's been modernized in three phases:

1. **Foundation** — Django 5.2 site with PostgreSQL, server-rendered templates, custom auto-difficulty logic, and wildcard search (`*` / `?` → regex).
2. **REST API + SPA cutover** — Added a Django REST Framework API (JWT auth via `djangorestframework-simplejwt`) alongside the original template views, then built a [Vue 3 SPA frontend](https://github.com/nicovece/nomalyze-frontend) consuming the same backend. Sessions still drive the template site; JWT serves the SPA. One `Recipe` model, two presentation layers, no sync code.
3. **Image pipeline overhaul** — Moved recipe images off Render's ephemeral disk to Cloudflare R2 (10 GB free tier, zero egress), pre-generated three responsive variants per image (400 / 800 / 1200 widths) via `django-imagekit`, and switched the variant format from JPEG q80 to **WebP q72** — ~30% byte reduction at the same perceived fidelity. Lighthouse: 40 → 91 (Django) and → 97 (Vue).

This repo is the backend half. It serves both the original Django template site and the JSON API the SPA consumes.

---

## REST API

Six endpoints, all under `/api/`. Recipe endpoints require a valid JWT (`Authorization: Bearer <access>`); auth endpoints are public.

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| `POST` | `/api/auth/token/` | — | Obtain access + refresh token pair |
| `POST` | `/api/auth/token/refresh/` | — | Exchange refresh token for new access token |
| `GET` | `/api/recipes/` | JWT | Paginated recipe list (page size 20) |
| `GET` | `/api/recipes/<id>/` | JWT | Recipe detail |
| `GET` | `/api/recipes/search/` | JWT | Filtered search (name, ingredients, cooking time, difficulty) |
| `GET` | `/api/recipes/search/stats/` | JWT | Same filters as `/search/`, returns aggregated chart data |

### Auth flow

```bash
# 1. Obtain tokens
curl -X POST https://nomalyze.com/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "password": "example123"}'
# => { "access": "eyJ…", "refresh": "eyJ…" }

# 2. Call a protected endpoint
curl https://nomalyze.com/api/recipes/ \
  -H "Authorization: Bearer eyJ…"
```

Access tokens expire after 30 minutes; refresh tokens after 7 days. The SPA's Axios interceptor handles the refresh on 401 transparently — see [`src/api/client.ts`](https://github.com/nicovece/nomalyze-frontend/blob/main/src/api/client.ts) in the frontend repo.

### Search query parameters

`/api/recipes/search/` accepts any combination of:

- `name` — substring match, or wildcard pattern with `*` / `?` (e.g. `*berry*`, `pa?ta`)
- `ingredients` — comma-separated list; **AND** logic (a recipe must contain all listed ingredients); each item also supports wildcards
- `cooking_time_max` — integer minutes, upper bound
- `difficulty` — one of `Easy` / `Medium` / `Intermediate` / `Hard`
- `show_all=true` — bypass filters, return everything

### Response shape — `recipe_image`

The `recipe_image` field is a `SerializerMethodField` that returns four URLs (one original + three resized variants) so the client can emit `<img srcset>` without further negotiation:

```json
{
  "id": 12,
  "name": "Lentil dal",
  "ingredients_list": ["red lentils", "onion", "garam masala"],
  "cooking_time": 35,
  "difficulty": "Hard",
  "recipe_image": {
    "original": "https://pub-….r2.dev/images/recipes/dal.webp",
    "small":    "https://pub-….r2.dev/CACHE/images/recipes/dal/…-400.webp",
    "medium":   "https://pub-….r2.dev/CACHE/images/recipes/dal/…-800.webp",
    "large":    "https://pub-….r2.dev/CACHE/images/recipes/dal/…-1200.webp"
  }
}
```

---

## Architecture Decisions

### API + SPA — coexistence over rewrite

The Django site already has working sessions, server-rendered templates, and admin tooling. Throwing all of that away for a SPA rewrite would be expensive and offer no user-facing benefit; the goal of the SPA is faster perceived performance for the public read path, not a full re-platform.

The DRF API at `/api/recipes/…` and `/api/auth/token/…` lives alongside the existing template views. The SPA uses JWT (cross-origin friendly, sent via `Authorization` header — no CSRF dance); the template site continues to use Django sessions. Both auth systems read and write the same `Recipe` model — no data duplication, no sync layer. New features that benefit from interactivity (live filtering, Chart.js visualisations) ship to the Vue SPA; admin/CRUD-heavy flows stay in Django's admin.

### API design notes

- **Stats endpoint reuses search filtering by composition, not inheritance.** `RecipeSearchStatsAPIView` instantiates `RecipeSearchAPIView` and delegates to its `get_queryset()` rather than subclassing it. The stats view returns aggregated data (three differently-shaped lists for three chart types), not a paginated list of recipes, so inheriting `ListAPIView` would force unhelpful machinery. Composition keeps the filter logic in one place without coupling the response shapes.
- **Wildcard search is translated to regex at the query layer.** `*` becomes `.*` and `?` becomes `.`; the query then uses Django's `__iregex` lookup. When no wildcard is present, the cheaper `__icontains` is used instead so the database can keep using B-tree indexes on the simple case. Multi-ingredient search is implemented as a chain of `qs.filter(Q(...))` calls, which produces AND semantics at the SQL level.
- **Image URLs are computed per request.** `RecipeSerializer.get_recipe_image` builds absolute URLs only when needed (local `FileSystemStorage` returns relative `/media/...` paths; R2 already returns absolute `https://pub-….r2.dev/...`). The request object is sniffed for the host so dev and prod both produce correct URLs without hardcoding.
- **Pagination is global, page size 20**, configured at the DRF settings level. JWT lifetimes (30 min access / 7 day refresh) are tuned for an SPA: short enough that a stolen access token has limited blast radius, long enough that the refresh dance is rare under normal use.

### Image management — Cloudflare R2 + responsive variants

Recipe images live in a Cloudflare R2 bucket, written via `django-storages` whenever an admin saves a recipe. `django-imagekit` generates three resized WebP variants (quality 72, widths 400 / 800 / 1200) on save, stored in R2 alongside the original under `CACHE/images/recipes/`. The DRF serializer returns an object with `original`, `small`, `medium`, `large` URLs; both the Django template site and the Vue SPA emit `<img srcset="...">` against those URLs so browsers pick the smallest sufficient image for the viewport and DPR.

Why R2 specifically: free tier covers 10 GB storage with zero egress fees, which fits a portfolio-scale request pattern indefinitely. Render's filesystem is ephemeral, so admin uploads previously didn't survive deploys; R2 makes uploads persistent without standing up a separate database/disk service.

Why pre-generated variants instead of an on-the-fly transformation CDN: a single set of URLs serves both the Render-hosted Django site and the Netlify-hosted Vue SPA without coupling either to a vendor-specific image-transform endpoint, and Cloudflare's image-resizing product requires a paid plan. Storage cost of variants is negligible (~4× per recipe, well under the free-tier ceiling).

Local development falls back to `FileSystemStorage` via `USE_R2_STORAGE=False`, so no R2 credentials are needed for `runserver`. The S3-compatible toggle is in `settings.py`; the actual R2 secrets live in Render's environment, not in this repo or in `render.yaml` (the four `R2_*` vars are marked `sync: false`).

---

## Tech stack

- **Backend:** Django 5.2, Python 3.12, PostgreSQL
- **API:** Django REST Framework, `djangorestframework-simplejwt`, `django-cors-headers`
- **Storage:** Cloudflare R2 (S3-compatible) via `django-storages`; responsive variants via `django-imagekit` (Pillow + WebP)
- **Styling (template site):** Tailwind CSS 3 with a custom brand palette (orange `#f37f20`, teal `#6fc3aa`, green `#a9c57c`, gold `#c0a659`) and Merriweather typography
- **Charts (template site):** matplotlib renders base64 PNGs server-side (the Vue SPA replaces this with Chart.js)
- **Tests:** pytest + pytest-django + pytest-cov, run against a real PostgreSQL service in CI
- **Lint / format:** Ruff (pyflakes, isort, line length 120)
- **CI:** GitHub Actions — lint → test (with coverage upload to Codecov) → security scans (Safety, Bandit) → build (Django system checks, migration validation, collectstatic)
- **Deploy:** Render.com (free tier) at https://nomalyze.com (custom domain) — backed by service `cf-recipe-app`

---

## Key features

- **Auto-difficulty calculation** — derived from cooking time + ingredient count on save (`Recipe.calculate_difficulty()`).
- **Wildcard search** — `*` and `?` patterns translated to regex; AND logic for ingredient combinations.
- **Responsive image variants** — three WebP sizes per recipe served via `<img srcset>`.
- **JWT + session auth coexist** — JWT for the SPA, sessions for the template site, both reading the same `Recipe` model.
- **Server-side charts** — matplotlib base64 PNGs on the Django site; the Vue SPA replaces these with Chart.js against `/api/recipes/search/stats/`.
- **Demo account** — `demo / example123` is read-only safe; data resets on each Render deploy.

---

## Local development

<details>
<summary>Setup with Docker (recommended)</summary>

```bash
git clone https://github.com/nicovece/cf-recipe-app
cd cf-recipe-app
docker-compose up --build
```

Runs Django + PostgreSQL + a Tailwind watcher. Visit `http://localhost:8000`.

</details>

<details>
<summary>Setup without Docker</summary>

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pnpm install                  # for the Tailwind watcher
./manage.sh migrate
./manage.sh createsuperuser
./manage.sh runserver
pnpm run dev                  # in another terminal — Tailwind watch mode
```

</details>

<details>
<summary>Tests, lint, format</summary>

```bash
pytest src/ --cov                                # full suite with coverage
pytest src/recipes/tests.py -k "test_name"       # single test
ruff check src/
ruff format src/
```

</details>

<details>
<summary>Environment variables (production)</summary>

| Variable | Purpose |
|---|---|
| `DEBUG` | `False` in production |
| `SECRET_KEY` | Django secret |
| `DATABASE_URL` | PostgreSQL connection string |
| `ALLOWED_HOSTS` | Comma-separated host list |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origin list (SPA origin in prod) |
| `USE_R2_STORAGE` | `True` to enable R2 (`False` falls back to local FS) |
| `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_PUBLIC_URL` | R2 credentials (set in Render dashboard, `sync: false` in `render.yaml`) |

</details>

---

## Maintainer & Contact

**Maintained by:** Nicola Vece

- Email: me@nicovece.com
- GitHub: [@nicovece](https://github.com/nicovece)
- LinkedIn: [nicovece](https://www.linkedin.com/in/nicovece/)
- Portfolio: [nicovece.dev](https://www.nicovece.dev/)

## Contributing

This is a portfolio project; PRs and issues are welcome but no SLA. For questions, [open an issue](https://github.com/nicovece/cf-recipe-app/issues) or email me@nicovece.com.

## License

MIT — see [LICENSE](LICENSE).
