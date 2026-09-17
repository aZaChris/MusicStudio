# Deploying MusicStudio to AWS

Two documented paths. ECS Fargate is the primary/recommended path (matches the
Docker Compose services 1:1, demonstrates real container orchestration). A plain
EC2 + Docker Compose box is a lower-cost fallback for a demo deployment.

## Option A: ECS Fargate (primary)

**Managed services**:
- **RDS PostgreSQL** — replaces the `db` Compose service. Single `db.t4g.micro` is
  plenty for this workload (≤10 teachers).
- **ElastiCache Redis** — replaces the `redis` Compose service (Celery broker/backend).
- **ECR** — one repository per image: `musicstudio-backend`, `musicstudio-frontend`.
- **ECS Fargate cluster**, one service per Compose service that isn't a managed
  dependency: `backend` (gunicorn, `infra/backend.Dockerfile`), `celery-worker`,
  `celery-beat` (same image, different `command`), `frontend` (nginx serving the
  Vite build — the `prod` stage of `infra/frontend.Dockerfile`).
- **Application Load Balancer** in front of the `backend` and `frontend` services
  (path-based routing: `/api/*`, `/admin/*` → backend; everything else → frontend;
  or serve the SPA from S3+CloudFront and only put the ALB in front of `backend`).
- **Secrets Manager / SSM Parameter Store** for `DJANGO_SECRET_KEY`, `JWT_SIGNING_KEY`,
  `DATABASE_URL`, `CELERY_BROKER_URL`, SMTP credentials — injected as task-definition
  secrets, never baked into the image or committed.

**Steps**:

1. Build and push images:
   ```bash
   aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
   docker build -f infra/backend.Dockerfile -t <account>.dkr.ecr.<region>.amazonaws.com/musicstudio-backend backend/
   docker push <account>.dkr.ecr.<region>.amazonaws.com/musicstudio-backend
   docker build -f infra/frontend.Dockerfile --target prod -t <account>.dkr.ecr.<region>.amazonaws.com/musicstudio-frontend frontend/
   docker push <account>.dkr.ecr.<region>.amazonaws.com/musicstudio-frontend
   ```
2. Provision RDS + ElastiCache, note their endpoints.
3. Store secrets in SSM/Secrets Manager (`DJANGO_SECRET_KEY`, `JWT_SIGNING_KEY`,
   `DATABASE_URL` pointing at RDS, `CELERY_BROKER_URL` pointing at ElastiCache, SMTP vars).
4. Create 4 ECS task definitions (backend, celery-worker, celery-beat, frontend),
   each pulling secrets from step 3 as environment variables.
5. Run the `backend` task's `python manage.py migrate` once (a one-off ECS `RunTask`,
   not part of the long-running service) before the services take traffic.
6. Create the 4 ECS services behind the ALB / CloudFront as described above.
7. Point DNS (Route 53) at the ALB/CloudFront distribution.

## Option B: EC2 + Docker Compose (lower-cost demo fallback)

1. Launch a single EC2 instance (Ubuntu, `t3.small` is enough), install Docker +
   Docker Compose.
2. `git clone` the repo, copy `infra/.env.example` to `infra/.env` and fill in
   production values (a real `DJANGO_SECRET_KEY`/`JWT_SIGNING_KEY`, `DJANGO_DEBUG=false`,
   `DJANGO_SETTINGS_MODULE=config.settings.prod`, real SMTP credentials).
3. `cd infra && docker compose up -d --build` — same Compose file used locally; this is
   the entire point of shipping Docker Compose as the local dev environment too.
4. Put an Elastic IP on the instance and point DNS at it. For TLS, put a Caddy or
   nginx reverse proxy (or an ALB) in front of the `backend`/`frontend` ports and
   terminate TLS there — `config.settings.prod` assumes TLS termination happens
   upstream (`SECURE_SSL_REDIRECT = True`).
5. Take RDS/ElastiCache out of the picture for this fallback — `db`/`redis` just run
   as Compose services on the same box, accepted trade-off for a low-cost demo.

## Either path

- Django serves `/api/schema/` and `/api/docs/` — useful to sanity-check a fresh
  deployment reached a healthy `backend` before pointing users at it.
- `python manage.py seed_demo` (see `specs/001-musicstudio-mvp/quickstart.md`) is safe
  to run once against a fresh deployment to have something to click through in a demo.
