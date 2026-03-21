from aiogram.fsm.state import State, StatesGroup


class NanoBananaStates(StatesGroup):
    waiting_for_prompt = State()
    waiting_for_quality = State()
