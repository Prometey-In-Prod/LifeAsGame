from aiogram.fsm.state import State, StatesGroup


class DailyCheckin(StatesGroup):
    bedtime = State()
    wakeup = State()
    trained = State()
    work_hours = State()
    vitamins = State()
    mood = State()
    energy = State()
    day_rating = State()
    weight = State()
    note = State()
