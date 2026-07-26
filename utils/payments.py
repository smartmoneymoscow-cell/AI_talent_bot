"""
Интеграция с YooKassa для оплаты через самозанятость.

Архитектура платежей:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Работодатель          Платформа           Специалист
  (заказчик)           (бот/агрегатор)       (самозанятый)
      │                     │                     │
      │  1. Создаёт заказ   │                     │
      │────────────────────>│                     │
      │                     │                     │
      │  2. Принимает работу│                     │
      │────────────────────>│                     │
      │                     │                     │
      │  3. Оплачивает      │                     │
      │     (YooKassa)      │                     │
      │────────────────────>│                     │
      │                     │  4. Чек + перевод   │
      │                     │  (за вычетом        │
      │                     │   комиссии)         │
      │                     │────────────────────>│
      │                     │                     │
  Автоматический чек    Комиссия платформы    Получает деньги
  от самозанятого       (напр. 5%)           на счёт

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Варианты работы с самозанятыми:

ВАРИАНТ 1 (реализован): YooKassa + ручной перевод
  - Работодатель платит через YooKassa
  - Платформа удерживает комиссию
  - Специалисту переводится остаток
  - Специалист как самозанятый формирует чек в приложении «Мой налог»

ВАРИАНТ 2 (альтернатива): Интеграция с «Мой налог» API (ФНС)
  - Автоматическая регистрация чеков через API ФНС
  - Требует регистрации в ФНС как партнёр
  - Документация: https://npd.nalog.ru/api/

ВАРИАНТ 3 (альтернатива): Через банк-партнёр (Тинькофф/Сбер)
  - Банк автоматически оформляет самозанятость
  - Платежи идут напрямую от заказчика к исполнителю
  - Банк сам формирует чеки
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from ai_talent_bot.config import config

# ── YooKassa SDK ──────────────────────────────────────────────
# Установка: pip install yookassa
try:
    from yookassa import Configuration, Payment as YooPayment
    YOOKASSA_AVAILABLE = True
except ImportError:
    YOOKASSA_AVAILABLE = False


def init_yookassa():
    """Инициализация YooKassa SDK."""
    if YOOKASSA_AVAILABLE and config.YOOKASSA_SHOP_ID and config.YOOKASSA_SECRET_KEY:
        Configuration.account_id = config.YOOKASSA_SHOP_ID
        Configuration.secret_key = config.YOOKASSA_SECRET_KEY
        return True
    return False


@dataclass
class PaymentResult:
    success: bool
    payment_id: str = ""
    confirmation_url: str = ""
    status: str = ""
    error: str = ""


async def create_payment(
    order_id: int,
    amount_rub: int,
    description: str,
    return_url: str = "https://t.me/",
) -> PaymentResult:
    """
    Создать платёж через YooKassa.

    Args:
        order_id: ID заказа в нашей БД
        amount_rub: сумма в рублях
        description: описание платежа
        return_url: URL возврата после оплаты

    Returns:
        PaymentResult с confirmation_url для оплаты
    """
    idempotence_key = str(uuid.uuid4())

    if not YOOKASSA_AVAILABLE:
        return PaymentResult(
            success=False,
            error="YooKassa SDK не установлен. Выполните: pip install yookassa",
        )

    if not config.YOOKASSA_SHOP_ID:
        # Демо-режим: имитируем платёж
        return PaymentResult(
            success=True,
            payment_id=f"demo_{idempotence_key[:8]}",
            confirmation_url="",
            status="demo",
        )

    try:
        payment = YooPayment.create({
            "amount": {
                "value": f"{amount_rub:.2f}",
                "currency": "RUB",
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url,
            },
            "capture": True,
            "description": description,
            "metadata": {
                "order_id": str(order_id),
            },
            "receipt": {
                # Данные чека для самозанятого
                # В продакшене: данные специалиста как получателя
                "customer": {
                    "email": "customer@example.com",
                },
                "items": [
                    {
                        "description": description[:128],
                        "quantity": "1.00",
                        "amount": {
                            "value": f"{amount_rub:.2f}",
                            "currency": "RUB",
                        },
                        "vat_code": 1,  # Без НДС (самозанятый)
                    },
                ],
            },
        }, idempotence_key)

        return PaymentResult(
            success=True,
            payment_id=payment.id,
            confirmation_url=payment.confirmation.confirmation_url,
            status=payment.status,
        )
    except Exception as e:
        return PaymentResult(success=False, error=str(e))


async def check_payment_status(payment_id: str) -> PaymentResult:
    """Проверить статус платежа."""
    if not YOOKASSA_AVAILABLE or not config.YOOKASSA_SHOP_ID:
        # Демо-режим: считаем оплату успешной
        return PaymentResult(success=True, payment_id=payment_id, status="succeeded")

    try:
        payment = YooPayment.find_one(payment_id)
        return PaymentResult(
            success=True,
            payment_id=payment.id,
            status=payment.status,
        )
    except Exception as e:
        return PaymentResult(success=False, error=str(e))


def calculate_fee(amount_rub: int) -> tuple[int, int]:
    """
    Рассчитать комиссию платформы.

    Returns:
        (platform_fee_kopecks, specialist_amount_kopecks)
    """
    fee_percent = config.PLATFORM_FEE_PERCENT
    platform_fee = int(amount_rub * fee_percent / 100)
    specialist_amount = amount_rub - platform_fee
    return platform_fee, specialist_amount
