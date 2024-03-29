from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from bot import dp, bot
from aiogram.types import ParseMode
from bot_storage.Keyboards import rasp_by_days_kb, cancel_kb
from bot_storage.Keyboards import InlineKeyboardMarkup, InlineKeyboardButton
from bot_storage.timetable.rasp_base import get_all_teachers, get_teacher_lessons_for_week_day, get_week_rasp_by_role
from bot_storage.accounts_base import get_role
from bot_storage.UserStates import get_role_waiting_for_action_state
from bot_storage.Keyboards import get_role_keyboard
from utils.scheduled_tasks import set_message_timeout_and_reset_state


class TeacherRaspReqStates(StatesGroup):
    waiting_for_inline_week_day_chose = State()
    waiting_for_teacher_name = State()


async def make_teacher_rasp_request(message: types.Message, teacher_name=None):
    # TODO: приделать сюда FSMContext и убрать дубликацию кода
    print(f"action make_teacher_rasp_request, teacher_name = {teacher_name}")
    if teacher_name is None:
        await message.answer("Для кого вы хотите узнать расписание?", reply_markup=cancel_kb)
        await TeacherRaspReqStates.waiting_for_teacher_name.set()
    else:
        await message.answer(f"Запрос расписания для {teacher_name}",
                             reply_markup=get_role_keyboard(get_role(message.from_user.id)))
        kb_msg = await message.answer("Выберите день недели", reply_markup=rasp_by_days_kb)
        set_message_timeout_and_reset_state(message.from_user.id, kb_msg.chat.id, kb_msg.message_id)
        await TeacherRaspReqStates.waiting_for_inline_week_day_chose.set()


@dp.message_handler(state=TeacherRaspReqStates.waiting_for_teacher_name, content_types=types.ContentType.TEXT)
async def get_teacher_name(message: types.Message, state: FSMContext):
    teacher_name = message.text.lower()
    print("запрошено раписание учителя", teacher_name)
    teacher_name = message.text.lower()
    teachers_set = set(map(str.lower, get_all_teachers()))
    if teacher_name in teachers_set:
        await state.update_data(teacher_name=teacher_name.title())
        await message.answer(f"Запрос расписания для {teacher_name}",
                             reply_markup=get_role_keyboard(get_role(message.from_user.id)))
        kb_msg = await message.answer("Хорошо, выберите день недели", reply_markup=rasp_by_days_kb)
        set_message_timeout_and_reset_state(message.from_user.id, kb_msg.chat.id, kb_msg.message_id)
        await TeacherRaspReqStates.waiting_for_inline_week_day_chose.set()
    else:
        teachers_choose_list = []
        teachers_choose_list_kb = InlineKeyboardMarkup(row_width=2)
        for teacher_full_name in teachers_set:
            if teacher_full_name.find(teacher_name) >= 0:
                # print(teacher_full_name)
                teachers_choose_list.append(teacher_full_name)
                teacher_full_name_button = InlineKeyboardButton(teacher_full_name.title(),
                                                                callback_data=teacher_full_name.strip())
                teachers_choose_list_kb.insert(teacher_full_name_button)
        if len(teachers_choose_list) < 1:
            await message.reply("Я не нашел такого учителя, введите снова")
        elif len(teachers_choose_list) >= 1:
            print(teachers_choose_list_kb)
            teachers_kb = await message.answer("Выберите учителя из списка", reply_markup=teachers_choose_list_kb)
            set_message_timeout_and_reset_state(message.from_user.id, teachers_kb.chat.id, teachers_kb.message_id)


@dp.callback_query_handler(state=TeacherRaspReqStates.waiting_for_teacher_name)
async def teacher_full_name_inline(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    teacher_name = callback_query.data
    print("выбор", teacher_name, "с инлайн клавиатуры")
    await state.update_data(teacher_name=teacher_name.title())
    kb_msg = await bot.send_message(callback_query.from_user.id, "Хорошо, выберите день недели",
                                    reply_markup=rasp_by_days_kb)
    set_message_timeout_and_reset_state(callback_query.from_user.id, kb_msg.chat.id, kb_msg.message_id)
    await TeacherRaspReqStates.waiting_for_inline_week_day_chose.set()


@dp.callback_query_handler(lambda cq: cq.data in ["monday", "tuesday", "wednesday",
                                                  "thursday", "friday", "saturday", "week"],
                           state=TeacherRaspReqStates.waiting_for_inline_week_day_chose)
async def rasp_by_day_inline_handler(callback_query: types.CallbackQuery, state: FSMContext):
    print(f"callback_data: {callback_query.data}")
    print(f"state_data: {await state.get_data()}")
    user_id = callback_query.from_user.id
    user_role = get_role(user_id)
    user_waiting_for_action_state = get_role_waiting_for_action_state(user_role)
    print(f"next state is {user_waiting_for_action_state}")
    print(f"current state is {await state.get_state()}")
    await bot.answer_callback_query(callback_query.id)
    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    callback_data_text = {'monday': 0, 'tuesday': 1, 'wednesday': 2,
                          'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
    callback_data = callback_query.data
    user_data = await state.get_data()
    teacher_name = user_data['teacher_name']
    print("запрос расписания для", teacher_name, "на", callback_data)
    if teacher_name is not None:
        lessons = None
        if callback_data == "week":  # запрос всей недели
            lessons = get_week_rasp_by_role('teacher', teacher_name)
        else:  # запрос по дням
            lessons = get_teacher_lessons_for_week_day(teacher_name, callback_data_text[callback_data])

        await bot.send_message(user_id, lessons,
                               parse_mode=ParseMode.MARKDOWN_V2, reply_markup=get_role_keyboard(user_role))
        await user_waiting_for_action_state.set()
    else:
        await bot.send_message(chat_id=callback_query.message.chat.id, text="для кого вы хотите узнать распиание?")
        await TeacherRaspReqStates.waiting_for_teacher_name.set()
