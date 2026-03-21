from aiogram.fsm.state import State, StatesGroup


class VeoStates(StatesGroup):
    waiting_for_prompt = State()
    waiting_for_quality = State()
