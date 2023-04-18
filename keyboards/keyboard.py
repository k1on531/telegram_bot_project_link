from aiogram.types import KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from aiogram import types


keyboard_menu = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
create_button = KeyboardButton('Создать 🚀')
execute_button = KeyboardButton('Выполнить 💤')
rules_button = KeyboardButton('Правила 🎩')
profile_button = KeyboardButton('Профиль 🕶')
keyboard_menu.add(create_button, execute_button)
keyboard_menu.add(rules_button, profile_button)


keyboard_rules = types.InlineKeyboardMarkup()
button_rules = types.InlineKeyboardButton(text='🤘 Правила', callback_data='button1')
keyboard_rules.add(button_rules)


keyboard_rules_accept = types.InlineKeyboardMarkup()
button_rules_accept = types.InlineKeyboardButton(text='Я принимаю правила', callback_data='button2')
keyboard_rules_accept.add(button_rules_accept)


keyboard_approve_reject = InlineKeyboardMarkup()
approve_button = InlineKeyboardButton('Одобрить', callback_data='approve')
reject_button = InlineKeyboardButton('Отклонить', callback_data='reject')
keyboard_approve_reject.add(approve_button, reject_button)


keyboard_cancel = InlineKeyboardMarkup()
button_cancel = InlineKeyboardButton('Отменить', callback_data='exit')
keyboard_cancel.add(button_cancel)


keyboard_like_in = types.InlineKeyboardMarkup()
button_like_in = types.InlineKeyboardButton(text='Я лайкнул', callback_data='like_in')
keyboard_like_in.add(button_like_in)


keyboard_start = InlineKeyboardMarkup()
start_button = InlineKeyboardButton('ЗАПУСТИТЬ', callback_data='start_broadcast')
keyboard_start.add(start_button)
