import requests


class CurrencyConverter:
    def __init__(self):
        # Офіційне API НБУ, яке повертає курс долара (USD) у форматі JSON
        self.api_url = "https://bank.gov.ua/NBUStatService/v1/statistix/exchange?valcode=USD&json"
        self.usd_rate = self._fetch_usd_rate()

    def _fetch_usd_rate(self):
        """Парсинг сторінки API НБУ для отримання курсу долара."""
        try:
            response = requests.get(self.api_url)
            # Перевіряємо, чи запит успішний
            response.raise_for_status()

            # Парсимо JSON-відповідь
            data = response.json()
            if data and len(data) > 0:
                # Отримуємо значення курсу (поле 'rate')
                return float(data[0]['rate'])
            else:
                raise ValueError("Дані відсутні у відповіді сервера.")

        except Exception as e:
            print(f"Помилка при отриманні курсу валют: {e}")
            print("Використовуємо резервний курс: 44.35 грн.")
            return 44.35  # Резервний актуальний курс на червень 2026 року

    def convert_uah_to_usd(self, amount_uah):
        """Конвертація гривні в долари США."""
        if amount_uah < 0:
            raise ValueError("Сума не може бути від'ємною.")
        return amount_uah / self.usd_rate


# --- Запуск консольного додатка ---
if __name__ == "__main__":
    print("Завантаження актуального курсу валют з НБУ...")
    converter = CurrencyConverter()
    print(f"Поточний офіційний курс: 1 USD = {converter.usd_rate:.4f} UAH\n")

    try:
        uah_input = float(input("Введіть суму в гривнях (UAH): "))
        usd_result = converter.convert_uah_to_usd(uah_input)
        print(f"Результат конвертації: {usd_result:.2f} USD")
    except ValueError as e:
        print(f"Помилка введення: будь ласка, введіть коректне число. ({e})")
