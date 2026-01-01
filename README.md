# 🌿 Philoropia Store API (Django REST Framework)

> A production-ready backend API for a **Plants** application — built with **Django + Django REST Framework**, containerized with **Docker**, and structured for clean, scalable development.

---

## ✨ What’s inside

Based on the repository structure, this project includes:

- **Django project layout** with separate modules/apps: `config`, `core`, `store` citeturn13view0  
- **Dockerized development stack** (`Dockerfile`, `docker-compose.yml`) citeturn13view0  
- **Pytest configuration** (`pytest.ini`) for test automation citeturn13view0  
- **Python dependency pinning** (`requirements.txt`) citeturn13view0  
- **Internationalization assets** under `locale/fa/LC_MESSAGES` (Farsi locale) citeturn13view0  
- Included data artifacts such as `backup.json`, `dump.rdb` (useful for seeding/testing in local setups) citeturn13view0  

> Note: GitHub’s web renderer returned “error while loading” in this environment, so this README is written to be **accurate to the repo layout** while keeping API-specific details (routes, schemas, env keys) as **discoverable** and easy to fill in.

---

## 🧠 Suggested project name options (for GitHub)

Pick one (all short & brandable):

1. **FloraStore API** ✅ (recommended)
2. **GreenPulse API**
3. **Plantify Backend**
4. **BloomStack API**
5. **Herbarium API**

---

## 🧱 Project structure

```text
.
├── config/                      # Django project config (settings/urls/asgi/wsgi, etc.)
├── core/                        # Shared utilities, base models, common services
├── store/                       # Domain app (plants, categories, products, orders, etc.)
├── locale/fa/LC_MESSAGES/       # i18n (Farsi) translations
├── Dockerfile
├── docker-compose.yml
├── manage.py
├── pytest.ini
├── requirements.txt
├── backup.json
└── dump.rdb
```

(Directory names confirmed from repository root listing.) citeturn13view0

---

## ✅ Requirements

- Python **3.10+** (recommended)
- Docker + Docker Compose (recommended for consistent local setup) citeturn13view0  

---

## 🚀 Quickstart (Docker)

> Use this path if you want “clone → run” with minimal setup.

```bash
# 1) Build & start containers
docker compose up --build

# 2) Run migrations (in the web container)
docker compose exec web python manage.py migrate

# 3) (Optional) Create a superuser
docker compose exec web python manage.py createsuperuser

# 4) (Optional) Load seed data if you use backup.json
docker compose exec web python manage.py loaddata backup.json
```

### Common Docker commands

```bash
# Stop
docker compose down

# Rebuild
docker compose up --build

# Logs
docker compose logs -f

# Django shell
docker compose exec web python manage.py shell
```

---

## 🧰 Local development (without Docker)

```bash
# 1) Create & activate a virtualenv
python -m venv .venv
source .venv/bin/activate   # (Windows) .venv\Scripts\activate

# 2) Install deps
pip install -r requirements.txt

# 3) Run migrations
python manage.py migrate

# 4) Run the server
python manage.py runserver
```

---

## ⚙️ Environment variables

Create a `.env` file (or export env vars) for a clean setup.

Recommended baseline (adapt to your settings file):

```env
DJANGO_SETTINGS_MODULE=config.settings
SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Database (example)
DB_NAME=plants
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# CORS (example)
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

> Tip: keep `.env.example` committed, keep real `.env` untracked.

---

## 🔐 Authentication

If authentication is enabled in your settings, document it here (pick the one you use):

- Session Auth (admin/browsable API)
- Token Auth
- JWT (recommended for Flutter/mobile)

Example (JWT, if used):

```http
POST /api/auth/token/
{
  "username": "...",
  "password": "..."
}
```

---

## 🌱 API documentation

If you’ve enabled DRF schema tooling (recommended), link it here:

- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`
- OpenAPI JSON: `/api/schema/`

If not enabled yet, consider adding `drf-spectacular` or `drf-yasg` to generate a clean OpenAPI spec.

---

## 🧪 Testing

This repo includes a `pytest.ini`, so tests are expected to be runnable via pytest. citeturn13view0

```bash
pytest -q
```

Useful options:

```bash
pytest -q --disable-warnings --maxfail=1
pytest -k "store"
pytest -x
```

---

## 🌍 Internationalization (i18n)

Farsi locale assets exist under `locale/fa/LC_MESSAGES`. citeturn13view0

Typical workflow:

```bash
# Create / update message files
django-admin makemessages -l fa

# Compile translations
django-admin compilemessages
```

---

## 🗄️ Seed data & backups

The root includes:

- `backup.json` (commonly used as a Django fixture)
- `dump.rdb` (commonly associated with Redis dumps)

These can be used to quickly bootstrap a local environment. citeturn13view0

If you want a standard flow, keep fixtures in a dedicated directory:

```text
fixtures/
  └── initial_data.json
```

Then load:

```bash
python manage.py loaddata fixtures/initial_data.json
```

---

## 📦 Deployment notes

Recommended production checklist:

- `DEBUG=False`
- strong `SECRET_KEY`
- set `ALLOWED_HOSTS`
- configure DB (PostgreSQL recommended)
- serve via `gunicorn` behind Nginx
- static/media handling (S3 or Nginx volume)
- run migrations in release step
- centralized logging (Sentry / ELK)

If you want, I can generate:
- `docker-compose.prod.yml`
- `gunicorn.conf.py`
- `.env.example`
- CI pipeline (GitHub Actions) for tests + lint + build

---

## 🤝 Contributing

```bash
# Create a feature branch
git checkout -b feat/your-feature

# Run formatting/linting (suggested)
# ruff / black / isort / mypy (choose your stack)

# Run tests
pytest
```

---

## 📄 License

A license file exists in the repository root (check `LICENSE` in your repo). citeturn13view0

---

## 📬 Contact

**Pouria Shirali**  
- LinkedIn: https://linkedin.com/in/pouriashiralipour  
- Instagram: https://instagram.com/pouria.shirali
