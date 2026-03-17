from aiogram.fsm.state import State, StatesGroup


class KlingStates(StatesGroup):
    waiting_for_prompt = State()
