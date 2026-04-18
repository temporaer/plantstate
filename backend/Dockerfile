FROM mambaorg/micromamba:1.5-jammy

USER root
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
USER $MAMBA_USER

COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml /tmp/environment.yml
RUN micromamba install -y -n base -f /tmp/environment.yml && \
    micromamba clean --all --yes

WORKDIR /app
COPY backend/ ./backend/
COPY pyproject.toml ./

RUN mkdir -p /app/data

EXPOSE 8000

ENV DATABASE_URL=sqlite:///data/plant_state.db

CMD ["python", "-m", "uvicorn", "backend.api.routes:app", "--host", "0.0.0.0", "--port", "8000"]
