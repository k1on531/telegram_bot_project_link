import logging
import locale
import pytz
import datetime
import re
import asyncio
import json
import aiosqlite


from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher.webhook import SendMessage
from aiogram.utils.executor import start_webhook
from aiogram.types import ReplyKeyboardRemove


from keyboards.keyboard import keyboard_menu, \
    keyboard_rules, keyboard_rules_accept, keyboard_approve_reject, keyboard_cancel, keyboard_like_in, keyboard_start


API_KEY_TG = ''

storage = MemoryStorage()

bot = Bot(token=API_KEY_TG)
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())


locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
msk_tz = pytz.timezone('Europe/Moscow')


logging.basicConfig(level=logging.INFO)
# logging.basicConfig(level=logging.DEBUG)


USER_ADMINS = [
    
]


# webhook settings
WEBHOOK_HOST = 'https://cool-flies-fix-212-118-43-78.loca.lt'
WEBHOOK_PATH = '/bot/'
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# webserver settings
WEBAPP_HOST = 'localhost'  # or ip
WEBAPP_PORT = 80


class Form(StatesGroup):
    name = State()
    profile = State()
    link_count = State()
    waiting_for_link = State()
    waiting_for_interval = State()


async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)
    # insert code here to run it after start


async def on_shutdown(dp):
    logging.warning('Shutting down..')

    # insert code here to run it before shutdown
    # Remove webhook (not acceptable in some cases)
    await bot.delete_webhook()

    # Close DB connection (if used)
    await dp.storage.close()
    await dp.storage.wait_closed()

    logging.warning('Bye!')


@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    """
    СТАРТ И ПРАВИЛА
    """
    ReplyKeyboardRemove()
    video_file = types.InputFile('pictures/1.mp4')
    await bot.send_video(
        chat_id=message.chat.id,
        video=video_file,
        caption=f'Привет, {message.from_user.first_name} \n\n'
        'Выполняй простые задания каждый день и зарабатывай бонусы на свой баланс. \n\n'
        '<b>Играть нужно соблюдая правила.</b>',
        reply_markup=keyboard_rules,
        parse_mode='HTML'
    )


@dp.callback_query_handler(text='button1')
async def process_callback_button1(callback_query: types.CallbackQuery):
    """
    ОБРАБОТКА ПРИНЯТИЯ ПРАВИЛ
    """
    await callback_query.message.delete()
    await bot.send_message(
        callback_query.from_user.id,
        '<b>ПРАВИЛА</b> 📍\n '
        '1. Задания приходят с понедельника по пятницу. \n '
        '2. У каждого задания срок – 24 часа на выполнение. \n'
        'Если не успеть, то задание удалится, а новое придет на следующий день. \n'
        '3. Играть нужно честно и добросовестно выполнять все действия, которые написаны в задании. \n\n'
        '🚨 <b>Игра не по правилам</b> приведет первые два раза к потере бонусов, а на третий – к блокировке.',
        reply_markup=keyboard_rules_accept,
        parse_mode='HTML'
    )


@dp.callback_query_handler(text='button2')
async def process_callback_button2(callback_query: types.CallbackQuery):
    """
    СПРОСИМ ИМЯ
    """
    await bot.answer_callback_query(callback_query.id)
    await callback_query.message.delete()
    await bot.send_message(callback_query.from_user.id, '<b>Как тебя зовут?</b> \n\n Имя и Фамилия', parse_mode='HTML')
    await Form.name.set()


@dp.message_handler(state=Form.name)
async def process_name(message: types.Message, state: FSMContext):
    """
    ОБРАБОТКА СОХРАНЕНИЯ ИМЕНИ
    СПРОСИМ ССЫЛКУ (ПРОФИЛЬ)
    """
    async with state.proxy() as data:
        data['name'] = message.text

    await Form.next()
    await bot.send_message(
        message.chat.id,
        '<b>Укажи ссылку</b> на свой Dribbble профиль \n\n например \n – https://dribbble.com/pajasu',
        parse_mode='HTML',
        disable_web_page_preview=True
    )


@dp.message_handler(state=Form.profile)
async def process_link(message: types.Message, state: FSMContext):
    """
    СОХРАНИМ ССЫЛКУ (ПРОФИЛЬ)
    """
    if re.match(r'http(s)?://\S+', message.text):
        if message.text == '/start':
            await process_start_command(message)
        if message.text == '/admin':
            await process_admin_command(message)
        if message.text == '/menu':
            await start_menu(message)
        async with state.proxy() as data:
            data['profile'] = message.text

        # отправляем сообщение о том, что заявка принята
        await bot.send_message(message.chat.id, 'Заявка принята')
        # отправляем заявку администратору
        await send_application(message, state)
    else:
        # отправляем сообщение, что это не ссылка
        await message.reply('Извините, это не ссылка')
        await state.finish()


async def send_application(message: types.Message,  state: FSMContext):
    """
    ОТПРАВИМ ЗАЯВКУ АДМИНУ
    """
    if message.text == '/start':
        await process_start_command(message)
    if message.text == '/admin':
        await process_admin_command(message)
    if message.text == '/menu':
        await start_menu(message)
    async with state.proxy() as data:
        data['profile'] = message.text
    task_info = json.dumps({'execute': {}, 'from_me': {}}, ensure_ascii=False)
    async with state.proxy() as data:
        async with aiosqlite.connect('base.db') as db:
            cursor = await db.execute(
                """
                INSERT INTO person (uid, name, profile, status, task_info)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (uid)
                DO UPDATE SET name = excluded.name, 
                    profile = excluded.profile,
                    status = excluded.status;
                """,
                (message.chat.id, data['name'], data['profile'], 'in review', task_info)
            )
            await db.commit()
            ido = cursor.lastrowid
            if not ido:
                async with aiosqlite.connect('base.db') as db:
                    async with db.execute(
                            """
                            SELECT id FROM person WHERE uid = ?
                            """, (message.from_user.id,)) as cursor:
                        persons = await cursor.fetchall()
                        if persons:
                            ido = persons[0][0]
            data['ido'] = ido
        # Отправка сообщения администратору бота
        text = f"Поступила заявка #{ido}\n\nИмя: {data['name']}\n\nСсылка: {data['profile']}"
    for user in USER_ADMINS:
        await bot.send_message(user, text, reply_markup=keyboard_approve_reject, disable_web_page_preview=True)
    await dp.storage.set_data(chat=123, data=message.from_user.id)
    await state.finish()


@dp.message_handler(text=['Создать 🚀', 'Выполнить 💤', 'Правила 🎩', 'Профиль 🕶'])
async def process_callback_keyboard(message: types.Message,  state: FSMContext):
    if message.text == '/start':
        await process_start_command(message)
    if message.text == '/admin':
        await process_admin_command(message)
    if message.text == '/menu':
        await start_menu(message)
    async with aiosqlite.connect('base.db') as db:
        async with db.execute(
                """
                SELECT id FROM person WHERE uid = ?
                """, (message.from_user.id,)) as cursor:
            persons = await cursor.fetchall()
            if persons:
                ido = persons[0][0]
    await dp.storage.set_data(chat=1, data=ido)
    if message.text == 'Создать 🚀':
        await bot.send_message(
            chat_id=message.chat.id,
            text='<b>НОВОЕ ЗАДАНИЕ</b> 📣 \nУкажите ссылку для рассылки \n\n<b>например</b>\nhttps://google.com',
            parse_mode='HTML',
            disable_web_page_preview=True,
            reply_markup=keyboard_cancel
        )
        await Form.waiting_for_link.set()
    elif message.text == 'Выполнить 💤':
        async with aiosqlite.connect('base.db') as db:
            async with db.execute(
                """
                SELECT uid, task_info
                FROM person
                WHERE uid=?
                """, (message.from_user.id,)
            ) as cur:
                tasks_info = await cur.fetchall()
                uid_, info_ = tasks_info[0]
        info_json = json.loads(info_)
        if not info_json.get('execute'):
            await bot.send_message(message.chat.id, 'Новых заданий нет')
        else:
            month_names = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                           'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
            for link, date_ in info_json.get('execute').items():
                photo = types.InputFile('pictures/2.png')
                date = datetime.datetime.strptime(date_, '%Y-%m-%d %H:%M:%S.%f%z') + datetime.timedelta(minutes=40)
                formatted_date = date.strftime('%d {0} %H:%M').format(month_names[date.month - 1])
                await bot.send_photo(
                    chat_id=message.from_user.id,
                    caption=f'Вам нужно пролайкать\n{link}\n\nСрок до {formatted_date} по МСК',
                    photo=photo,
                    reply_markup=keyboard_like_in,
                    disable_notification=True
                )

    elif message.text == 'Правила 🎩':
        await bot.send_message(
            message.from_user.id,
            '<b>ПРАВИЛА</b> 📍\n '
            '1. Задания приходят с понедельника по пятницу. \n '
            '2. У каждого задания срок – 24 часа на выполнение. \n'
            'Если не успеть, то задание удалится, а новое придет на следующий день. \n'
            '3. Играть нужно честно и добросовестно выполнять все действия, которые написаны в задании. \n'
            '🚨 <b>Игра не по правилам</b> приведет первые два раза к потере бонусов, а на третий – к блокировке.',
            parse_mode='HTML'
        )
    elif message.text == 'Профиль 🕶':
        async with aiosqlite.connect('base.db') as db:
            query = await db.execute(
                """
                SELECT COALESCE(task_create, 0), COALESCE(task_complete, 0), COALESCE(task_ignored, 0)
                FROM person
                WHERE id=?
                """, (int(ido),)
            )
            row = await query.fetchone()
            if row:
                task_create, task_complete, task_ignored = row
        await bot.send_message(
            message.from_user.id,
            '<b>ЗАДАНИЯ</b> ❤ \n\n'
            f'Созданные: {task_create}\n'
            f'Выполненные: {task_complete}\n'
            f'Пропущенные: {task_ignored}',
            parse_mode='HTML'
        )


@dp.message_handler(state=Form.waiting_for_link)
async def save_link(message: types.Message,  state: FSMContext):
    async with aiosqlite.connect('base.db') as db:
        async with db.execute(
                """
                SELECT id, interval_, task_create, task_info FROM person WHERE uid = ?
                """, (message.from_user.id,)) as cursor:
            persons = await cursor.fetchall()
            if persons:
                ido, link_count, task_create, task_info_me = persons[0]
                task_create = 0 if not task_create else task_create
                data = json.loads(task_info_me)
                data['from_me'] = {message.text: str(datetime.datetime.now(msk_tz))}
                task_info_me = json.dumps(data, ensure_ascii=False)
    if re.match(r'http(s)?://\S+', message.text) and ido:
        async with aiosqlite.connect('base.db') as db:
            await db.execute(
                """
                UPDATE person
                SET task_create=?, task_info=?
                WHERE id = ?
                """, (task_create + 1, task_info_me, ido)
            )
            await db.commit()
        # ЗАПУСТИТЬ рассылку
        await bot.send_message(
            chat_id=message.chat.id,
            reply_markup=keyboard_start,
            text='Ссылка сохранена'
        )
    else:
        # отправляем сообщение, что это не ссылка
        await message.reply('Извините, это не ссылка')
    await state.finish()


@dp.callback_query_handler(lambda c: c.data == 'start_broadcast')
async def process_callback_start_broadcast(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Обработчик нажатия на инлайн-кнопку ЗАПУСТИТЬ
    """
    await callback_query.message.delete()
    # Получаем список пользователей, которым нужно отправить сообщения
    data = await state.get_data()
    ido = data.get('ido')
    if not ido:
        async with aiosqlite.connect('base.db') as db:
            async with db.execute(
                    """
                    SELECT id FROM person WHERE uid = ?
                    """, (callback_query.from_user.id,)) as cursor:
                persons = await cursor.fetchall()
                if persons:
                    ido = persons[0][0]
    async with aiosqlite.connect('base.db') as db:
        async with db.execute(
                """
                SELECT uid FROM person WHERE id NOT IN (?)
                """, (ido,)) as cursor:
            persons = await cursor.fetchall()
        async with db.execute(
                """
                SELECT task_info, interval_ FROM person WHERE id = ?
                """, (ido,)) as link1:
            links = await link1.fetchall()
    if links:
        link_info, interval = links[0]
    else:
        await bot.send_message(
            chat_id=callback_query.from_user.id,
            text='Рассылка не запущена, у вас отсутствует ссылка и интервал'
        )
    if persons and link_info:
        link_from_me = json.loads(link_info)
        # Удалим из бд протухшие задания
        new_link_from_me = {}
        for lin, date in link_from_me.get('from_me').items():
            now = datetime.datetime.now(msk_tz)
            date_ = datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S.%f%z')
            delta = now - date_
            if not delta.days:
                new_link_from_me[lin] = date
        # Запишем в бд
        if new_link_from_me:
            link_from_me['from_me'] = new_link_from_me
            async with aiosqlite.connect('base.db') as db:
                await db.execute(
                    """
                    UPDATE person
                    SET task_info=?
                    WHERE id=?
                    """, (json.dumps(link_from_me, ensure_ascii=False), ido)
                )
                await db.commit()
        # удамим клаву, чтобы обновить message id
        await bot.send_message(
            chat_id=callback_query.from_user.id,
            text='Рассылка запущена',
            reply_markup=ReplyKeyboardRemove()
        )
        # добавим клаву
        await start_menu(callback_query, state)
        month_names = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                       'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']

        for uid in persons:
            # Задаем интервал рассылки
            await asyncio.sleep(60*60/interval)
            for link, date_ in new_link_from_me.items():
                date = datetime.datetime.now(msk_tz) + datetime.timedelta(minutes=40)
                formatted_date = date.strftime('%d {0} %H:%M').format(month_names[date.month - 1])
                photo = types.InputFile('pictures/2.png')

                async with aiosqlite.connect('base.db') as db:
                    cur = await db.execute("SELECT uid, task_info FROM person WHERE uid = ?", uid)
                    tasks_info = await cur.fetchall()
                    _, task = tasks_info[0]
                    data = json.loads(task)
                    data['execute'][link] = str(datetime.datetime.now(msk_tz))
                    task = json.dumps(data, ensure_ascii=False)
                    await db.execute(
                        """
                        UPDATE person
                        SET task_info=?
                        WHERE uid=?
                        """, (task, uid[0])
                    )
                    await db.commit()
                await bot.send_photo(
                    chat_id=uid[0],
                    caption=f'Вам нужно пролайкать\n{link}\n\nСрок до {formatted_date} по МСК',
                    photo=photo,
                    reply_markup=keyboard_like_in,
                    disable_notification=True
                )
    else:
        await bot.send_message(chat_id=callback_query.from_user.id, text='Рассылка не запущена')


async def send_message(uid, link):
    await bot.send_message(chat_id=uid, text=link)


@dp.callback_query_handler(text='like_in')
async def process_callback_button2(callback_query: types.CallbackQuery):
    """
    ОБРАБОТЧИК КНОПКИ "Я ЛАЙКНУЛ"
    """
    await bot.answer_callback_query(callback_query.id)
    await callback_query.message.delete()
    async with aiosqlite.connect('base.db') as db:
        cur = await db.execute(
            """
            SELECT uid, task_info, task_complete, task_ignored FROM person WHERE uid=?
            """, tuple([callback_query.from_user.id])
        )
        task_info = await cur.fetchall()
        uid, info, task_complete, task_ignored = task_info[0]
        task_complete = 0 if not task_complete else task_complete
        task_ignored = 0 if not task_ignored else task_ignored
        match = re.search(r'(https?://\S+)', callback_query.message.caption)
        link = match.group(1)
        info = json.loads(info)
        exist_date = info.get('execute').get(link)
        date_format = datetime.datetime.strptime(exist_date, '%Y-%m-%d %H:%M:%S.%f%z') + datetime.timedelta(minutes=40)
        if datetime.datetime.now(msk_tz) > date_format:
            task_ignored += 1
            await bot.send_message(chat_id=callback_query.from_user.id, text='Вы не успели')
        else:
            task_complete += 1
            await bot.send_message(chat_id=callback_query.from_user.id, text='Спасибо, задание выполнено!')
        del info['execute'][link]
        async with aiosqlite.connect('base.db') as db:
            await db.execute(
                """
                UPDATE person
                SET task_info=?, task_complete=?, task_ignored=?
                WHERE uid=?
                """, (json.dumps(info, ensure_ascii=False), task_complete, task_ignored, uid)
            )
            await db.commit()


@dp.message_handler(commands=['menu'])
async def start_menu(callback_query: types.CallbackQuery,  state: FSMContext):
    """
    ВЫЗОВ МЕНЮ
    """
    async with aiosqlite.connect('base.db') as db:
        query = await db.execute(
            """
            SELECT status
            FROM person
            WHERE uid=?
            """, (int(callback_query.from_user.id),)
        )
        row = await query.fetchone()
        if row:
            status = row[0]
    if status != 'Player':
        await state.finish()
    await bot.send_message(callback_query.from_user.id, text='Выберите действие', reply_markup=keyboard_menu)


@dp.callback_query_handler(lambda c: c.data == 'exit', state=Form.waiting_for_link)
async def process_exit_link(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.delete()
    await state.finish()


@dp.callback_query_handler(text=['approve', 'reject'])
async def process_approval(callback_query: types.CallbackQuery):
    """
    ЗАЯВКА У АДМИНА (ОДОБРИТЬ/ОТКЛОНИТЬ)
    """
    prev_user_id = await dp.storage.get_data(chat=123)
    if callback_query.data == 'approve':

        async with aiosqlite.connect('base.db') as db:
            async with db.execute(
                    """
                    SELECT name, profile FROM person WHERE uid = ?
                    """, (prev_user_id,)) as cursor:
                persons = await cursor.fetchall()
                if persons:
                    name, profile = persons[0]
            async with db.execute(
                """
                SELECT interval_
                FROM person
                LIMIT 1
                """
            ) as interval_cursor:
                interval_ex = await interval_cursor.fetchall()
                if interval_ex:
                    interval_value = interval_ex[0][0] or 10

        for user in USER_ADMINS:
            await bot.send_message(
                user,
                f'Заявка пользователя {name} одобрена.\n'
                f'Ссылка на профиль: {profile}.\n',
                disable_web_page_preview=True
            )

        # запишем в бд  кол-во ссылок
        async with aiosqlite.connect('base.db') as db:
            await db.execute(
                """
                UPDATE person
                SET interval_=?, status=?
                WHERE uid =?
                """, (interval_value, 'Player', prev_user_id)
            )
            await db.commit()
        await bot.send_message(chat_id=prev_user_id, text='Ваша заявка одобрена', reply_markup=keyboard_menu)
    else:
        # отправляем сообщение пользователю с уведомлением об отклонении заявки
        await bot.send_message(prev_user_id, 'Заявка отклонена, попробуйте еще раз')
        # await state.finish()
    await callback_query.message.delete()


@dp.message_handler(commands=['admin'])
async def process_admin_command(message: types.Message):
    if message.from_user.id in USER_ADMINS:
        await Form.waiting_for_interval.set()
        await bot.send_message(message.chat.id, 'Задайте интервал рассылки')


@dp.message_handler(state=Form.waiting_for_interval)
async def process_admin_interval(message: types.Message, state: FSMContext):
    try:
        interval = int(message.text)
    except ValueError:
        await bot.send_message(message.chat.id, 'Ошибка! Введите целое число.')
        await state.finish()
        return
    async with aiosqlite.connect('base.db') as db:
        await db.execute(
            """
            UPDATE person
            SET interval_=?
            """, (interval,)
        )
        await db.commit()
    await state.finish()
    await bot.send_message(message.chat.id, 'Интервал сохранен')


if __name__ == '__main__':
    # executor.start_polling(dp, skip_updates=True)
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
