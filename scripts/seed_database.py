from app.database import SessionLocal, create_database
from app.services.content_service import load_pills


def main() -> None:
    create_database()
    with SessionLocal() as db:
        created = load_pills(db)
    print(f"Database ready. {created} pill(s) created.")


if __name__ == "__main__":
    main()
