FROM mambaorg/micromamba:1.5-jammy

COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml /tmp/environment.yml
RUN micromamba install -y -n base -f /tmp/environment.yml && \
    micromamba clean --all --yes

WORKDIR /app
COPY backend/ ./backend/
COPY pyproject.toml ./

EXPOSE 8000

CMD ["uvicorn", "backend.api.routes:app", "--host", "0.0.0.0", "--port", "8000"]
