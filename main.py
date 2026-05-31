import sys
import time
import json
import pickle
import csv
from enum import Enum
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

# --- 1. Enum (Перелічуваний тип) ---
class TransportType(Enum):
    PLANE = "Літак"
    BUS = "Автобус"
    TRAIN = "Поїзд"
    CAR = "Автомобіль"

# --- 2. Моделювання даних (Dataclasses) ---
@dataclass
class Traveler:
    name: str
    email: str
    passport_number: str

@dataclass
class AppConfig:
    agency_name: str = "DreamTravel"
    default_currency: str = "UAH"
    eur_to_uah_rate: float = 42.5

# --- Бізнес-логіка (Функтор) ---
class CurrencyConverter:
    def __init__(self, rate: float):
        self.rate = rate
        self.call_count = 0

    def __call__(self, amount: float, currency: str) -> float:
        self.call_count += 1
        if currency.upper() == "EUR":
            return amount * self.rate
        return amount

# --- 3. Ієрархія класів, Інкапсуляція та Валідація ---
class TravelStep:
    def __init__(self, start_time: datetime, end_time: datetime, title: str, price: float):
        if end_time <= start_time:
            raise ValueError("Час завершення етапу не може передувати часу початку.")
        self.start_time = start_time
        self.end_time = end_time
        self.title = title
        self.status = "ОЧІКУЄ"
        
        # Інкапсуляція: захищений атрибут
        self._price = 0.0
        self.price = price # Виклик сетера для валідації
        self._enter_time = None

    @property
    def price(self):
        return self._price

    @price.setter
    def price(self, value):
        if value < 0:
            raise ValueError("Помилка валідації: Вартість не може бути від'ємною!")
        self._price = value

    # Поліморфізм: абстрактні методи для нащадків
    def get_icon(self) -> str:
        return "📍"

    def get_details(self) -> str:
        return "Деталі відсутні"

    # --- 4. Менеджер контексту (Транзакційність бронювання) ---
    def __enter__(self):
        print(f"\n[System] Спроба транзакції для етапу '{self.title}'...")
        self.status = "В ОБРОБЦІ"
        self._enter_time = time.time()  
        return self

    def __exit__(self, exc_type, exc_val, traceback):
        elapsed_time = time.time() - self._enter_time
        timeout_limit = 5.0 

        if exc_type:
            self.status = "ПОМИЛКА"
            print(f"[System] Транзакцію скасовано через виняток: {exc_val}")
            return True # Приглушуємо помилку для продовження роботи програми
        elif elapsed_time > timeout_limit:
            self.status = "EXPIRED"
            print(f"[System] Помилка: Перевищено час очікування.")
        else:
            self.status = "ЗАБРОНЬОВАНО"
            print(f"[System] Транзакція успішна! Стан змінено на '{self.status}'.")
        return True

    # --- 5. Магічні методи ---
    def __lt__(self, other):
        # Дозволяє сортувати об'єкти хронологічно
        return self.start_time < other.start_time

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.title}', price={self.price})"

    def __str__(self):
        start_str = self.start_time.strftime('%H:%M %d.%m')
        end_str = self.end_time.strftime('%H:%M %d.%m')
        return f"[{start_str} - {end_str}] {self.title} | Вартість: {self.price} | Стан: {self.status}"

# Нащадок 1
class Flight(TravelStep):
    def __init__(self, start_time: datetime, end_time: datetime, title: str, price: float, transport: TransportType, flight_number: str):
        super().__init__(start_time, end_time, title, price)
        self.transport = transport
        self.flight_number = flight_number

    # Перевизначення методів (Поліморфізм)
    def get_icon(self) -> str:
        icons = {TransportType.PLANE: "✈️", TransportType.BUS: "🚌", TransportType.TRAIN: "🚆", TransportType.CAR: "🚗"}
        return icons.get(self.transport, "🚀")

    def get_details(self) -> str:
        return f"Рейс/Маршрут: {self.flight_number}, Транспорт: {self.transport.value}"

    def __repr__(self):
        return f"Flight('{self.title}', transport={self.transport.name}, flight_num='{self.flight_number}')"

# Нащадок 2
class HotelBooking(TravelStep):
    def __init__(self, start_time: datetime, end_time: datetime, title: str, price: float, hotel_name: str, room_type: str):
        super().__init__(start_time, end_time, title, price)
        self.hotel_name = hotel_name
        self.room_type = room_type

    def get_icon(self) -> str:
        return "🏨"

    def get_details(self) -> str:
        return f"Готель: {self.hotel_name}, Номер: {self.room_type}"

    def __repr__(self):
        return f"HotelBooking('{self.title}', hotel='{self.hotel_name}', room='{self.room_type}')"

# Нащадок 3
class Excursion(TravelStep):
    def __init__(self, start_time: datetime, end_time: datetime, title: str, price: float, location: str, guide_name: str):
        super().__init__(start_time, end_time, title, price)
        self.location = location
        self.guide_name = guide_name

    def get_icon(self) -> str:
        return "🗺️"

    def get_details(self) -> str:
        return f"Локація: {self.location}, Гід: {self.guide_name}"
        
    def __repr__(self):
        return f"Excursion('{self.title}', location='{self.location}')"

# --- 6. Кастомний Ітератор (Генератор) ---
class ChronologicalIterator:
    """Ітератор, який завжди обходить кроки подорожі у хронологічному порядку."""
    def __init__(self, steps: list):
        self._steps = sorted(steps) # Сортування працює завдяки магічному методу __lt__
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._index < len(self._steps):
            step = self._steps[self._index]
            self._index += 1
            return step
        raise StopIteration

# --- 7. Клас-менеджер (Композиція/Агрегація) ---
class Itinerary:
    def __init__(self, traveler: Traveler = None):
        self.steps = []
        self.traveler = traveler
        self.config = AppConfig()
        self.converter = CurrencyConverter(rate=self.config.eur_to_uah_rate)

    def add_step(self, step: TravelStep):
        self.steps.append(step)

    def delete_step(self, index: int):
        if 0 <= index < len(self.steps):
            removed = self.steps.pop(index)
            print(f"[System] Етап '{removed.title}' видалено!")
        else:
            raise IndexError("Етап з таким індексом не існує.")

    # Магічний метод доступу за індексом
    def __getitem__(self, index):
        # Повертає відсортований елемент
        return sorted(self.steps)[index]

    # --- 8. Серіалізація та Персистентність ---
    def load_config(self, filepath="config.json"):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.config = AppConfig(**data)
                self.converter.rate = self.config.eur_to_uah_rate
        except FileNotFoundError:
            # Створення дефолтного конфігу, якщо його немає
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.config), f, ensure_ascii=False, indent=4)

    def save_system_state(self, filepath="travel_data.pkl"):
        state = {
            'traveler': self.traveler,
            'steps': self.steps
        }
        with open(filepath, 'wb') as f:
            pickle.dump(state, f)

    def load_system_state(self, filepath="travel_data.pkl"):
        try:
            with open(filepath, 'rb') as f:
                state = pickle.load(f)
                self.traveler = state.get('traveler')
                self.steps = state.get('steps', [])
                print(f"[System] Відновлено етапів: {len(self.steps)}")
        except FileNotFoundError:
            print("[System] Нова сесія (файл бекапу не знайдено).")

    def export_csv_report(self, filepath="itinerary_report.csv"):
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(['Сутність', 'Назва події', 'Початок', 'Кінець', 'Вартість', 'Статус', 'Деталі']) 
            for step in sorted(self.steps):
                type_name = type(step).__name__
                start_str = step.start_time.strftime('%H:%M %d.%m.%Y')
                end_str = step.end_time.strftime('%H:%M %d.%m.%Y')
                writer.writerow([type_name, step.title, start_str, end_str, step.price, step.status, step.get_details()])
        print(f"[System] Аналітичний звіт експортовано у '{filepath}'.")

    def __str__(self):
        if not self.steps:
            return "Маршрут порожній."
        
        # Використовуємо кастомний ітератор для обходу
        iterator = ChronologicalIterator(self.steps)
        
        lines = []
        user_info = f" Мандрівник: {self.traveler.name}" if self.traveler else ""
        lines.append(f"\n🗺️  ТАЙМЛАЙН МАРШРУТУ {self.config.agency_name}{user_info} 🗺️")
        lines.append("=" * 60)
        
        for i, step in enumerate(iterator, start=1):
            icon = step.get_icon()
            time_f = step.start_time.strftime('%d.%m %H:%M')
            lines.append(f"  |")
            lines.append(f"  +-- {icon} [{time_f}] {step.title} ({step.price} {self.config.default_currency})")
            lines.append(f"  |      Статус:  {step.status}")
            lines.append(f"  |      Деталі:  {step.get_details()}")
            
        lines.append("  |")
        lines.append("  🏁 Кінець маршруту\n" + "=" * 60)
        return "\n".join(lines)


# --- 9. Інтерфейс командного рядка (CLI) ---
def main_menu():
    print("\n" + "="*50)
    print(" 🌍 ПЛАНУВАЛЬНИК ПОДОРОЖЕЙ 🌍")
    print("="*50)
    print("1 ➕ — Додати трансфер (літак, автобус, тощо)")
    print("2 🏨 — Додати готель")
    print("3 🗺️  — Додати екскурсію")
    print("4 📜 — Показати візуальний таймлайн маршруту (Магічний метод __str__)")
    print("5 💳 — Оплатити етап (Тест контекстного менеджера)")
    print("6 💾 — Експорт (CSV) та Збереження (Pickle)")
    print("7 ❌ — Видалити етап")
    print("0 🚪 — Вийти")
    print("="*50)

if __name__ == "__main__":
    # Ініціалізація системи
    default_traveler = Traveler(name="Sofia", email="sofia@example.com", passport_number="FT123456")
    manager = Itinerary(traveler=default_traveler)
    manager.load_config()
    manager.load_system_state()

    # Нескінченний цикл із глобальним перехопленням винятків
    while True:
        main_menu()
        try:
            choice = input("Оберіть дію: ").strip()
            
            match choice:
                case "1":
                    print("\n--- Додавання трансферу ---")
                    title = input("Назва маршруту (напр. Київ-Львів): ").strip()
                    price = float(input("Вартість: "))
                    
                    print("Доступний транспорт:")
                    for idx, t in enumerate(TransportType, 1):
                        print(f"{idx}. {t.value}")
                    t_choice = int(input("Оберіть номер транспорту: "))
                    transport = list(TransportType)[t_choice - 1]
                    
                    number = input("Номер рейсу/автобуса/поїзда: ").strip()
                    hours = float(input("Тривалість у годинах: "))
                    
                    dt_start = datetime.now() + timedelta(days=len(manager.steps))
                    dt_end = dt_start + timedelta(hours=hours)
                    
                    step = Flight(dt_start, dt_end, title, price, transport, number)
                    manager.add_step(step)
                    print(f"✅ Додано: {repr(step)}")

                case "2":
                    print("\n--- Додавання готелю ---")
                    title = input("Назва етапу проживання: ").strip()
                    price = float(input("Вартість за весь період: "))
                    hotel = input("Назва готелю: ").strip()
                    room = input("Тип номеру: ").strip()
                    days = int(input("Кількість ночей: "))
                    
                    dt_start = datetime.now() + timedelta(days=len(manager.steps))
                    dt_end = dt_start + timedelta(days=days)
                    
                    step = HotelBooking(dt_start, dt_end, title, price, hotel, room)
                    manager.add_step(step)
                    print("✅ Готель додано.")

                case "3":
                    print("\n--- Додавання екскурсії ---")
                    title = input("Назва екскурсії: ").strip()
                    price = float(input("Вартість: "))
                    location = input("Локація: ").strip()
                    guide = input("Ім'я гіда: ").strip()
                    
                    dt_start = datetime.now() + timedelta(days=len(manager.steps))
                    dt_end = dt_start + timedelta(hours=3)
                    
                    step = Excursion(dt_start, dt_end, title, price, location, guide)
                    manager.add_step(step)
                    print("✅ Екскурсію додано.")

                case "4":
                    # Використання перевизначеного __str__ для красивого таймлайну
                    print(manager)

                case "5":
                    if not manager.steps:
                        print("Маршрут порожній!")
                        continue
                    
                    for i, step in enumerate(manager.steps, 1):
                        print(f"{i}. {step.title} - Стан: {step.status}")
                    idx = int(input("Оберіть номер етапу для оплати: ")) - 1
                    target_step = manager.steps[idx]
                    
                    # Використання менеджера контексту
                    with target_step as active_booking:
                        print(f"З'єднання з банком для списання {active_booking.price}...")
                        time.sleep(1) # Імітація затримки
                        # Щоб імітувати помилку, можна розкоментувати рядок нижче:
                        # raise ConnectionError("Банк відхилив платіж!")

                case "6":
                    manager.save_system_state()
                    manager.export_csv_report()
                    print("✅ Дані успішно збережені.")

                case "7":
                    if manager.steps:
                        for i, step in enumerate(manager.steps, 1):
                            print(f"{i}. {step.title}")
                        idx = int(input("Номер для видалення: ")) - 1
                        manager.delete_step(idx)
                    else:
                        print("Маршрут порожній!")

                case "0":
                    manager.save_system_state()
                    print("Дані збережено. До побачення!")
                    sys.exit(0)

                case _:
                    print("⚠️ Невідома команда.")

        except ValueError as e:
            print(f"🔴 [Помилка вводу/Валідації]: {e}")
        except IndexError as e:
            print(f"🔴 [Помилка індексу]: {e}")
        except Exception as e:
            print(f"🔴 [Критична помилка]: {e}")