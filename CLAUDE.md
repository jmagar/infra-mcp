# Claude Code Memory

This file contains instructions for Claude to follow when working on the `infrastructor` project.

## 🏛️ Architecture

*   The project is a dual-server architecture with a FastAPI REST API and a `fastmcp` MCP server.
*   The MCP server is a client to the REST API. All operations should go through the API.
*   The database is a TimescaleDB instance running in a Docker container.

## 💻 Development

*   The `dev.sh` script is the primary way to manage the development environment.
*   The API server runs on port `9101` and the MCP server runs on port `9102`.
*   The project uses `ruff` for linting and formatting, and `mypy` for type checking.

## 🗄️ Database

*   The database schema is managed through SQL scripts in the `init-scripts` directory and migrations in the `alembic` directory.
*   The schema makes extensive use of TimescaleDB features like hypertables, compression policies, and continuous aggregates.

## 🛠️ Tools

*   The project uses a variety of tools, including `fastapi`, `fastmcp`, `sqlalchemy`, `asyncpg`, `httpx`, and `asyncssh`.
*   The full list of dependencies can be found in the `pyproject.toml` file.
