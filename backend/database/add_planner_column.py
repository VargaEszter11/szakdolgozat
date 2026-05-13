"""
Add users.use_travel_log_in_planner for existing PostgreSQL databases.

Run from the backend directory:
    python -m database.add_planner_column
"""

from sqlalchemy import text

from database.database import engine


def main() -> None:
    stmt = text(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
        "use_travel_log_in_planner BOOLEAN NOT NULL DEFAULT true"
    )
    with engine.begin() as conn:
        conn.execute(stmt)
    print("[OK] Column users.use_travel_log_in_planner is present.")


if __name__ == "__main__":
    main()
