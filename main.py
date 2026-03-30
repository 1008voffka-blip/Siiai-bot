#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import json
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
        context = data.get('context', '')
        rag_results = data.get('rag_results', [])
        
        if not user_message:
            return jsonify({'error': 'Сообщение не может быть пустым'}), 400
        
        # Формируем расширенный контекст из RAG результатов
        rag_context = ''
        if rag_results and len(rag_results) > 0:
            rag_context = "\n\n=== ИНФОРМАЦИЯ С САЙТА ===\n"
            for i, result in enumerate(rag_results):
                rag_context += f"\n--- СТРАНИЦА {i+1}: {result.get('title', 'Без названия')} ---\n"
                rag_context += f"URL: {result.get('url', '')}\n"
                rag_context += f"Содержание: {result.get('content', '')}\n"
            rag_context += "\n=== КОНЕЦ ИНФОРМАЦИИ ===\n"
            rag_context += "\nИспользуй ТОЛЬКО эту информацию для ответа. НЕ ВЫДУМЫВАЙ услуги, которых нет в информации.\n"
        
        # Системный промпт
        system_prompt = """Ты — Онлайн консультация Сияй. Ты женского пола, тебя зовут Сияй. Ты работаешь в компании "Сияй".

ПРАВИЛА:
1. Всегда обращайся к пользователю на "Вы".
2. Отвечай кратко (3-5 предложений).
3. Используй ТОЛЬКО информацию из раздела "ИНФОРМАЦИЯ С САЙТА".
4. Если в информации есть услуги — перечисли их.
5. НЕ ВЫДУМЫВАЙ услуги, которых нет в информации.
6. Если информации нет — скажи: "Уточните, пожалуйста, вопрос. Полный список услуг представлен на нашем сайте". """
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Добавляем историю (только последние 10 сообщений)
        for msg in history[-10:]:
            messages.append(msg)
        
        # Формируем сообщение пользователя с контекстом
        full_message = user_message
        if rag_context:
            full_message = user_message + rag_context
        
        messages.append({"role": "user", "content": full_message})
        
        logger.info(f"Сообщение с контекстом: {full_message[:200]}...")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=2000,
        )
        
        reply = response.choices[0].message.content
        logger.info(f"Ответ: {reply[:100]}...")
        
        return jsonify({'response': reply})
    
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/chat-with-image', methods=['POST'])
def chat_with_image():
    try:
        # Поддерживаем как JSON, так и FormData
        if request.is_json:
            data = request.json
            user_text = data.get('text', 'Что на этом изображении?')
            image_url = data.get('image_url', '')
            history = data.get('history', [])
            context = data.get('context', '')
        else:
            user_text = request.form.get('text', 'Что на этом изображении?')
            image_url = request.form.get('image_url', '')
            history_json = request.form.get('history', '[]')
            history = json.loads(history_json)
            context = request.form.get('context', '')
        
        if not image_url:
            return jsonify({'error': 'Не указано изображение'}), 400
        
        # Формируем системный промпт
        system_prompt = """Ты — Онлайн консультация Сияй, женского пола. Всегда обращайся на "Вы". Отвечай кратко. НЕ ВЫДУМЫВАЙ услуги. Если в переданной информации нет услуги — скажи, что не знаешь. Информация о компании: адрес г. Ростов-на-Дону, СЖМ, ул. Каменобродская, 33/22; телефон +7 938 135-28-05; форма записи https://сияйестественно.рф/kontakty-v-rostove/#forma"""

        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Добавляем историю
        for msg in history[-10:]:
            messages.append(msg)
        
        # Добавляем контекст если есть
        if context:
            messages.append({"role": "system", "content": f"Контекст: {context}"})
        
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": image_url, "detail": "auto"}}
            ]
        })
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=2000,
        )
        
        reply = response.choices[0].message.content
        logger.info(f"Image analyzed: {image_url[:50]}...")
        
        return jsonify({'response': reply})
    
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
