import random


class Creature:
    def __init__(self, name, hp):
        self.name = name
        self.hp = hp
        self.max_hp = hp

    def is_alive(self):
        return self.hp > 0


class Player(Creature):
    def __init__(self, name, hp=100):
        super().__init__(name, hp)
        self.level = 1
        self.exp = 0
        self.potions = 3
        self.skills = [
            {'name': 'Швидкий удар', 'min_dmg': 10, 'max_dmg': 15, 'chance': 0.9},
            {'name': 'Потужний удар', 'min_dmg': 25, 'max_dmg': 40, 'chance': 0.4},
            {'name': 'Удар в серце', 'min_dmg': 60, 'max_dmg': 80, 'chance': 0.15}
        ]

    def heal(self):
        if self.potions > 0:
            amount = 40 + (self.level * 5)
            self.hp += amount
            if self.hp > self.max_hp:
                self.hp = self.max_hp
            self.potions -= 1
            print(f'💕 Ви вилікувалися на {amount} HP! Залишилось зілля: {self.potions}')
            return True
        else:
            print('🧪 У вас більше немає зілля!')
            return False

    def gain_exp(self, amount):
        self.exp += amount
        print(f'💥 Ви отримали {amount} досвіду!')
        if self.exp >= 100:
            self.new_level()

    def new_level(self):
        self.level += 1
        self.exp = 0
        self.max_hp += 20
        self.hp = self.max_hp
        self.potions += 1  # Бонус при рівні
        print(f'🍾 НОВИЙ РІВЕНЬ! Тепер ви {self.level} рівня. HP відновлено та збільшено!')


class Monster(Creature):
    def __init__(self, player_level):
        monster_data = [
            {'name': 'Гоблін', 'hp': 30, 'damage': 15},
            {'name': 'Орк боксер', 'hp': 55, 'damage': 25},
            {'name': 'Орк з сокирою', 'hp': 80, 'damage': 35},
            {'name': 'Мертвий король', 'hp': 120, 'damage': 20},
        ]
        monster = random.choice(monster_data)
        multiplier = 1 + (player_level - 1) * 0.2
        super().__init__(monster['name'], int(monster['hp'] * multiplier))
        self.power = int(monster['damage'] * multiplier)


# ======== Гра ========
print('⚔️ Вітаємо у грі "OOP-Battles" ⚔️')
player_name = input("🤴 Введіть ім'я свого героя: ")
player = Player(player_name)
print(f'🏇 {player.name} вирушає у пригоду!\n')

while player.is_alive():
    enemy = Monster(player.level)
    print(f'\n👹 На шляху з\'явився {enemy.name}! (HP: {enemy.hp}, Сила: {enemy.power})')

    while enemy.is_alive() and player.is_alive():
        print(f"\n--- {player.name}: {player.hp}/{player.max_hp} HP | {enemy.name}: {enemy.hp} HP ---")
        print('Що будете робити?')
        for index, skill in enumerate(player.skills):
            print(
                f"{index + 1}. {skill['name']} ({skill['min_dmg']}-{skill['max_dmg']} dmg, {int(skill['chance'] * 100)}%)")
        print('4. Випити зілля 🧪')
        print('5. Пропустити хід 💤')

        try:
            choice = int(input('Ваш вибір: '))
        except ValueError:
            print("Введіть число!")
            continue

        player_turn_success = True

        # Логіка атаки гравця
        if 1 <= choice <= 3:
            skill = player.skills[choice - 1]
            if random.random() <= skill['chance']:
                damage = random.randint(skill['min_dmg'], skill['max_dmg'])
                enemy.hp -= damage
                print(f"🎯 Влучання! Ви нанесли {damage} шкоди.")
            else:
                print("💨 Промах! Монстр виявився спритнішим.")

        elif choice == 4:
            if not player.heal():
                player_turn_success = False  # Якщо зілля немає, гравець має переобрати дію

        elif choice == 5:
            print("💤 Ви вирішили відпочити цей хід.")

        else:
            print("Невірний вибір!")
            player_turn_success = False

        # Хід монстра (якщо він вижив і гравець зробив дію)
        if enemy.is_alive() and player_turn_success:
            monster_dmg = random.randint(int(enemy.power * 0.8), int(enemy.power * 1.2))
            player.hp -= monster_dmg
            print(f"🔥 {enemy.name} атакує і наносить {monster_dmg} шкоди!")

    if not enemy.is_alive():
        print(f"🏆 {enemy.name} переможений!")
        player.gain_exp(50)
        # Шанс знайти зілля після бою
        if random.random() < 0.3:
            player.potions += 1
            print("🧪 Ви знайшли зілля у кишені монстра!")

print('\n' + '=' * 30)
print('💀 ГРУ ЗАВЕРШЕНО! 💀')
print(f'☠️ {player.name} протримався до {player.level} рівня!')



