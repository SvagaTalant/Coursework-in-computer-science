import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

def get_ai_insight(data_package, user_query):
    token = os.getenv("GROQ_API_KEY")
    if not token:
        return "Помилка: Ключ не знайдено"

    client = Groq(api_key=token)
    
    context = (
        f"ДАНІ ДЛЯ АНАЛІЗУ:\n"
        f"- Загальна сума: {data_package['total_spent']:.2f} грн.\n"
        f"- Очікувані витрати наступного місяця: {data_package['forecast']:.2f} грн.\n"
        f"- Знайдено нетипових покупок: {len(data_package['anomalies'])}\n"
        f"- Виявлено регулярних платежів (підписок): {len(data_package['subscriptions'])}\n"
        f"- Статистика категорій (std показує нестабільність):\n"
        f"{data_package['cat_stats'].to_string(index=False)}"
    )

    system_instruction = """
    Ти — особистий фінансовий консультант. 
    ТВОЄ ЗАВДАННЯ: Пояснювати складні фінансові дані простою, людською мовою.
    
    ПРАВИЛА:
    1. ЗАБОРОНЕНО використовувати технічні терміни: 'std', 'дисперсія', 'середньоквадратичне відхилення', 'індекс', 'датафрейм'.
    2. Замість 'висока дисперсія (std)' кажи 'нестабільні витрати' або 'різкі перепади'.
    3. Замість 'аномалія' кажи 'нетипова покупка' або 'неочікувані витрати'.
    4. Обов'язково зверни увагу на категорії, де витрати сильно скачуть (високий std у даних), але поясни це як: "Цього місяця ви витрачали на цю категорію дуже нерівномірно".
    5. Твоя відповідь повинна бути дружньою, але професійною.
    6. ПИШИ ВИКЛЮЧНО УКРАЇНСЬКОЮ МОВОЮ. Не використовуй латиницю або ієрогліфи всередині українських слів.
    7. Твоя відповідь має бути чистою від дефектів кодування.
    8. Якщо бачиш категорію латиницею, перекладай її українською.

    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"Ось мої дані: {context}\n\nПитання користувача: {user_query}"}
            ],
            model="llama-3.3-70b-versatile",
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Помилка аналізу: {str(e)}"