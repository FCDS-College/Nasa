from railway_sdk import bucket, define_railway, image, preserve, project, redis, service, volume


@define_railway
def main(ctx=None):
    postgres_variables = {
        name: preserve()
        for name in (
            "DATABASE_URL",
            "PGDATA",
            "PGDATABASE",
            "PGHOST",
            "PGPASSWORD",
            "PGPORT",
            "PGUSER",
            "POSTGRES_DB",
            "POSTGRES_PASSWORD",
            "POSTGRES_USER",
            "RAILWAY_DEPLOYMENT_DRAINING_SECONDS",
            "SSL_CERT_DAYS",
        )
    }
    redis_cache = redis("Redis", region="sfo")
    redis_volume = volume(
        "redis-volume",
        {
            "alerts": {"usage": {"100": {}, "80": {}, "95": {}}},
            "allowOnlineResize": True,
            "region": "sfo",
            "sizeMB": 5000,
        },
    )
    postgres_volume = volume(
        "postgres-volume",
        {
            "alerts": {"usage": {"100": {}, "80": {}, "95": {}}},
            "allowOnlineResize": True,
            "region": "sfo",
            "sizeMB": 5000,
        },
    )
    postgres_db = service(
        "Postgres",
        source=image("pgvector/pgvector:pg18"),
        replicas={"sfo": 1},
        env=postgres_variables,
        volumeMounts={"/var/lib/postgresql/data": postgres_volume},
    )
    artifacts = bucket("versatile-bin-Yo7I", {"region": "sjc"})

    existing_api_variables = {
        name: preserve()
        for name in (
            "FLAME_API_AUTH_ENABLED",
            "FLAME_AURA_BASE_URL",
            "FLAME_AURA_ENABLED",
            "FLAME_DATABASE_URL",
            "FLAME_ENVIRONMENT",
            "FLAME_READ_API_TOKEN",
            "FLAME_REDIS_URL",
            "FLAME_S3_ACCESS_KEY",
            "FLAME_S3_BUCKET",
            "FLAME_S3_ENDPOINT_URL",
            "FLAME_S3_REGION",
            "FLAME_S3_SECRET_KEY",
            "FLAME_WRITE_API_TOKEN",
        )
    }
    existing_api_variables["PORT"] = "8000"
    existing_worker_variables = {
        name: preserve()
        for name in (
            "FLAME_API_AUTH_ENABLED",
            "FLAME_AURA_BASE_URL",
            "FLAME_AURA_ENABLED",
            "FLAME_DATABASE_URL",
            "FLAME_ENVIRONMENT",
            "FLAME_REDIS_URL",
            "FLAME_S3_ACCESS_KEY",
            "FLAME_S3_BUCKET",
            "FLAME_S3_ENDPOINT_URL",
            "FLAME_S3_REGION",
            "FLAME_S3_SECRET_KEY",
        )
    }

    api = service(
        "flame-api",
        replicas={"sfo": 1},
        env=existing_api_variables,
        build={"builder": "DOCKERFILE", "dockerfilePath": "apps/api/Dockerfile"},
        preDeploy="alembic upgrade head && python -m flame_api.seed && python -m flame_api.ingest",
        healthcheck="/health/live",
        healthcheckTimeout=30,
    )
    worker = service(
        "flame-worker",
        replicas={"sfo": 1},
        env=existing_worker_variables,
        build={"builder": "DOCKERFILE", "dockerfilePath": "apps/api/Dockerfile"},
        start='sh -c \'exec rq worker --url "$FLAME_REDIS_URL" flame-analysis\'',
    )

    return project(
        "flame-in-freefall-aura",
        resources=[
            postgres_db,
            api,
            worker,
            redis_cache,
            redis_volume,
            postgres_volume,
            artifacts,
        ],
    )
