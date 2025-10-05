FROM alpine:3 AS build
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml /app/
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /bin/
ENV UV_LINK_MODE=copy
ENV UV_PYTHON_INSTALL_DIR=/python
RUN --mount=type=cache,target=/root/.cache/uv uv sync --compile-bytecode --extra server
COPY . /app/
RUN unset DATABASE_URL; uv run manage.py collectstatic --noinput --clear -v 1
RUN apk add --no-cache gettext
RUN unset DATABASE_URL; uv run manage.py compilemessages --ignore .venv || true

FROM nginx:1-alpine-slim
ENV UV_PYTHON_INSTALL_DIR=/python
COPY --from=build /app /app
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /bin/
COPY --from=build /python /python
RUN apk add --no-cache nginx supervisor
RUN mkdir -p /etc/nginx/conf.d
COPY ./nginx.conf /etc/nginx/conf.d/default.conf
WORKDIR /app
VOLUME ["/app/media"]
EXPOSE 80
ENTRYPOINT sh -c "\
nginx -g \"daemon off;\" & \
case \"\$DATABASE_URL\" in \
    postgres*) \
        uv pip install psycopg[binary,pool]~=3.2 \
        ;; \
    mysql*) \
        uv pip install mysqlclient~=2.2 \
        ;; \
esac; \
uv run --no-sync gunicorn feuilles_annonces.wsgi:application --bind 0.0.0.0:8000 & \
uv run --no-sync manage.py migrate; \
uv run --no-sync manage.py createcachetable; \
wait \
"
