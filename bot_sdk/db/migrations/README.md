# Migrations layout

- SDK-owned migrations live here and should only cover shared/SDK tables.
- Bot-specific schemas should keep their own Alembic env/migrations under each bot directory (e.g., `bots/my_bot/migrations`).
- Point `alembic.ini` in each bot to its own `script_location`; the SDK env in this folder remains for shared models only.
