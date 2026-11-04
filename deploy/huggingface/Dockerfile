# The backend as a Hugging Face Docker Space. The GitHub workflow copies this file, the Space
# README and backend/ (app, data, pyproject.toml) into the Space, so paths are relative to that.
FROM python:3.13-slim

# Spaces run the container as user 1000.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1
WORKDIR $HOME/app

# The CPU build of PyTorch: the default one bundles CUDA, several GB the Space has no GPU for.
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY --chown=user backend/pyproject.toml backend/
COPY --chown=user backend/app backend/app
COPY --chown=user backend/data backend/data
WORKDIR $HOME/app/backend
RUN pip install --no-cache-dir -e ".[finbert]"

# The Space's disk is wiped on every restart, so the model goes into the image instead of
# being downloaded at each start; offline mode then keeps it from reaching out at runtime.
RUN python -c "from transformers import pipeline; from app.engines.finbert_engine import MODEL_ID; pipeline('text-classification', model=MODEL_ID)"
ENV HF_HUB_OFFLINE=1

EXPOSE 7860
# The backend reads the visitor's address itself (TRUSTED_PROXY_HOPS), so uvicorn mustn't rewrite it.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--no-proxy-headers"]
