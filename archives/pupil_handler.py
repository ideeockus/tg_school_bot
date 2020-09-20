from aiogram import Bot, Dispatcher, executor, types, utils
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from rasp_base import get_lessons_for_today, get_lessons_for_yesterday, check_for_class, get_lessons_by_day
from bot import dp, bot
from Keyboards import pupil_kb, pupil_rasp_by_days_kb, ReplyKeyboardRemove

# logging.basicConfig(filename='tatgram_rasp34.log', level=logging.DEBUG)


class PupilStates(StatesGroup):
    rasp_today = State()  # расписание на сегодня
    rasp_yesterday = State()  # расписание на завтра
    waiting_for_class_name = State()  # ожидание номера класса
    waiting_for_action = State()  # ожидание действий
    waiting_for_identifier = State()  # ждет название класса
    waiting_for_registration = State()
    waiting_for_other_class_name = State()  # для другого класса


@dp.message_handler(state=PupilStates.waiting_for_registration, content_types=types.ContentType.TEXT)
async def rasp_today(message: types.Message, state: FSMContext):
    # classes_set = get_all_classes()
    # print(classes_set)
    class_name = message.text
    if check_for_class(class_name):
        print("Регистрация в классе", message.text)
        await state.update_data(class_name=message.text)
        await message.answer("Окей, ты зарегистрирован", reply_markup=pupil_kb)
        await message.answer("Теперь ты можешь узнать расписание")
        await PupilStates.waiting_for_action.set()
    else:
        await message.answer("Не могу найти такого класса, введите еще раз")


@dp.message_handler(lambda m: m.text in ["На сегодня", "На завтра"], state=PupilStates.waiting_for_action)
async def rasp_today(message: types.Message, state: FSMContext):
    # print("УФХЦЧШЦХЗ")
    user_data = await state.get_data()
    role = user_data['chosen_role']
    class_name = user_data['class_name']
    print(role, "запросил расписание", message.text)

    if class_name is not None:
        if message.text.lower() == "на сегодня":
            lessons = get_lessons_for_today(class_name)
            await message.answer(lessons)
            await PupilStates.waiting_for_action.set()
        if message.text.lower() == "на завтра":
            lessons = get_lessons_for_yesterday(class_name)
            await message.answer(lessons)
            await PupilStates.waiting_for_action.set()
        return

    print("класс не указан", user_data)

    await message.answer("Укажите свой класс, пожалуйста")
    # await RaspBotStates.wait_for_class_name_rasp_today.set()
    if message.text == "На сегодня":
        await state.update_data(lessons_for="сегодня")
        await PupilStates.rasp_today.set()
    if message.text == "На завтра":
        await state.update_data(lessons_for="завтра")
        await PupilStates.rasp_yesterday.set()


@dp.message_handler(lambda m: m.text == "По дням", state=PupilStates.waiting_for_action, content_types=types.ContentType.TEXT)
async def rasp_today(message: types.Message, state: FSMContext):
    print("Запрос по дням, отправляю inline клавиатуру")
    await message.answer("Выберите день", reply_markup=pupil_rasp_by_days_kb)


@dp.callback_query_handler(lambda cq: cq.data in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"],
                           state=PupilStates.waiting_for_action,)
async def rasp_by_day_inline_handler(callback_query: types.CallbackQuery, state: FSMContext):
    print("пришел callback на расписание по дням")
    callback_data_text = {'monday': "понедельник", 'tuesday': "вторник", 'wednesday': "Среда",
                          'thursday': "четверг", 'friday': "пятница", 'saturday': "суббота", 'sunday': "воскресенье"}
    callback_data = callback_query.data
    user_data = await state.get_data()
    class_name = user_data['class_name']
    if 'other_class_name' in user_data:
        if user_data['other_class_name'] is not None:
            class_name = user_data['other_class_name']

    print(class_name, "запрос расписания на", user_data)
    lessons = "Нет уроков"
    print(class_name)
    if class_name is not None:
        print(callback_data)
        lessons = get_lessons_by_day(callback_data_text[callback_data], class_name)
        await PupilStates.waiting_for_action.set()
    else:
        await PupilStates.waiting_for_class_name.set()
        await bot.send_message(chat_id=callback_query.message.chat.id, text="Напомните номер класса, пожалуйста")
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, lessons)
    await state.update_data(other_class_name=None)
    print("удаляю клавиатуру")
    print(callback_query)
    # await bot.edit_message_reply_markup(chat_id=callback_query.message.chat.id,
    #                                     message_id=callback_query.message.message_id,
    #                                     reply_markup=ReplyKeyboardRemove)
    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)


@dp.message_handler(lambda m: m.text == "Для другого класса", state=PupilStates.waiting_for_action, content_types=types.ContentType.TEXT)
async def rasp_today(message: types.Message, state: FSMContext):
    print("запрос расписания для другого класса")
    await message.answer("Для какого класса вы хотите узнать расписание?")
    await PupilStates.waiting_for_other_class_name.set()


@dp.message_handler(state=PupilStates.waiting_for_other_class_name, content_types=types.ContentType.TEXT)
async def rasp_today(message: types.Message, state: FSMContext):
    print("Запрос для другого класса: ")
    other_class_name = message.text
    if not check_for_class(other_class_name):
        await message.reply("Не могу найти такого класса")
        await PupilStates.waiting_for_action.set()
        return
    await state.update_data(other_class_name=other_class_name)
    await message.answer("Расписание для " + other_class_name + "\nВыберите день недели",
                         reply_markup=pupil_rasp_by_days_kb)
    await PupilStates.waiting_for_action.set()


@dp.message_handler(state=PupilStates.rasp_today, content_types=types.ContentType.TEXT)  # на сегодня
async def rasp_today(message: types.Message, state: FSMContext):
    print("устаревшая функция \"на сегодня\"")
    rasp_lessons = get_lessons_for_today(message.text)
    await message.answer(rasp_lessons)
    await PupilStates.waiting_for_action.set()


@dp.message_handler(state=PupilStates.rasp_yesterday, content_types=types.ContentType.TEXT)  # на завтра
async def rasp_today(message: types.Message, state: FSMContext):
    # cur_state = await state.get_state()
    # print(cur_state)
    print("устаревшая функция \"на завтра\"")

    rasp_lessons = get_lessons_for_yesterday(message.text)
    await message.answer(rasp_lessons)
    await PupilStates.waiting_for_action.set()


@dp.message_handler(lambda m: m.text == "Расписание учителей", state=PupilStates.waiting_for_action)
async def rasp_yesterday(message: types.Message, state: FSMContext):
    print("Запрос расписания учителей")
    await message.reply("В базе данных пока нет информации об учителях")
