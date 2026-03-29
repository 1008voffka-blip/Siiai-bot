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

# Создаем приложение Flask
app = Flask(__name__)
CORS(app)  # Разрешаем запросы с любых доменов

# --- БЕЗОПАСНОЕ ХРАНЕНИЕ API-КЛЮЧА ---
# Ключ берется из переменной окружения, а не хранится в коде!
AITUNNEL_API_KEY = os.environ.get('AITUNNEL_API_KEY')
if not AITUNNEL_API_KEY:
    logger.error("КРИТИЧЕСКАЯ ОШИБКА: не установлена переменная окружения AITUNNEL_API_KEY")
    # В продакшене лучше не запускаться без ключа
    # raise ValueError("AITUNNEL_API_KEY не установлен")

# Инициализация клиента OpenAI для AITunnel
client = OpenAI(
    api_key=AITUNNEL_API_KEY,
    base_url="https://api.aitunnel.ru/v1/",
)

# ==================== ЭНДПОИНТЫ API ====================

@app.route('/health', methods=['GET'])
def health():
    """Проверка работоспособности API"""
    return jsonify({'status': 'ok', 'message': 'AI Chatbot is running'})


@app.route('/chat', methods=['POST'])
def chat():
    """
    Обычный текстовый чат
    Ожидает JSON: {"message": "текст", "history": [...]}
    """
    try:
        data = request.json
        user_message = data.get('message', '')
        history = data.get('history', [])
        
        if not user_message:
            return jsonify({'error': 'Сообщение не может быть пустым'}), 400
        
        # Формируем сообщения с системным промптом
        messages = [
            {"role": "system", "content": "Ты полезный и дружелюбный помощник. Отвечай кратко и по делу."}
        ]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        
        # Отправляем запрос в AITunnel
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
    """
    Чат с распознаванием изображения
    Ожидает JSON: {"text": "вопрос", "image_url": "ссылка_на_картинку"}
    """
    try:
        data = request.json
        user_text = data.get('text', 'Что на этом изображении?')
        image_url = data.get('image_url', '')
        
        if not image_url:
            return jsonify({'error': 'Не указано изображение'}), 400
        
        # Отправляем запрос с изображением
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url, "detail": "auto"}
                        }
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
    """Проверка баланса AITunnel"""
    try:
        response = requests.get(
            f"{client.base_url}aitunnel/balance",
            headers={"Authorization": f"Bearer {AITUNNEL_API_KEY}"}
        )
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Для локального тестирования
    app.run(host='0.0.0.0', port=5000, debug=False)
