"""Создаёт схему в Postgres и засевает справочники (витамины, категории).

Запуск из корня проекта:  python -m scripts.init_db
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db.database import SessionLocal, engine  # noqa: E402
from src.db.models import Base  # noqa: E402
from src.db.seed import seed  # noqa: E402


def main() -> None:
    Base.metadata.create_all(engine)
    print("Схема создана.")
    with SessionLocal() as session:
        seed(session)
    print("Справочники засеяны (витамины, категории).")


if __name__ == "__main__":
    main()
