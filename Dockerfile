# syntax=docker/dockerfile:1
FROM python:3.11.3-slim-buster as base

# Setup ENV variables here (if needed in the future)


FROM base as python-deps

# Install pipx and poetry
RUN pip3 install --user pipx
ENV PATH=/root/.local/bin:$PATH
RUN pipx install poetry==1.8.2
ENV PATH=/root/.local/pipx/venvs/poetry/bin:$PATH

# Install python dependencies in /.venv
COPY pyproject.toml .
COPY poetry.lock .
RUN poetry config virtualenvs.in-project true
RUN poetry install --only main


FROM base
# Copy virtual env from python-deps stage
COPY --from=python-deps /.venv /.venv
ENV PATH="/.venv/bin:$PATH"

# Setup workdir and add to PYTHONPATH
WORKDIR /bot
ENV PYTHONPATH="/bot/wappu_spiriter/:$PYTHONPATH"

# Install app into container
COPY . .

# Create a non-root user and add permission to access /bot folder
RUN adduser -u 5678 --disabled-password --gecos "" botuser
RUN chown -R botuser /bot
USER botuser

# Run the app
CMD [ "python3", "-m", "wappu_spiriter" ]