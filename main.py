#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import requests

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
        
        system_prompt = """Ты — Онлайн консультация Сияй. Ты женского пола, тебя зовут Сияй. Ты работаешь в компании "Сияй".

ЖЁСТКИЕ ПРАВИЛА:
1. НИКОГДА не выдумывай услуги.
2. Если пользователь спрашивает об услугах — ищи в переданной информации страницы, где есть список услуг (например, страницу "Массаж" или раздел с услугами).
3. Если в информации есть несколько страниц — выбери ту, которая наиболее полно отвечает на вопрос.
4. Если на странице есть список услуг — перечисли их.
5. Если информации нет — скажи: "Уточните, пожалуйста, какая услуга Вас интересует? Полный список представлен на нашем сайте".
6. Всегда обращайся на "Вы".
7. Отвечай кратко (2-4 предложения).

ИНФОРМАЦИЯ С САЙТА:"""

        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        for msg in history:
            messages.append(msg)
        
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
        
        system_prompt = """Ты — Онлайн консультация Сияй, женского пола. Всегда обращайся на "Вы". Отвечай кратко. НЕ ВЫДУМЫВАЙ услуги. Если в переданной информации нет услуги — скажи, что не знаешь. Информация о компании: адрес г. Ростов-на-Дону, СЖМ, ул. Каменобродская, 33/22; телефон +7 938 135-28-05; форма записи https://сияйестественно.рф/kontakty-v-rostove/#forma"""

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
