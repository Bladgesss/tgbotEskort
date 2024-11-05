import telebot
from telebot import types
import json
import os
import random
from datetime import datetime, timedelta
from models_data import models_data
import threading
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import sys



class ReloadHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            print(f'Изменение в файле: {event.src_path}. Перезапускаем бота...')
            os.execl(sys.executable, sys.executable, *sys.argv)  # Перезапуск текущего процесса


def start_bot():

    API_TOKEN = '7730145071:AAF1fXgLmJPPvEHHl6jmKbI3ZmGl-q9xrhg'
    bot = telebot.TeleBot(API_TOKEN)
    user_data_file = 'user_data.json'


    banks_data = {
        'sberbank': {
            'owner': 'Савченко Маргарита Николаевна',
            'card_number': '2200280414795189',
            'active': False,
        },
        't_bank': {
            'owner': 'Иванов Иван Иванович',
            'card_number': '1234567890123456',
            'active': False,
        },
        'alfabank': {
            'owner': 'Петрова Анна Васильевна',
            'card_number': '9876543210987654',
            'active': False,
        },
        'ozon': {
            'owner': 'Андрей Морозов',
            'card_number': '2204320335878858',
            'active': True,
        },
    }

    cities = [
        "Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Нижний Новгород",
        "Казань", "Челябинск", "Омск", "Самара", "Ростов-на-Дону",
        "Уфа", "Красноярск", "Воронеж", "Пермь", "Волгоград",
        "Тюмень", "Ижевск", "Барнаул", "Благовещенск", "Ставрополь",
        "Архангельск", "Калуга", "Чебоксары", "Тула", "Ярославль",
        "Саранск", "Набережные Челны", "Кемерово", "Сочи"
    ]
    time_options = {
        '1': "Час - 4100₽",
        '2': "2 часа - 7925₽",
        'night': "Ночь - 16400₽"
    }


    if os.path.exists(user_data_file):
        with open(user_data_file, 'r', encoding='utf-8') as f:
            user_data = json.load(f)
    else:
        user_data = {}

    def save_data():
        with open(user_data_file, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=4)



    def periodic_message():
        while True:
            time.sleep(32400)  # Интервал в секундах (например, 9 часов)
            for user_id in user_data.keys():  # Проходим по всем пользователям
                bot.send_message(user_id, "Тебе грустно и одиноко ? ☹️\nУстал и хочешь отдохнуть ? 😤\nСкорее заказывай наших моделей, они могут творить безумные вещи. 🥵")

    threading.Thread(target=periodic_message, daemon=True).start()


    city_models = {city: {'models': models, 'count': 0, 'last_update': None} for city, models in models_data.items()}

    def get_models_count_for_city(city):
        if city not in city_models:
            return 0

        now = datetime.now()

        if city_models[city]['last_update'] is None or now - city_models[city]['last_update'] > timedelta(hours=3):
            city_models[city]['count'] = random.randint(5, min(len(city_models[city]['models']), 15))
            city_models[city]['last_update'] = now

        return city_models[city]['count']

    def get_random_models(city):
        # Проверяем, существует ли город в city_models
        if city not in city_models:
            print(f"Город '{city}' не найден в city_models.")
            return []

        available_models = city_models[city]['models']
        count = get_models_count_for_city(city)

        # Убедимся, что count не превышает количество доступных моделей
        if count > len(available_models):
            count = len(available_models)

        # Возвращаем случайные модели, если есть доступные
        return random.sample(available_models, count) if count > 0 else []

    def create_model_profile(model, photo_number=1):
        name = model['name']
        age = model['age']
        photo_path = model['photo'] if photo_number == 1 else model.get('photo2')
        description = model['description']

        # Создание клавиатуры
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Оформить", callback_data=f"order_{name}"))
        markup.add(types.InlineKeyboardButton("Забронировать", callback_data=f"reserve_{name}"))
        markup.add(types.InlineKeyboardButton("Другое фото", callback_data=f"other_photo_{name}_{photo_number}"))
        return f"👤 {name}, {age} лет\n\n{description}", photo_path, markup

    @bot.callback_query_handler(func=lambda call: call.data.startswith('other_photo_'))
    def switch_photo(call):
        parts = call.data.split('_')
        model_name = parts[2]  # Извлекаем имя модели
        current_photo_number = int(parts[3])  # Текущий номер фото

        # Определяем следующее фото (1 или 2)
        new_photo_number = 2 if current_photo_number == 1 else 1

        # Находим город и модель
        city = user_data[str(call.message.chat.id)]['city']
        model = next((m for m in models_data[city] if m['name'] == model_name), None)

        if model:
            profile_text, photo_path, markup = create_model_profile(model, new_photo_number)

            # Удаляем предыдущее сообщение
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception as e:
                print(f"Ошибка при удалении сообщения: {e}")

            # Проверяем существование файла
            if photo_path and os.path.exists(photo_path):
                with open(photo_path, 'rb') as photo:
                    bot.send_photo(call.message.chat.id, photo, caption=profile_text, reply_markup=markup)
            else:
                bot.send_message(call.message.chat.id, "Фото модели не найдено.")
        else:
            bot.send_message(call.message.chat.id, "Модель не найдена.")

    def send_model_profile(call):
        model_name = call.data.split('_')[1]  # Извлекаем имя модели из callback_data
        model = None

        for city, models in models_data.items():
            for m in models:
                if m['name'] == model_name:
                    model = m
                    break
            if model:
                break

        if model:
            profile_text, photo_path, markup = create_model_profile(model)

            # Проверяем, существует ли файл
            print(f"Путь к фото: {photo_path}")
            if os.path.exists(photo_path):
                try:
                    with open(photo_path, 'rb') as photo:  # Открываем файл
                        bot.send_photo(call.message.chat.id, photo, caption=profile_text, reply_markup=markup)
                except Exception as e:
                    print(f"Ошибка при отправке фото: {e}")
                    bot.send_message(call.message.chat.id, f"Ошибка при отправке фото: {e}")
            else:
                bot.send_message(call.message.chat.id, "Фото модели не найдено.")
        else:
            bot.send_message(call.message.chat.id, "Модель не найдена.")

    @bot.message_handler(commands=['start'])
    def start(message):
        user_id = str(message.chat.id)
        city = user_data[user_id]['city']
        models = get_models_for_city(city)  # Получаем модели для текущего города
        models_count = len(models)
        if user_id not in user_data:
            user_data[user_id] = {'rating': 5, 'city': None, 'currency': None}
            bot.send_message(message.chat.id, "Привет! Пожалуйста, введи свой город без ошибок.")
        else:
            models_count = 0  # Значение по умолчанию

            # Проверяем, если город задан, и получаем количество моделей
            if city:
                models_count = get_models_count_for_city(city)
            bot.send_message(message.chat.id, "Добро пожаловать обратно!")
            profile_info = (
                f"👤Профиль:\n\n"
                f"❕Ваш ID - : {user_id}\n\n"
                f"🏙 Текущий город - {user_data[user_id]['city']}\n\n"
                f"Рейтинг: {user_data[user_id]['rating']} ⭐️\n"
                f"Валюта: {user_data[user_id]['currency']}\n"
                f"Свободных моделей - {models_count}\n"  # Выводим количество моделей
            )

            action_markup = types.InlineKeyboardMarkup()
            action_markup.add(types.InlineKeyboardButton("Мои заказы", callback_data="my_orders"))
            # action_markup.add(types.InlineKeyboardButton("Смена валюты", callback_data="change_currency"))
            # action_markup.add(types.InlineKeyboardButton("Смена города", callback_data="change_city"))

            bot.send_message(message.chat.id, profile_info, reply_markup=action_markup)

            reply_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            btn1 = types.KeyboardButton("❤️‍🔥Модели")
            btn2 = types.KeyboardButton("👤Профиль")
            info = types.KeyboardButton("🔍Информация")
            tech = types.KeyboardButton("🧑‍💻Техническая поддержка")
            reply_markup.add(btn1, btn2, info, tech)

            bot.send_message(message.chat.id, "Выберите действие:", reply_markup=reply_markup)

    @bot.message_handler(func=lambda message: user_data.get(str(message.chat.id), {}).get('city') is None)
    def set_city(message):
        user_id = str(message.chat.id)

        city = message.text
        if city in cities:
            user_data[user_id]['city'] = city
            save_data()  
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🇷🇺RUB", callback_data="currency_RUB"))
            markup.add(types.InlineKeyboardButton("🇰🇿KZT", callback_data="currency_KZT"))

            bot.send_message(
                message.chat.id,
                f"Город {city} сохранен. Выбери валюту:",
                reply_markup=markup
            )
        else:
            bot.send_message(message.chat.id, "В данном городе нет наших услуг. Пожалуйста, введи еще раз:")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('currency_'))
    def currency_choice(call):
        user_id = str(call.message.chat.id)
        currency = call.data.split('_')[1].upper()
        user_data[user_id]['currency'] = currency
        save_data()

        bot.answer_callback_query(call.id, f"Выбрана валюта: {currency}")

        city = user_data[user_id].get('city')  # Получаем текущий город

        models_count = 0  # Значение по умолчанию

        # Проверяем, если город задан, и получаем количество моделей
        if city:
            models_count = get_models_count_for_city(city)  # Получаем количество моделей для города

        profile_info = (
            f"👤Профиль:\n\n"
            f"❕Ваш ID - : {user_id}\n\n"
            f"🏙 Текущий город - {city if city else 'не указан'}\n\n"
            f"Рейтинг: {user_data[user_id]['rating']} ⭐️\n"
            f"Валюта: {user_data[user_id]['currency']}\n"
            f"Свободных моделей - {models_count}\n"  # Теперь models_count всегда определено
        )

        action_markup = types.InlineKeyboardMarkup()
        action_markup.add(types.InlineKeyboardButton("Мои заказы", callback_data="my_orders"))
        # action_markup.add(types.InlineKeyboardButton("Смена валюты", callback_data="change_currency"))
        # action_markup.add(types.InlineKeyboardButton("Смена города", callback_data="change_city"))

        bot.send_message(call.message.chat.id, profile_info, reply_markup=action_markup)

        reply_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("❤️‍🔥Модели")
        btn2 = types.KeyboardButton("👤Профиль")
        info = types.KeyboardButton("🔍Информация")
        tech = types.KeyboardButton("🧑‍💻Техническая поддержка")
        reply_markup.add(btn1, btn2, info, tech)

        bot.send_message(call.message.chat.id, "Выберите действие:", reply_markup=reply_markup)

    def get_models_for_city(city):
        if city in models_data:
            models = models_data[city]
            random.shuffle(models)  # Перемешиваем модели, если нужно
            return models
        return []

    @bot.message_handler(content_types=['text'])
    def func(message):
        user_id = str(message.chat.id)

        if user_id in user_data and user_data[user_id].get('city'):
            if user_data[user_id].get('reserving'):
                # Вызываем обработчик для бронирования
                handle_text_message(message)
                return

        if user_id in user_data and user_data[user_id]['city']:
            if message.text == "❤️‍🔥Модели":
                city = user_data[user_id]['city']
                models = get_random_models(city)  # Получаем случайные модели
                models_count = len(models)
                
                if models_count > 0:
                    response_text = f"В городе {city} найдено {models_count} моделей:\n"
                    markup = types.InlineKeyboardMarkup()
                    
                    for index, model in enumerate(models):
                        model_info = f"#{index + 1} | {model['name']} | {model['age']} лет"
                        markup.add(types.InlineKeyboardButton(model_info, callback_data=f"model_{model['name']}"))
                    
                    bot.send_message(message.chat.id, response_text, reply_markup=markup)
                else:
                    bot.send_message(message.chat.id, "В данном городе нет доступных моделей.")
            
            elif message.text == "👤Профиль":
                # Получаем актуальное количество моделей каждый раз
                city = user_data[user_id]['city']
                models_count = get_models_count_for_city(city)  # Получаем количество моделей для города

                profile_info = (
                    f"👤Профиль:\n\n"
                    f"❕Ваш ID: {user_id}\n\n"
                    f"🏙Текущий город - {city}\n\n"
                    f"Рейтинг: {user_data[user_id]['rating']} ⭐️\n"
                    f"Валюта: {user_data[user_id]['currency']}\n"
                    f"Свободных моделей - {models_count}\n"
                )
                action_markup = types.InlineKeyboardMarkup()
                action_markup.add(types.InlineKeyboardButton("Мои заказы", callback_data="my_orders"))

                bot.send_message(message.chat.id, profile_info, reply_markup=action_markup)
            elif message.text == "🔍Информация":
                bot.send_message(message.chat.id, "🔍 Информация\n\nДорогие пользователи,\n\nХотелось бы поделиться информацией о нашем проекте, который разработан для обеспечения быстрого и комфортного поиска. Теперь вам больше не потребуется затрачивать значительное количество времени и усилий на поиск идеального способа провести досуг.\n\nМы создали структуру нашего сервиса с учетом удобства для каждого пользователя. Это позволяет сделать выбор быстрее и более простым, убирая лишние сложности.\n\nПочему бы вам не избежать дополнительных трудностей в поисках удовольствия?\n\nОсобое внимание следует уделить тому, что мы придерживаемся политики полной анонимности для наших клиентов и не требуем предоставления персональных данных.\n\nС уважением,\nКоманда технической поддержки вашего эскорт агентства")
            elif message.text == "🧑‍💻Техническая поддержка":
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("Написать", url="https://t.me/support"))
                bot.send_message(message.chat.id, "Техническая поддержка эскорт-агентства всегда готова помочь в случае возникновения любых технических проблем. Обращайтесь в неё, если у вас возникли трудности с доступом к платформе, проблемы с оплатой услуг, вопросы по функциональности бота.\n\n Чтобы получить качественную помощь, соблюдайте следующие правила:\n1. При описании проблемы будьте максимально информативны. Укажите детали, ошибки, которые привели к проблеме.\n2. Соблюдайте уважительное и корректное общение с сотрудниками поддержки.\n3. Если проблема касается конфиденциальной информации, не раскрывайте личные данные в открытой переписке.\n\nСроки ответа технической поддержки колеблются:\n- Первый уровень (10 минут): Быстрые ответы на общие вопросы и проблемы, которые могут быть решены быстро.\n- Второй уровень (30 минут - 1 час): Сложные проблемы, требующие более глубокого анализа и решения.\n\nОбращение в техническую поддержку позволит вам оперативно решить возникшие технические сложности и продолжить пользоваться услугами эскорт-агентства без перебоев.", reply_markup=markup)
        else:
            # Если профиль еще не заполнен
            bot.send_message(message.chat.id, "Сначала выберите город и валюту.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('model_'))
    def model_profile(call):
        model_name = call.data.split('_')[1]
        city = user_data[str(call.message.chat.id)]['city']
        
        # Найти модель по имени в данных для города
        model = next((m for m in models_data[city] if m['name'] == model_name), None)

        if model:
            profile_text, photo_path, markup = create_model_profile(model)

            # Проверка существования файла
            if os.path.exists(photo_path):
                try:
                    with open(photo_path, 'rb') as photo:
                        bot.send_photo(call.message.chat.id, photo, caption=profile_text, reply_markup=markup)
                except Exception as e:
                    print(f"Ошибка при отправке фото: {e}")
                    bot.send_message(call.message.chat.id, "Ошибка при отправке фото.")
            else:
                bot.send_message(call.message.chat.id, "Фото модели не найдено.")
        else:
            bot.send_message(call.message.chat.id, "Модель не найдена.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('order_'))
    def order_model(call):
        model_name = call.data.split('_')[1]
        city = user_data[str(call.message.chat.id)]['city']
        
        # Найти модель по имени
        model = next((m for m in models_data[city] if m['name'] == model_name), None)

        if model:
            # Сначала удаляем предыдущее сообщение
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception as e:
                print(f"Ошибка при удалении сообщения: {e}")

            # Отправляем фото модели с текстом и кнопками
            photo_path = model['photo']  # Получаем путь к фото напрямую
            if os.path.exists(photo_path):
                with open(photo_path, 'rb') as photo:
                    # Создаем клавиатуру с кнопками
                    time_markup = types.InlineKeyboardMarkup()
                    time_markup.add(types.InlineKeyboardButton("🏞Час - 4100₽", callback_data=f'time_1_{model["name"]}'),
                                    types.InlineKeyboardButton("🌄2 часа - 7925₽", callback_data=f'time_2_{model["name"]}'),
                                    types.InlineKeyboardButton("🌃Ночь - 16400₽", callback_data=f'time_night_{model["name"]}'),
                                    types.InlineKeyboardButton("⬅️Назад", callback_data=f"back_to_model_{model['name']}"))
                    
                    # Отправляем фото с текстом и клавиатурой
                    bot.send_photo(call.message.chat.id, photo, caption="Выберите время на которое вы хотите оформить модель:", reply_markup=time_markup)
            else:
                bot.send_message(call.message.chat.id, "Фото модели не найдено.")
        else:
            bot.send_message(call.message.chat.id, "Модель не найдена.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('back_to_model_'))
    def back_to_model(call):
        parts = call.data.split('_')
        model_name = parts[3] if len(parts) > 3 else None  # Извлекаем имя модели
        city = user_data[str(call.message.chat.id)]['city']
        
        # Найти модель по имени
        model = next((m for m in models_data[city] if m['name'] == model_name), None)

        if model:
            profile_text, photo_path, markup = create_model_profile(model)

            if os.path.exists(photo_path):
                with open(photo_path, 'rb') as photo:
                    bot.send_photo(call.message.chat.id, photo, caption=profile_text, reply_markup=markup)
            else:
                bot.send_message(call.message.chat.id, "Фото модели не найдено.")
        else:
            print(f"Модель '{model_name}' не найдена.")  # Логирование для отладки
            bot.send_message(call.message.chat.id, "Модель не найдена.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('time_'))
    def choose_time(call):
        parts = call.data.split('_')
        time_key = parts[1]  # Это '1', '2' или 'night'
        model_name = '_'.join(parts[2:])  # Извлекаем имя модели
        city = user_data[str(call.message.chat.id)]['city']

        # Найти модель по имени
        model = next((m for m in models_data[city] if m['name'] == model_name), None)

        if model:
            # Удаляем предыдущее сообщение
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except Exception as e:
                print(f"Ошибка при удалении сообщения: {e}")

            # Отправляем фото модели с выбранным тарифом и кнопками
            photo_path = model['photo']
            if os.path.exists(photo_path):
                with open(photo_path, 'rb') as photo:
                    # Создаем клавиатуру с кнопками для оплаты
                    payment_markup = types.InlineKeyboardMarkup()
                    payment_markup.add(types.InlineKeyboardButton("Карта", callback_data='payment_card'))
                    payment_markup.add(types.InlineKeyboardButton("Оплата наличными", callback_data='payment_cash'))
                    payment_markup.add(types.InlineKeyboardButton("⬅️Назад", callback_data=f"back_to_model_{model['name']}"))

                    # Получаем текст тарифа
                    tariff_text = time_options.get(time_key, "Неизвестный тариф")
                    caption_text = f"Вы выбрали - {model['name']} - {tariff_text}\n\nВыберите способ оплаты:"
                    bot.send_photo(call.message.chat.id, photo, caption=caption_text, reply_markup=payment_markup)
            else:
                bot.send_message(call.message.chat.id, "Фото модели не найдено.")
        else:
            bot.send_message(call.message.chat.id, "Модель не найдена.")
            
    @bot.callback_query_handler(func=lambda call: call.data == 'payment_cash')
    def handle_cash_payment(call):
        # Ответ на нажатие кнопки "Оплата наличными"
        bot.send_message(
            call.message.chat.id, 
            "⚠️Оплата наличными доступна только после подтверждения первого заказа в мерах безопасности!"
        )

    @bot.callback_query_handler(func=lambda call: call.data == 'payment_card')
    def choose_payment_bank(call):
        # Удаляем предыдущее сообщение
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception as e:
            print(f"Ошибка при удалении сообщения: {e}")

        # Извлекаем данные о модели и тарифе из текста предыдущего сообщения
        parts = call.message.caption.split("\n")
        
        # Проверяем, что у нас есть как минимум одна строка
        if len(parts) < 1:
            bot.send_message(call.message.chat.id, "Ошибка: недоступна информация о модели или тарифе.")
            return

        # Извлечение имени модели и тарифа
        model_info = parts[0].strip()
        if " - " in model_info:
            model_name, tariff_text = model_info.rsplit(" - ", 1)  # Разбиваем с конца на две части
        else:
            model_name = model_info
            tariff_text = "Неизвестный тариф"  # Если нет тарифа

        # Убираем лишние пробелы
        model_name = model_name.strip()
        tariff_text = tariff_text.strip()

        city = user_data[str(call.message.chat.id)]['city']

        # Найти модель по имени
        model = next((m for m in models_data[city] if m['name'] in model_name), None)

        if model:
            # Отправляем фото модели с текстом и кнопками для выбора банка
            photo_path = model['photo']
            if os.path.exists(photo_path):
                with open(photo_path, 'rb') as photo:
                    # Создаем клавиатуру с кнопками для банков
                    bank_markup = types.InlineKeyboardMarkup()
                    bank_markup.add(types.InlineKeyboardButton("Сбербанк", callback_data='bank_sberbank'))
                    bank_markup.add(types.InlineKeyboardButton("Т-Банк", callback_data='bank_t_bank'))
                    bank_markup.add(types.InlineKeyboardButton("Альфабанк", callback_data='bank_alfabank'))
                    bank_markup.add(types.InlineKeyboardButton("Озон", callback_data='bank_ozon'))
                    bank_markup.add(types.InlineKeyboardButton("⬅️Назад", callback_data=f"back_to_model_{model['name']}"))

                    caption_text = f"Выберите банк, с которого осуществляется пополнение:\n\n{tariff_text}"
                    bot.send_photo(call.message.chat.id, photo, caption=caption_text, reply_markup=bank_markup)
            else:
                bot.send_message(call.message.chat.id, "Фото модели не найдено.")
        else:
            bot.send_message(call.message.chat.id, "Модель не найдена.")


    @bot.callback_query_handler(func=lambda call: call.data.startswith('bank_'))
    def handle_bank_selection(call):
        bank_name = call.data.split('_')[1]  # Извлекаем имя банка
        city = user_data[str(call.message.chat.id)]['city']
        model_info = call.message.caption.split("\n")

        if len(model_info) < 1:
            bot.send_message(call.message.chat.id, "Ошибка: недоступна информация о модели или тарифе.")
            return

        amount = "9400₽"  # Здесь можно заменить на получение суммы из данных
        model_name = model_info[0].strip()

        # Получаем данные о выбранном банке
        bank_info = banks_data.get(bank_name)

        if bank_info and bank_info['active']:
            # Формируем сообщение для оплаты
            payment_message = (
                "♻️ Оплата банковской картой:\n\n"
                f"Сумма: {amount}\n\n"
                "◽️ Реквизиты для оплаты банковской картой:\n"
                f"┣ {bank_info['owner']}\n"
                f"┣ {bank_name.capitalize()}\n"
                f"┗ {bank_info['card_number']}\n\n"
                "⚠️ Счет действителен 15 минут!\n"
                "⚠️ ВАЖНО! Обязательно после пополнения, отправьте скриншот или чек оплаты в чат с ботом.\n"
                "⚠️ Оплата заказа принимается строго через бота."
            )
            bot.send_message(call.message.chat.id, payment_message)
        else:
            bot.send_message(call.message.chat.id, "⚠️На данный момент данный банк недоступен.")
            
    @bot.message_handler(content_types=['photo', 'document'])
    def handle_payment_proof(message):
        # Пересылаем фото или документ себе в личку
        chat_id = message.chat.id
        user_id = message.from_user.id

        # Если это фото
        if message.content_type == 'photo':
            # Отправляем последнее фото (оно в списке photos)
            file_id = message.photo[-1].file_id

            # Получаем файл
            file_info = bot.get_file(file_id)

            # Отправляем фото себе в личку
            bot.send_photo(
                chat_id=7411578535,  # Ваш Telegram ID (замените на ваш ID)
                photo=file_info.file_id,
                caption=f"Чек от пользователя {message.from_user.username} (ID: {user_id})"
            )

        # Если это документ
        elif message.content_type == 'document':
            # Получаем file_id документа
            file_id = message.document.file_id

            # Получаем файл
            file_info = bot.get_file(file_id)

            # Отправляем документ себе в личку
            bot.send_document(
                chat_id=7411578535,  # Ваш Telegram ID (замените на ваш ID)
                document=file_info.file_id,
                caption=f"Чек от пользователя {message.from_user.username} (ID: {user_id})"
            )

        # Ответ пользователю
        bot.send_message(chat_id, "Чек отправлен. Спасибо! Ожидайте связи з модератором.")


    @bot.callback_query_handler(func=lambda call: call.data.startswith('reserve_'))
    def reserve_model(call):
        user_id = str(call.message.chat.id)
        model_name = call.data.split('_')[1]

        if user_id not in user_data:
            user_data[user_id] = {
                'city': "Москва",
                'rating': 5,
                'currency': "RUB",
                'reserving': False,
                'model_name': None
            }

        user_data[user_id]['reserving'] = True
        user_data[user_id]['model_name'] = model_name
        save_data()

        # Сообщение с просьбой уточнить детали
        reservation_message = (
            "Уточните пожалуйста следующие детали брони:\n"
            "- Дата и время встречи;\n"
            "- Место встречи (адрес, где состоится встреча, у Вас или у модели);\n"
            "- Контактные данные для связи с вами (Ваш номер телефона или Telegram)"
        )

        # Кнопка "Отмена"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌Отмена", callback_data=f"cancel_reserve_{model_name}"))
        
        # Отправляем сообщение с деталями и кнопками
        message_sent = bot.send_message(call.message.chat.id, reservation_message, reply_markup=markup)
        user_data[user_id]['reservation_message_id'] = message_sent.message_id


    @bot.callback_query_handler(func=lambda call: call.data == "cancel_reservation")
    def cancel_reservation(call):
        user_id = str(call.message.chat.id)
        
        if user_id not in user_data or not user_data[user_id].get('reserving'):
            bot.send_message(call.message.chat.id, "Вы не находитесь в процессе бронирования.")
            return
        
        model_name = user_data[user_id].get('model_name')
        city = user_data[user_id].get('city')

        # Найти модель по имени
        model = next((m for m in models_data[city] if m['name'] == model_name), None)

        if model:
            profile_text, photo_path, markup = create_model_profile(model)

            if os.path.exists(photo_path):
                with open(photo_path, 'rb') as photo:
                    bot.send_photo(call.message.chat.id, photo, caption=profile_text, reply_markup=markup)
            else:
                bot.send_message(call.message.chat.id, "Фото модели не найдено.")
        else:
            bot.send_message(call.message.chat.id, "Модель не найдена.")

        # Сброс состояния бронирования
        user_data[user_id]['reserving'] = False
        user_data[user_id]['model_name'] = None
        save_data()


    @bot.message_handler(content_types=['text'])
    def handle_text_message(message):
        user_id = str(message.chat.id)

        # Проверяем, что пользователь находится в процессе бронирования
        if user_id in user_data and user_data[user_id].get('reserving'):
            # Сохраняем введенные данные
            user_data[user_id]['reservation_details'] = message.text
            save_data()  # Сохраняем данные в файл

            # Получаем имя модели и город
            model_name = user_data[user_id]['model_name']  
            city = user_data[user_id]['city']
            
            model = next((m for m in models_data[city] if m['name'] == model_name), None)

            if model:
                # Удаляем предыдущее сообщение с деталями
                if 'reservation_message_id' in user_data[user_id]:
                    try:
                        bot.delete_message(chat_id=user_id, message_id=user_data[user_id]['reservation_message_id'])
                    except Exception as e:
                        print(f"Ошибка при удалении сообщения: {e}")
                
                # Отправляем сообщение о том, что детали записаны
                bot.send_message(message.chat.id, "✅ Детали бронирования записаны.")
                
                # Отправляем фото модели с текстом и кнопками
                photo_path = model['photo']
                if os.path.exists(photo_path):
                    with open(photo_path, 'rb') as photo:
                        time_markup = types.InlineKeyboardMarkup()
                        time_markup.add(types.InlineKeyboardButton("🏞Час - 4100₽", callback_data=f'time_1_{model["name"]}'),
                                        types.InlineKeyboardButton("🌄2 часа - 7925₽", callback_data=f'time_2_{model["name"]}'),
                                        types.InlineKeyboardButton("🌃Ночь - 16400₽", callback_data=f'time_night_{model["name"]}'),
                                        types.InlineKeyboardButton("⬅️Назад", callback_data=f"back_to_model_{model['name']}"))
                        
                        caption_text = "Выберите время на которое вы хотите оформить модель:"
                        bot.send_photo(message.chat.id, photo, caption=caption_text, reply_markup=time_markup)

                # Сбрасываем состояние бронирования
                user_data[user_id]['reserving'] = False
                user_data[user_id]['model_name'] = None  # Сбрасываем имя модели
                save_data()  # Сохраняем изменения

            else:
                bot.send_message(message.chat.id, "Модель не найдена.")
        else:
            # Уведомляем пользователя, что он не находится в процессе бронирования
            bot.send_message(message.chat.id, "Пожалуйста, начните бронирование заново.")

            

    try:
        bot.polling(non_stop=True)
    except Exception as e:
        print(f'Ошибка: {e}')
        time.sleep(60)  # Задержка перед перезапуском
        start_bot()  # Перезапуск бота


if __name__ == "__main__":
    path = './'  # Путь к директории, которую нужно отслеживать
    event_handler = ReloadHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    try:
        start_bot()  # Запуск бота
    except KeyboardInterrupt:
        print('Завершение работы...')
    finally:
        observer.stop()  # Остановка наблюдателя
    observer.join()



