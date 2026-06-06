import random

name = input("Ім'я героя: ")

level = 1
xp = 0
gold = 20

max_hp = 100
hp = max_hp

attack = 10

inventory = ["Зілля"]

def stats():
    print("\n-------------------------")
    print("Герой:", name)
    print("Рівень:", level)
    print("XP:", xp)
    print("HP:", hp, "/", max_hp)
    print("Атака:", attack)
    print("Золото:", gold)
    print("Інвентар:", inventory)
    print("-------------------------")

def level_up():
    global level, xp, max_hp, hp, attack

    while xp >= level * 50:
        level += 1
        max_hp += 20
        hp = max_hp
        attack += 3

        print("\nНовий рівень:", level)

def battle():
    global hp, gold, xp

    monsters = [
        ["Скелет", 30, 7, 15],
        ["Гоблін", 40, 10, 20],
        ["Орк", 60, 12, 30],
        ["Тролль", 80, 15, 40]
    ]

    monster = random.choice(monsters)

    m_name = monster[0]
    m_hp = monster[1]
    m_attack = monster[2]
    reward = monster[3]

    print("\nВорог:", m_name)

    while m_hp > 0 and hp > 0:

        print("\nВаш HP:", hp)
        print(m_name, "HP:", m_hp)

        print("1. Атака")
        print("2. Зілля")

        choice = input("> ")

        if choice == "1":
            dmg = random.randint(
                attack - 2,
                attack + 5
            )

            m_hp -= dmg

            print("Шкода:", dmg)

        elif choice == "2":

            if "Зілля" in inventory:
                inventory.remove("Зілля")

                heal = 30
                hp += heal

                if hp > max_hp:
                    hp = max_hp

                print("Відновлено", heal)

            else:
                print("Немає зілля")
                continue

        if m_hp > 0:
            enemy = random.randint(
                m_attack - 2,
                m_attack + 2
            )

            hp -= enemy

            print("Отримано шкоди:", enemy)

    if hp > 0:
        print("Перемога!")

        gold += reward
        xp += reward

        level_up()

def treasure():
    global gold

    found = random.randint(10, 50)

    gold += found

    print("Знайдено золото:", found)

def potion():
    inventory.append("Зілля")

    print("Знайдено зілля")

def trap():
    global hp

    damage = random.randint(5, 20)

    hp -= damage

    print("Пастка:", damage)

def merchant():
    global gold

    print("\n1. Купити зілля (15)")
    print("2. Купити меч (50)")
    print("3. Вийти")

    choice = input("> ")

    if choice == "1":

        if gold >= 15:
            gold -= 15
            inventory.append("Зілля")

        else:
            print("Недостатньо золота")

    elif choice == "2":

        global attack

        if gold >= 50:
            gold -= 50
            attack += 5

        else:
            print("Недостатньо золота")

def heal_room():
    global hp

    hp += 25

    if hp > max_hp:
        hp = max_hp

    print("Відновлено 25 HP")

def boss():
    global hp, gold, xp

    boss_hp = 150

    print("\nБОС: ДРАКОН")

    while boss_hp > 0 and hp > 0:

        print("\nВаш HP:", hp)
        print("Дракон HP:", boss_hp)

        print("1. Атака")
        print("2. Зілля")

        choice = input("> ")

        if choice == "1":

            dmg = random.randint(
                attack,
                attack + 8
            )

            boss_hp -= dmg

            print("Шкода:", dmg)

        elif choice == "2":

            if "Зілля" in inventory:
                inventory.remove("Зілля")

                hp += 30

                if hp > max_hp:
                    hp = max_hp

            else:
                print("Немає зілля")
                continue

        if boss_hp > 0:

            enemy = random.randint(12, 22)

            hp -= enemy

            print("Дракон атакує:", enemy)

    if hp > 0:
        print("\nДракон переможений!")
        gold += 200
        xp += 200

rooms = 0

while hp > 0:

    rooms += 1

    stats()

    if rooms == 10:
        boss()
        break

    event = random.randint(1, 7)

    if event == 1:
        battle()

    elif event == 2:
        treasure()

    elif event == 3:
        potion()

    elif event == 4:
        trap()

    elif event == 5:
        merchant()

    elif event == 6:
        heal_room()

    else:
        print("Порожня кімната")

if hp <= 0:
    print("\nГру завершено")

else:
    print("\nВітаємо!")
    print("Підземелля пройдено!")

print("\nПідсумок")
print("Герой:", name)
print("Рівень:", level)
print("XP:", xp)
print("Золото:", gold)
