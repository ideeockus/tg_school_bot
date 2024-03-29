from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from aiogram.utils.markdown import bold, code, italic, text, escape_md
from bot_storage.bot_stats import edit_stat, inc_req_stat_by_class
from bot_storage import engine, Lessons, Roles

"""
A - 0 empty column
B - 1 class_name
C - 2 week_day
D -3 lesson_start_time
E -4 lesson_end_time
F - 5 subject_name
G - 6 room_number
"""

DbSession = sessionmaker(bind=engine)


def get_lessons_for_week_day(class_name: str, week_day: int, update_stats=True):
    if update_stats:
        edit_stat("get_rasp_total", 1)
        edit_stat("get_class_rasp", 1)
        inc_req_stat_by_class(class_name)

    rasp_session = DbSession()

    week_days_list = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    day_lessons = rasp_session.query(Lessons).filter(Lessons.class_name == class_name.upper(),
                                                     Lessons.week_day == week_days_list[week_day])  # выборка по бд
    day_lessons_text = ""
    for lsn in day_lessons:
        lesson_start = lsn.lesson_start_time[:-3]
        lesson_end = lsn.lesson_end_time[:-3]
        subject_name = lsn.subject_name or ""  # empty str if None
        room_number = lsn.room_number
        room_number = text("\n", "кабинет ", room_number) if room_number is not None else ""
        teacher_name = lsn.teacher_name
        teacher_name = f"\n{teacher_name}" if teacher_name is not None else ""
        day_lessons_text += text(bold(f"[{lesson_start} - {lesson_end}]"),
                                 bold(subject_name), escape_md(room_number), italic(teacher_name), "\n\n")
    if day_lessons_text == "":
        day_lessons_text = "Выходной\n"  # EDIT THIS LINE LATER
    day_lessons_text_result = f"Расписание для класса {str(class_name)}:\n\n"
    day_lessons_text_result += "📅 " + week_days_list[week_day] + "\n"
    day_lessons_text_result += day_lessons_text

    rasp_session.close()
    # return md_format(day_lessons_text_result)
    # return escape_md(day_lessons_text_result)
    return day_lessons_text_result


def get_lessons_for_today(class_name: str):
    current_week_day = datetime.now().weekday()
    return get_lessons_for_week_day(class_name, current_week_day)


def get_lessons_for_yesterday(class_name: str):
    next_week_day = (datetime.now() + timedelta(days=1)).weekday()
    return get_lessons_for_week_day(class_name, next_week_day)


def get_all_classes():
    classes_set = set()

    rasp_session = DbSession()

    classes = rasp_session.query(Lessons.class_name)  # выборка по бд
    for class_name in classes:
        classes_set.add(class_name.class_name)

    rasp_session.close()
    return classes_set


def check_for_class(class_name) -> bool:  # проверить наличие класса в бд
    classes_map = map(str.lower, get_all_classes())  # к нижнему регстру
    classes_set = set(classes_map)
    return class_name.lower() in classes_set  # True or False


def get_lessons_by_day(day: str, class_name: str):
    day = day.lower()
    print("__rasp_base", "поиск в базе расписания для", class_name, "на", day)
    if day == "сегодня":
        return get_lessons_for_today(class_name)
    if day == "завтра":
        return get_lessons_for_yesterday(class_name)

    week_days_list = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    if day.capitalize() in week_days_list:
        week_day_num = week_days_list.index(day.capitalize())
        return get_lessons_for_week_day(class_name, week_day_num)
    else:
        print("__rasp_base:", "такого дня нет в базе")


def get_all_teachers():
    teachers_set = set()

    rasp_session = DbSession()

    teachers = rasp_session.query(Lessons.teacher_name)  # выборка по бд
    for teacher_name in teachers:
        teacher_name = teacher_name.teacher_name
        if teacher_name is None or teacher_name == "":
            continue
        if teacher_name.find("/") >= 0:
            splitted_teacher_cell = teacher_name.split(" / ")
            for teacher_name_splitted in splitted_teacher_cell:
                teachers_set.add(teacher_name_splitted.strip().lower())
        else:
            teachers_set.add(teacher_name.lower())

    rasp_session.close()
    return teachers_set


def get_teacher_lessons_for_week_day(teacher: str, week_day: int, update_stats=True):
    if update_stats:
        edit_stat("get_rasp_total", 1)
        edit_stat("get_teacher_rasp", 1)

    rasp_session = DbSession()

    week_days_list = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    day_lessons = rasp_session.query(Lessons).filter(Lessons.teacher_name.ilike(f"%{teacher}%"),
                                                     Lessons.week_day == week_days_list[week_day])  # выборка по бд
    day_lessons_dict = {}
    for lsn in day_lessons:
        lesson_start = lsn.lesson_start_time[:-3]
        lesson_end = lsn.lesson_end_time[:-3]
        subject_name = lsn.subject_name
        teacher_name = lsn.teacher_name
        class_name = lsn.class_name
        room_number = lsn.room_number
        room_number = text(f"в кабинете ", bold(room_number)) if room_number is not None else ""
        day_lessons_dict[lesson_start] = text(bold(f"[{lesson_start} - {lesson_end}]"),
                                              italic(subject_name), "у", bold(class_name),
                                              room_number, "\n\n")
    if len(day_lessons_dict) == 0:
        day_lessons_dict['dayoff'] = "Выходной\n"
    day_lessons_text_result = f"Расписание для учителя {str(teacher)}:\n\n"
    day_lessons_text_result += "📅 " + week_days_list[week_day] + "\n"

    start_times = list(day_lessons_dict.keys())
    start_times.sort()
    for start_time in start_times:
        day_lessons_text_result += day_lessons_dict[start_time]

    rasp_session.close()
    # return md_format(day_lessons_text_result)
    # return escape_md(day_lessons_text_result)
    return day_lessons_text_result


def get_week_rasp_by_role(role: str, identifier: str):
    """
    :param role:
    :param identifier: teacher name or class name
    :return:
    """
    week_days_list = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    week_rasp = ""

    # учесть в статистике
    edit_stat("get_rasp_total", 1)
    if role == Roles.teacher.name:
        edit_stat("get_teacher_rasp", 1)
    elif role == Roles.pupil.name:
        edit_stat("get_class_rasp", 1)
        inc_req_stat_by_class(identifier)

    for day_num in range(len(week_days_list)):
        if role == Roles.teacher.name:
            day_rasp = get_teacher_lessons_for_week_day(identifier, day_num, False)
            week_rasp += day_rasp[day_rasp.index("\n"):]  # без первой строки
        elif role == Roles.pupil.name:
            day_rasp = get_lessons_for_week_day(identifier, day_num, False)
            week_rasp += day_rasp[day_rasp.index("\n"):]  # без первой строки
    return f"Расписание на неделю для {identifier}\n" + week_rasp
