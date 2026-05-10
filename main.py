#OOP

class Human:
   def __init__(self, name, age):
       self.name = name
       self.age = age

   def say_hi(self):
        print(f'Привіт, мене звуть {self.name}. Мені {self.age} років.')

   def birthday(self):
       self.age +=1
       print(f'Людині {self.name} виповнилося {self.age} років! ')

class Student(Human):
       def __init__(self, name, age, grades):
            super().__init__(name, age)
            self.grades = grades

       def say_hi(self):
           print(f'Привіт, я студент {self.name}! Мої оцінки: {self.grades}')

class Auto:
    def __init__(self):
        self.passengers = []

    def add_passenger(self, passenger):
        if passenger in self.passengers:
            print(f"Пасажир {passenger.name} вже в Авто!")
            return
        self.passengers.append(passenger)

    def print_all(self):
        print('----Всі пасажипм авто:----')
        for passenger in self.passengers:
            passenger.say_hi()
        print('----------------------')



john = Student('Джон', 25, [10, 12, 8, 10, 9, 8, 10])
bob = Human("Bob", 30)
anna = Human("Anna", 20)

john.birthday()
john.say_hi()

for i in range(5):
    bob.birthday()


bob.say_hi()
anna.say_hi()

bmw = Auto()
bmw.add_passenger(john)
bmw.add_passenger(john)
bmw.add_passenger(bob)

bmw.print_all()

