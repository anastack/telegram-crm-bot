import os
import json
from openai import AsyncOpenAI
from datetime import datetime
from database.database import SessionLocal
from database.models import Service, Provider, Appointment, User

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY", "NOT_SET"),
)

# Выбор модели
MODEL_NAME = "openai/gpt-4o-mini"

SYSTEM_PROMPT = """Ты — вежливый, приветливый и компетентный виртуальный администратор нашего сервиса. 
Твоя цель — отвечать на вопросы клиентов об услугах, специалистах и помогать им записаться на прием.

У тебя есть доступ к следующим функциям (tools):
1. `get_services` - Возвращает список всех доступных услуг с их ID, ценой и длительностью.
2. `get_providers` - Возвращает список всех специалистов с их ID.
3. `book_appointment` - Создает запись на прием для клиента.

Правила:
- Всегда уточняй детали перед записью: какую услугу хочет клиент, к какому специалисту, дату и время.
- Если клиент спрашивает об услугах, используй `get_services`.
- Если клиент хочет записаться, предложи ему выбрать услугу из доступных, затем специалиста (`get_providers`), а затем спроси желаемую дату и время (формат: YYYY-MM-DD HH:MM).
- После того как соберешь все 4 параметра (service_id, provider_id, date, time), вызови `book_appointment`.
- Формат даты должен быть "YYYY-MM-DD", а времени "HH:MM".
- Если клиент пишет какую-то ерунду, вежливо верни его к теме наших услуг.
"""

# Функции-инструменты
def get_services():
    db = SessionLocal()
    try:
        services = db.query(Service).all()
        result = [{"id": s.id, "name": s.name, "price": s.price, "duration": s.duration} for s in services]
        return json.dumps(result, ensure_ascii=False)
    finally:
        db.close()

def get_providers():
    db = SessionLocal()
    try:
        providers = db.query(Provider).all()
        result = [{"id": p.id, "name": p.name} for p in providers]
        return json.dumps(result, ensure_ascii=False)
    finally:
        db.close()

def book_appointment(user_id: int, service_id: int, provider_id: int, date: str, time: str):
    db = SessionLocal()
    try:
        # Проверяем пользователя
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            return json.dumps({"error": "User not found in DB."})
            
        date_time_str = f"{date} {time}"
        try:
            appointment_dt = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            return json.dumps({"error": "Invalid date or time format. Use YYYY-MM-DD and HH:MM."})
            
        new_app = Appointment(
            user_id=user.id,
            service_id=service_id,
            provider_id=provider_id,
            date_time=appointment_dt
        )
        db.add(new_app)
        db.commit()
        
        # Получаем красивые названия для ответа
        service = db.query(Service).filter(Service.id == service_id).first()
        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        
        return json.dumps({
            "status": "success", 
            "message": f"Successfully booked {service.name} with {provider.name} on {date} at {time}"
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        db.close()

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_services",
            "description": "Получить список доступных услуг, их ID, стоимость и длительность.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_providers",
            "description": "Получить список доступных специалистов и их ID.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Записать клиента на услугу к специалисту на определенную дату и время.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_id": {
                        "type": "integer",
                        "description": "ID выбранной услуги (из get_services)"
                    },
                    "provider_id": {
                        "type": "integer",
                        "description": "ID выбранного специалиста (из get_providers)"
                    },
                    "date": {
                        "type": "string",
                        "description": "Дата в формате YYYY-MM-DD"
                    },
                    "time": {
                        "type": "string",
                        "description": "Время в формате HH:MM"
                    }
                },
                "required": ["service_id", "provider_id", "date", "time"]
            }
        }
    }
]

# Хранилище контекста бесед (в памяти для простоты)
# В продакшене лучше использовать БД или Redis
user_contexts = {}

async def process_user_message(user_id: int, text: str) -> str:
    """Отправляет сообщение пользователя в ИИ и возвращает ответ."""
    
    # Быстрая проверка на отсутствие ключа
    api_key = os.getenv("OPENROUTER_API_KEY", "NOT_SET")
    if api_key in ["NOT_SET", "твой_ключ_здесь", ""]:
        return "🤖 Функция ИИ пока недоступна, так как администратор еще не настроил API ключ. Пожалуйста, воспользуйтесь стандартным меню (нажмите 'Выйти')."
        
    # Инициализируем контекст если его нет
    if user_id not in user_contexts:
        user_contexts[user_id] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        
    # Добавляем сообщение пользователя
    user_contexts[user_id].append({"role": "user", "content": text})
    
    # Ограничиваем историю (оставляем системный промпт + последние 10 сообщений)
    if len(user_contexts[user_id]) > 11:
        user_contexts[user_id] = [user_contexts[user_id][0]] + user_contexts[user_id][-10:]
        
    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=user_contexts[user_id],
            tools=TOOLS,
            tool_choice="auto"
        )
        
        response_message = response.choices[0].message
        
        # Проверяем, вызвал ли ИИ функцию
        if response_message.tool_calls:
            user_contexts[user_id].append(response_message)
            
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                print(f"ИИ вызывает функцию: {function_name} с аргументами {function_args}")
                
                if function_name == "get_services":
                    function_response = get_services()
                elif function_name == "get_providers":
                    function_response = get_providers()
                elif function_name == "book_appointment":
                    function_response = book_appointment(
                        user_id=user_id,
                        service_id=function_args.get("service_id"),
                        provider_id=function_args.get("provider_id"),
                        date=function_args.get("date"),
                        time=function_args.get("time")
                    )
                else:
                    function_response = json.dumps({"error": f"Unknown function: {function_name}"})
                
                # Добавляем результат функции в контекст
                user_contexts[user_id].append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                })
            
            # Делаем второй вызов API с результатами функции
            second_response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=user_contexts[user_id]
            )
            final_message = second_response.choices[0].message
            user_contexts[user_id].append(final_message)
            return final_message.content
        else:
            # Обычный текстовый ответ
            user_contexts[user_id].append(response_message)
            return response_message.content
            
    except Exception as e:
        print(f"Ошибка при работе с ИИ: {e}")
        return "Извините, сейчас я не могу обработать ваш запрос (возможно, не настроен API-ключ OpenRouter или проблема с сетью). Попробуйте позже или используйте кнопки меню."
