"""One-off: add credit_bonus/is_comp to the existing subscriptions table.

create_all() only creates missing tables, not missing columns on existing
ones — run this once before the admin backoffice's new columns are usable.
"""

import asyncio

from sqlalchemy import text

from app.core.database import engine


async def main():
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS credit_bonus INTEGER NOT NULL DEFAULT 0"
        ))
        await conn.execute(text(
            "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS is_comp BOOLEAN NOT NULL DEFAULT FALSE"
        ))
    print("subscriptions: credit_bonus + is_comp columns ready.")


if __name__ == "__main__":
    asyncio.run(main())
