import argparse
import asyncio
from passlib.context import CryptContext

from app.db import SessionLocal
from app.models import User, UserRole

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


async def create_admin(email: str, password: str) -> None:
    async with SessionLocal() as session:
        async with session.begin():
            session.add(
                User(
                    email=email,
                    password_hash=pwd_context.hash(password),
                    role=UserRole.admin,
                )
            )
        print(f"Admin {email} created.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--email",
        required=True,
        help="Email address of administartor account. Used for login",
    )
    parser.add_argument(
        "--password", required=True, help="Password for administrator account"
    )
    args = parser.parse_args()

    asyncio.run(create_admin(args.email, args.password))


if __name__ == "__main__":
    main()
