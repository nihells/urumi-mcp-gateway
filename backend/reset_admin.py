from pathlib import Path
from getpass import getpass

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import User
from app.security import hash_password, verify_password


def main():
    database_path = (Path.cwd() / "data" / "urumi.db").resolve()

    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}"
    )

    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        user = (
            db.query(User)
            .filter(User.username == "admin")
            .first()
        )

        if user is None:
            print("Admin account not found. No changes made.")
            return

        print("Admin account found.")

        password = getpass(
            "Enter NEW admin password (minimum 12 characters): "
        )
        confirmation = getpass("Confirm new password: ")

        if len(password) < 12:
            print("Password must be at least 12 characters.")
            return

        if password != confirmation:
            print("Passwords do not match.")
            return

        user.password_hash = hash_password(password)
        db.commit()

        verified = verify_password(password, user.password_hash)

        print("Password reset and verification:", verified)
        print("Database:", database_path)

    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    main()