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

    @property
    def price(self):
        return self._price

    @price.setter
    def price(self, value):
        if value < 0:
            raise ValueError("Вартість не може бути від'ємною!")
        self._price = value

    # Поліморфізм: абстрактні методи для нащадків
    def get_icon(self) -> str:
        return "📍"

    def get_details(self) -> str:
        return "Деталі відсутні"

    # --- 4. Менеджер контексту (Транзакційне Редагування) ---
    def __enter__(self):
        print(f"\n[System] Відкриття транзакції редагування для '{self.title}'...")
        self._backup_state = {
            'title': self.title,
            'price': self._price,
            'start_time': self.start_time,
            'end_time': self.end_time
        }
        return self

    def __exit__(self, exc_type, exc_val, traceback):
        if exc_type:
            self.title = self._backup_state['title']
            self._price = self._backup_state['price']
            self.start_time = self._backup_state['start_time']
            self.end_time = self._backup_state['end_time']
            print(f"⚠️ [Транзакцію скасовано] Зміни відхилено через помилку: {exc_val}")
            return True 
        else:
            self.status = "ОНОВЛЕНО"
            print(f"✅ [Транзакція успішна] Зміни для етапу '{self.title}' збережено!")
        return True

    # --- 5. Магічні методи ---
    def __lt__(self, other):
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

    def get_icon(self) -> str:
        icons = {TransportType.PLANE: "✈️", TransportType.BUS: "🚌", TransportType.TRAIN: "🚆", TransportType.CAR: "🚗"}
        return icons.get(self.transport, "🚀")

    def get_details(self) -> str:
        return f"Рейс/Маршрут: {self.flight_number}, Траспорт: {self.transport.value}"

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

# --- 6. Кастомний Ітератор ---
class ChronologicalIterator:
    def __init__(self, steps: list):
        self._steps = sorted(steps) 
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

    def __getitem__(self, index):
        return sorted(self.steps)[index]

    # --- 8. Серіалізація та Персистентність ---
    def load_config(self, filepath="config.json"):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.config = AppConfig(**data)
                self.converter.rate = self.config.eur_to_uah_rate
        except FileNotFoundError:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.config), f, ensure_ascii=False, indent=4)

    def save_system_state(self, filepath="travel_data.pkl"):
        state = {'traveler': self.traveler, 'steps': self.steps}
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
    print("1 ➕ — Додати новий етап (Трансфер / Готель / Екскурсія)")
    print("2 📜 — Показати загальний таймлайн маршруту")
    print("3 🔍 — ПОШУК та РЕДАГУВАННЯ даних (Тест 'with')")
    print("4 🌪️  — ФІЛЬТРАЦІЯ етапів за статусом")
    print("5 🔀 — СОРТУВАННЯ етапів (за вибором)")
    print("6 ❌ — Видалити етап")
    print("7 💾 — Зберегти зміни (Pickle/CSV)")
    print("0 🚪 — Вийти")
    print("="*50)

if __name__ == "__main__":
    default_traveler = Traveler(name="Sofia", email="sofia@example.com", passport_number="FT123456")
    manager = Itinerary(traveler=default_traveler)
    manager.load_config()
    manager.load_system_state()

    while True:
        main_menu()
        try:
            choice = input("Оберіть дію: ").strip()
            
            match choice:
                case "1":
                    print("\n--- Оберіть тип нового етапу ---")
                    print("1. ✈️/🚌 Трансфер (Літак, автобус, поїзд...)")
                    print("2. 🏨 Готель / Проживання")
                    print("3. 🗺️  Екскурсія")
                    sub_choice = input("Ваш вибір: ").strip()
                    
                    match sub_choice:
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
                            print(f"✅ Трансфер додано успішно.")

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
                        
                        case _:
                            print("⚠️ Невідомий тип етапу. Повернення в головне меню.")

                case "2":
                    print(manager)

                case "3":
                    if not manager.steps:
                        print("Маршрут порожній!")
                        continue
                    
                    query = input("Введіть текст для пошуку етапу: ").strip().lower()
                    found_steps = [s for s in manager.steps if query in s.title.lower()]
                    
                    if not found_steps:
                        print("⚠️ Нічого не знайдено за таким запитом.")
                        continue
                    
                    print("\nЗнайдені збіги:")
                    for idx, s in enumerate(found_steps, 1):
                        print(f"{idx}. {s.title} (Поточна ціна: {s.price})")
                    
                    s_idx = int(input("Оберіть номер етапу для редагування: ")) - 1
                    target_step = found_steps[s_idx]
                    
                    with target_step as active_step:
                        new_title = input(f"Нова назва (натисніть Enter, щоб залишити '{active_step.title}'): ").strip()
                        if new_title:
                            active_step.title = new_title
                        
                        price_input = input(f"Нова вартість (натисніть Enter, щоб залишити {active_step.price}): ").strip()
                        if price_input:
                            active_step.price = float(price_input)

                case "4":
                    if not manager.steps:
                        print("Маршрут порожній!")
                        continue
                    print("Оберіть статус для фільтрації:")
                    print("1. ОЧІКУЄ\n2. ОНОВЛЕНО")
                    f_choice = input("Ваш вибір: ").strip()
                    status_map = {"1": "ОЧІКУЄ", "2": "ОНОВЛЕНО"}
                    target_status = status_map.get(f_choice)
                    
                    if target_status:
                        filtered = [s for s in manager.steps if s.status == target_status]
                        if filtered:
                            print(f"\n📋 Етапи зі статусом '{target_status}':")
                            for s in filtered:
                                print(f"  * {s}")
                        else:
                            print("Етапів із таким статусом не знайдено.")
                    else:
                        print("Невірний вибір.")

                case "5":
                    if not manager.steps:
                        print("Маршрут порожній!")
                        continue
                    print("Оберіть тип сортування для відображення:")
                    print("1. Хронологічне (за часом початку — магічний метод __lt__)")
                    print("2. За ціною (від найдешевших)")
                    s_choice = input("Ваш вибір: ").strip()
                    
                    if s_choice == "1":
                        print("\n🕒 Хронологічний список:")
                        for s in sorted(manager.steps):
                            print(f"  {s}")
                    elif s_choice == "2":
                        print("\n💰 Список за ціною:")
                        for s in sorted(manager.steps, key=lambda x: x.price):
                            print(f"  {s.title} — {s.price} UAH")
                    else:
                        print("Невірний вибір.")

                case "6":
                    if manager.steps:
                        for i, step in enumerate(manager.steps, 1):
                            print(f"{i}. {step.title}")
                        idx = int(input("Номер для видалення: ")) - 1
                        manager.delete_step(idx)
                    else:
                        print("Маршрут порожній!")

                case "7":
                    manager.save_system_state()
                    manager.export_csv_report()
                    print("✅ Дані успішно збережені.")

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