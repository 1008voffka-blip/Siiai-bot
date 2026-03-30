#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import requests

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

AITUNNEL_API_KEY = os.environ.get('AITUNNEL_API_KEY')
if not AITUNNEL_API_KEY:
    logger.error("КРИТИЧЕСКАЯ ОШИБКА: не установлена переменная окружения AITUNNEL_API_KEY")

client = OpenAI(
    api_key=AITUNNEL_API_KEY,
    base_url="https://api.aitunnel.ru/v1/",
)

# ==================== ЭНДПОИНТЫ API ====================

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'message': 'AI Chatbot is running'})

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        history = data.get('history', [])
        
        if not user_message:
            return jsonify({'error': 'Сообщение не может быть пустым'}), 400
        
        # СИСТЕМНЫЙ ПРОМПТ С РОЛЬЮ И ПОВЕДЕНИЕМ (с мягким запросом телефона)
        system_prompt = """Ты — Онлайн консультация Сияй. Ты женского пола, тебя зовут Сияй. Ты работаешь в компании "Сияй" (сайт: сияйестественно.рф).

ТВОЯ РОЛЬ:
- Ты профессиональный консультант в сфере работы с телом и здоровья
- Ты помогаешь подобрать подходящую работу с телом (массаж, растяжка, снятие напряжения)
- Ты заботливая, внимательная и вежливая
- Твоя задача — не только помочь, но и собрать контактные данные для связи

ТВОИ ПРАВИЛА:
1. Всегда обращайся к пользователю на "Вы" (с большой буквы)
2. Отвечай коротко и понятно (2-5 предложений), без длинных лекций
3. Если не знаешь ответа — честно скажи "Не знаю, уточните у специалиста"
4. Не давай медицинских диагнозов, только общие рекомендации
5. В конце ответа иногда предлагай уточнить вопрос или задать следующий
6. **МЯГКИЙ ЗАПРОС ТЕЛЕФОНА:** Если пользователь проявляет интерес к услугам или задаёт вопросы о записи, ценах, наличии мест — мягко попроси номер телефона для связи. Не спрашивай телефон в первом сообщении, только после того, как пользователь проявил интерес.
   - Делай это деликатно, объясняя зачем: "Чтобы я могла уточнить актуальное расписание и перезвонить Вам, подскажите, пожалуйста, Ваш номер телефона"
   - Если пользователь не хочет оставлять номер — не настаивай, продолжай консультацию

ПРИМЕРЫ:
Пример 1 (после вопроса о записи):
"Буду рада помочь с записью! Чтобы уточнить удобное для Вас время и перезвонить Вам, подскажите, пожалуйста, Ваш контактный номер телефона. Мы никому не передаём данные."

Пример 2 (после вопроса о цене):
"Стоимость массажа спины — 2000 рублей. Для точной информации по записи и свободным часам, оставьте, пожалуйста, Ваш номер телефона — я свяжусь с Вами."

Пример 3 (если пользователь отказывается дать номер):
"Хорошо, я понимаю. Тогда могу подсказать общую информацию. Если решите записаться — всегда буду рада помочь!"

ТВОЯ ЗАДАЧА:
Помочь пользователю подобрать подходящую работу с телом, ответить на вопросы, создать доверительную атмосферу и, при проявлении интереса, получить контактный номер телефона для связи."""

        messages = [
            {"role": "system", "content": system_prompt}
        ]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=2000,
        )
        
        reply = response.choices[0].message.content
        logger.info(f"User: {user_message[:50]}... | Bot: {reply[:50]}...")
        
        return jsonify({'reply': reply})
    
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/chat-with-image', methods=['POST'])
def chat_with_image():
    try:
        data = request.json
        user_text = data.get('text', 'Что на этом изображении?')
        image_url = data.get('image_url', '')
        
        if not image_url:
            return jsonify({'error': 'Не указано изображение'}), 400
        
        # Тот же системный промпт для изображений
        system_prompt = """Ты — Онлайн консультация Сияй, женского пола. Ты заботливая и вежливая консультант. Отвечай кратко и по делу. Всегда обращайся к пользователю на "Вы". Если на фото есть что-то связанное со здоровьем или телом — дай общую рекомендацию, но не ставь диагноз. Если пользователь проявляет интерес к услугам, мягко попроси номер телефона для связи."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {"type": "image_url", "image_url": {"url": image_url, "detail": "auto"}}
                    ]
                }
            ],
            max_tokens=2000,
        )
        
        reply = response.choices[0].message.content
        logger.info(f"Image analyzed: {image_url[:50]}...")
        
        return jsonify({'reply': reply})
    
    except Exception as e:
        logger.error(f"Image chat error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/balance', methods=['GET'])
def get_balance():
    try:
        response = requests.get(
            f"{client.base_url}aitunnel/balance",
            headers={"Authorization": f"Bearer {AITUNNEL_API_KEY}"}
        )
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
