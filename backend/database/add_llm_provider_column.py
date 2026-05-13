"""
Add users.preferred_llm_provider for existing PostgreSQL databases.

Run from the backend directory:
    python -m database.add_llm_provider_column
"""

from sqlalchemy import text

from database.database import engine


def main() -> None:
    stmt = text(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
        "preferred_llm_provider TEXT NOT NULL DEFAULT 'deepseek'"
    )
    with engine.begin() as conn:
        conn.execute(stmt)
    print("[OK] Column users.preferred_llm_provider is present.")


if __name__ == "__main__":
    main()
