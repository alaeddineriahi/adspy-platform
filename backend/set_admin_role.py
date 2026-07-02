"""
One-off: promote a Clerk user to admin (or demote back to member).

    venv/Scripts/python.exe set_admin_role.py alariahi123@gmail.com admin

Run from backend/. Requires CLERK_SECRET_KEY in .env.
"""

import asyncio
import sys

from app.core import clerk_admin


async def main():
    if len(sys.argv) < 2:
        print("usage: set_admin_role.py <email> [admin|member]")
        sys.exit(1)
    email = sys.argv[1]
    role = sys.argv[2] if len(sys.argv) > 2 else "admin"

    user = await clerk_admin.get_user_by_email(email)
    if user is None:
        print(f"No Clerk user found for {email!r} — sign up first, then re-run this.")
        sys.exit(1)

    updated = await clerk_admin.set_role(user["id"], role)
    print(f"{updated['email']} ({updated['id']}) is now role={updated['role']!r}")


if __name__ == "__main__":
    asyncio.run(main())
