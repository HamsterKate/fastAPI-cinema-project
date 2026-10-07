# 🎬 Cinema 2.0

> A production-oriented Online Cinema API built with FastAPI.

Cinema 2.0 lets users explore a movie catalog, manage profiles and favorites, add movies to a cart, create orders, and pay through Stripe Checkout.

---

## 📚 Contents

- [✨ Features](#features)
- [🛠 Tech stack](#tech-stack)
- [🚀 Quick start](#quick-start)
- [📖 API documentation](#api-documentation)
- [🧪 Testing and coverage](#testing-and-coverage)
- [🔄 CI](#ci)
- [🗂 Project structure](#project-structure)
- [🛑 Stop services](#stop-services)

<a id="features"></a>

## ✨ Features

| Area | What it provides |
| --- | --- |
| 👤 Accounts | Registration, email activation, login, JWT refresh, logout, and password recovery |
| 🛡 Roles | Role-based access control for users and moderators |
| 🎞 Movies | Catalog, filters, pagination, create/update, soft delete, and bulk-import utilities |
| 🪪 Profiles | Editable profile data and avatar uploads to MinIO |
| ❤️ Favorites | Add, list, and remove favorite movies |
| 🛒 Cart | Add/remove items and clear the shopping cart |
| 📦 Orders | Checkout from cart, order history, details, and cancellation |
| 💳 Payments | Stripe Checkout session creation and webhook processing |

<a id="tech-stack"></a>

## 🛠 Tech stack

- **Python 3.12**
- **FastAPI** and Pydantic
- **PostgreSQL 17**
- **SQLAlchemy** and Alembic
- **Docker Compose**
- **MinIO** for avatar storage
- **MailHog** for development emails
- **Stripe** for payments
- **Pytest** and **pytest-cov**
- **GitHub Actions** for CI

<a id="quick-start"></a>

## 🚀 Quick start

### 1. Create environment variables

```powershell
Copy-Item .env.sample .env
```

> Configure Stripe variables only if you want to test the payment flow with Stripe.

### 2. Build and start the application

```powershell
docker compose up -d --build
```

### 3. Apply database migrations

```powershell
docker compose exec web alembic upgrade head
```

### 4. Open local services

| Service | URL |
| --- | --- |
| 🎬 API | <http://localhost:8000> |
| 📖 Swagger UI | <http://localhost:8000/docs> |
| 📘 ReDoc | <http://localhost:8000/redoc> |
| ✉️ MailHog | <http://localhost:8025> |
| 🗄 MinIO Console | <http://localhost:9001> |

<a id="api-documentation"></a>

## 📖 API documentation

Interactive API documentation is generated automatically by FastAPI:

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

All API endpoints use the `/api/v2` prefix.

<a id="testing-and-coverage"></a>

## 🧪 Testing and coverage

The project contains API and unit tests for accounts, movies, profiles, favorites, cart, orders, payments, pagination, and movie-import utilities.

Run the complete test suite:

```powershell
docker compose exec web pytest -v
```

Run tests with coverage reporting:

```powershell
docker compose exec web pytest --cov=app --cov-report=term-missing
```

Current result:

```text
155 passed · 78% coverage
```

<a id="ci"></a>

## 🔄 CI

GitHub Actions runs on every push and pull request.

The pipeline:

1. Builds and starts Docker services.
2. Checks Python compilation.
3. Applies Alembic migrations.
4. Verifies migration consistency.
5. Runs the complete test suite with coverage reporting.

<a id="project-structure"></a>

## 🗂 Project structure

```text
app/
├── accounts/       # Authentication, authorization, tokens, email flows
├── cart/           # Shopping cart
├── core/           # Configuration, pagination, storage
├── db/             # Database session and migrations
├── favorites/      # Favorite movies
├── movies/         # Movie catalog and import utilities
├── orders/         # Checkout and order management
├── payments/       # Stripe Checkout and webhook handling
└── profiles/       # User profiles and avatars

tests/              # API and unit tests
```

<a id="stop-services"></a>

## 🛑 Stop services

Stop containers while preserving database volumes:

```powershell
docker compose down
```

Stop containers and remove local volumes:

```powershell
docker compose down -v
```