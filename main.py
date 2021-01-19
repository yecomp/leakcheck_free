import time
import pickle
import json

import requests
import telebot
from telebot.types import ReplyKeyboardMarkup
from leakcheck import LeakCheckAPI

import config


class UserSetting:
    def __init__(self):
        self.users_info = {}
        self.api_key = config.API_KEY
        self.url = f'https://leakcheck.net/api/?key={self.api_key}'
        # Текущие лимиты: {'checks': 400, 'keyword': 45}
        self.limits = {}

    def load_info(self):
        try:
            with open('settings.pkl', 'rb') as f:
                info = pickle.load(f)
            if info and isinstance(info, dict):
                self.users_info = info
            else:
                raise ValueError
        except:
            pass

    def save_info(self):
        try:
            if self.users_info:
                with open('settings.pkl', 'wb') as f:
                    pickle.dump(self.users_info, f)
        except:
            pass

    def upd_limits(self):
        try:
            api = LeakCheckAPI()
            api.set_key(config.API_KEY)
            limits = api.getLimits()
            if limits and isinstance(limits, dict):
                self.limits = limits
            else:
                raise ValueError
            return True
        except:
            pass

    def status(self, tid, new_status):
        try:
            if not self.users_info.get(tid):
                self.users_info[tid] = {}
            self.users_info[tid]["status"] = new_status
        except:
            pass


bot = telebot.TeleBot(config.TG_TOKEN)
user = UserSetting()


kb_main = ReplyKeyboardMarkup(True)
kb_main.row('📧 E-mail', '🕹 Логин', '💎 Лимиты')
kb_main.row('📨 E-mail по ключевому слову (keyword@*.*)')
kb_main.row('📱 Телефон [СНГ]', '🌎 Minecraft')

kb_cancel = ReplyKeyboardMarkup(True)
kb_cancel.row('🔙 Отмена')


@bot.message_handler(commands=['start'])
def start_message(message):
    try:
        tid = message.chat.id
        user.upd_limits()
        checks, keyword = user.limits.values()
        text_message = f"Привет! В этом боте доступен функционал сайта *leakcheck*, но полностью *бесплатно*!\n\n" + \
            f"Осталось на сегодня:\nПроверок: `{checks}`\nПо ключу: `{keyword}`\n\nРазработчик: {config.ADMIN_TG}"
        bot.send_message(tid, text_message, parse_mode='markdown', reply_markup=kb_main)
        user.status(tid, "start")
    except:
        pass


@bot.message_handler(content_types=["text"])
def main_sender(message):
    tid = message.chat.id
    txt = message.text
    if txt == '🔙 Отмена':
        user.status(tid, "start")
        bot.send_message(tid, 'Возвращаюсь обратно.', reply_markup=kb_main)
    elif txt == '💎 Лимиты':
        user.upd_limits()
        checks, keyword = user.limits.values()
        text_message = f"Осталось на сегодня:\nПроверок: `{checks}`\nПо ключу: `{keyword}`"
        bot.send_message(tid, text_message, parse_mode='markdown', reply_markup=kb_main)
    elif config.CHECK_TYPES.get(txt):
        # Получаем тип проверки.
        user.status(tid, 'to_check')
        user.users_info[tid]["type"] = config.CHECK_TYPES[txt]
        bot.send_message(tid, 'Введите данные для проверки:', reply_markup=kb_cancel)
    elif user.users_info.get(tid, {}).get("status") == "to_check":
        try:
            user_type = user.users_info[tid]["type"]
            # Получаем результаты проверки.
            result = requests.get(user.url + f'&type={user_type}&check={txt}').json()
            if result["success"]:

                count = result["found"]
                raw_count = count
                result_chars = 0
                lines = []
                real_count = 0

                for x in result["result"]:
                    result_chars += len(x["line"])
                    if result_chars <= 3500:
                        lines.append(f'<code>{x["line"]}</code>')
                        real_count += 1
                    else:
                        count = str(count) + f' (отображено: {real_count})'
                        raw_count = str(raw_count) + f' ({real_count})'
                        break

                lines = '\n'.join(lines)

                if count and lines:
                    result_text = f'Найдено: <code>{count}</code>\nСтроки:\n{lines}'
                    bot.send_message(tid, result_text, parse_mode='html', reply_markup=kb_main)
                else:
                    bot.send_message(tid, f"⚠️ Внимание - ничего не найдено!", reply_markup=kb_main)
            else:
                error_desc = result["error"]
                if error_desc == "Not found":
                    bot.send_message(tid, f"⚠️ Внимание - ничего не найдено!", reply_markup=kb_main)
                else:
                    bot.send_message(tid, f"❌ Ошибка при проверке:\n`{error_desc}`\n\nОбратитесь к админу: *{config.ADMIN_TG}*", parse_mode='markdown', reply_markup=kb_main)
        except:
            bot.send_message(tid, f"❌ Ошибка - не удалось проверить данные!\n\nОбратитесь к админу: *{config.ADMIN_TG}*", parse_mode='markdown', reply_markup=kb_main)
        user.status(tid, "start")
    else:
        bot.send_message(tid, f"❌ Ошибка - не удалось распознать действие!\n\nОбратитесь к админу: *{config.ADMIN_TG}*", parse_mode='markdown', reply_markup=kb_main)
    user.save_info()

if __name__ == "__main__":
    try:
        if user.upd_limits():
            print('[~] Запускаю бота... Можешь писать боту в Telegram!')
            bot.polling(none_stop=True, interval=0)
        else:
            raise ValueError
    except Exception as e:
        print('[x] Бот крашнулся :c')
        print(f'[i] Info: {e}')
    print()
