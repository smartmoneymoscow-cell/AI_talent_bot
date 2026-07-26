"""FSM-состояния для диалогов."""
from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    choosing_role = State()
    entering_name = State()
    entering_bio = State()
    entering_skills = State()       # для специалистов
    entering_portfolio = State()     # для специалистов
    entering_rate = State()          # для специалистов (₽/час)
    entering_budget = State()        # для работодателей


class ProfileEditStates(StatesGroup):
    editing_name = State()
    editing_bio = State()
    editing_skills = State()
    editing_portfolio = State()
    editing_rate = State()


class OrderCreateStates(StatesGroup):
    entering_title = State()
    entering_description = State()
    choosing_category = State()
    entering_budget = State()
    entering_deadline = State()
    confirming = State()


class ApplicationStates(StatesGroup):
    entering_message = State()
    entering_price = State()


class ReviewStates(StatesGroup):
    entering_rating = State()
    entering_comment = State()


class SearchStates(StatesGroup):
    entering_query = State()
    choosing_category = State()
