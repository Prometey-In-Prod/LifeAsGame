from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import Category, Vitamin

VITAMINS = [
    "Креатин",
    "Магний",
    "VitaComplex",
    "Куркумин",
    "AlfaGPS",
    "D3",
    "Элеутерококк",
    "Женьшень",
    "Родиола Розовая",
]

CATEGORIES: dict[str, list[str]] = {
    "income": ["Зарплата", "Подработка", "Биржа", "Процент по вкладам"],
    "expense": [
        "Еда",
        "Личная жизнь",
        "Транспорт",
        "Домашние расходы",
        "Одежда",
        "Уход и красота",
        "Здоровье",
        "Образование",
        "Подарки",
        "Домашние животные",
        "Саморазвитие",
    ],
    "debt": ["Кредитка Т", "Кредитка А1", "Кредитка А2"],
    "saving": ["Путешествие", "Крипта", "Вклады", "Акции", "Фонды"],
}


def seed(session: Session) -> None:
    existing_vits = set(session.scalars(select(Vitamin.name)))
    for name in VITAMINS:
        if name not in existing_vits:
            session.add(Vitamin(name=name))

    existing_cats = {(c.name, c.kind) for c in session.scalars(select(Category))}
    for kind, names in CATEGORIES.items():
        for name in names:
            if (name, kind) not in existing_cats:
                session.add(Category(name=name, kind=kind))

    session.commit()
