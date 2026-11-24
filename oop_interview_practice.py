# ============================================================
# Advanced OOP Interview Practice
# Revision-friendly version with comments
# ============================================================

# Python OOP concepts covered:
# 1. Class and object
# 2. Encapsulation
# 3. Inheritance
# 4. Method overriding
# 5. Abstraction
# 6. Polymorphism
# 7. Multiple inheritance
# 8. Composition
# 9. Static methods
# 10. Class methods
# 11. Dunder methods
# 12. Custom exception handling

from abc import ABC, abstractmethod
from datetime import datetime


# Custom exception: used to validate invalid inputs
class ValidationError(Exception):
    pass


# ============================================================
# Person class: base class for all people
# - class variable
# - constructor (__init__)
# - class method
# - dunder methods __str__ and __repr__
# ============================================================
class Person:
    person_count = 0  # class variable shared by all Person objects

    def __init__(self, name, age, email):
        # Validation: object cannot be created with invalid data
        if not name.strip():
            raise ValidationError("Name cannot be empty")
        if age <= 0:
            raise ValidationError("Age must be positive")
        if "@" not in email:
            raise ValidationError("Invalid email")

        self.name = name
        self.age = age
        self.email = email
        Person.person_count += 1

    @classmethod
    def get_person_count(cls):
        # This method accesses class-level data, not instance data
        return cls.person_count

    def display(self):
        # Example of instance method
        return f"Person(name={self.name}, age={self.age}, email={self.email})"

    def __str__(self):
        # String representation for print()
        return self.display()

    def __repr__(self):
        # Developer-friendly representation
        return self.display()


# ============================================================
# Employee inherits from Person
# - demonstrates inheritance
# - encapsulation using private attribute
# - property setter/getter
# - overriding display() method
# - __eq__ dunder method
# ============================================================
class Employee(Person):
    def __init__(self, name, age, email, emp_id, salary):
        super().__init__(name, age, email)  # calls parent constructor
        self.emp_id = emp_id
        self.__salary = salary  # private attribute (encapsulation)

    @property
    def salary(self):
        # getter for private attribute
        return self.__salary

    @salary.setter
    def salary(self, value):
        # setter validates data before assignment
        if value < 0:
            raise ValidationError("Salary cannot be negative")
        self.__salary = value

    def calculate_bonus(self):
        # Base implementation for Employee
        return self.__salary * 0.10

    def display(self):
        # Method overriding: child class changes behavior
        return (
            f"Employee(emp_id={self.emp_id}, name={self.name}, "
            f"age={self.age}, email={self.email}, salary={self.__salary})"
        )

    def __eq__(self, other):
        # Dunder method for comparison
        if isinstance(other, Employee):
            return self.emp_id == other.emp_id and self.email == other.email
        return False


# ============================================================
# Manager inherits from Employee
# - overrides calculate_bonus()
# - demonstrates polymorphism
# ============================================================
class Manager(Employee):
    def __init__(self, name, age, email, emp_id, salary, department):
        super().__init__(name, age, email, emp_id, salary)
        self.department = department

    def calculate_bonus(self):
        # Overridden method: Manager gets higher bonus
        return self.salary * 0.20

    def display(self):
        return (
            f"Manager(emp_id={self.emp_id}, name={self.name}, "
            f"department={self.department}, salary={self.salary})"
        )


# ============================================================
# Developer inherits from Employee
# - another overridden method
# - demonstrates polymorphism
# ============================================================
class Developer(Employee):
    def __init__(self, name, age, email, emp_id, salary, tech_stack):
        super().__init__(name, age, email, emp_id, salary)
        self.tech_stack = tech_stack

    def calculate_bonus(self):
        # Different implementation from Manager
        return self.salary * 0.15

    def display(self):
        return (
            f"Developer(emp_id={self.emp_id}, name={self.name}, "
            f"tech_stack={self.tech_stack}, salary={self.salary})"
        )


# ============================================================
# Abstract class (Abstraction)
# - Role is abstract because assign_task() must be implemented
# ============================================================
class Role(ABC):
    @abstractmethod
    def assign_task(self):
        pass


# ============================================================
# TeamLead uses multiple inheritance
# - inherits from Manager and Role
# - demonstrates multiple inheritance
# ============================================================
class TeamLead(Manager, Role):
    def __init__(self, name, age, email, emp_id, salary, department):
        super().__init__(name, age, email, emp_id, salary, department)

    def assign_task(self):
        # Must implement abstract method from Role
        return f"{self.name} assigned sprint planning task"

    def manage_team(self):
        return f"{self.name} is leading {self.department}"


# ============================================================
# Department class: demonstrates composition
# - Department contains employees
# ============================================================
class Department:
    def __init__(self, name):
        self.name = name
        self.employees = []

    def add_employee(self, employee):
        # Composition: Department owns employee references
        self.employees.append(employee)

    def get_employee_count(self):
        return len(self.employees)

    def total_salary(self):
        return sum(emp.salary for emp in self.employees)


# ============================================================
# Company class: also demonstrates composition
# - Company contains departments
# ============================================================
class Company:
    def __init__(self, name):
        self.name = name
        self.departments = []

    def add_department(self, department):
        self.departments.append(department)

    def get_all_employees(self):
        employees = []
        for dept in self.departments:
            employees.extend(dept.employees)
        return employees

    def company_total_salary(self):
        total = 0
        for dept in self.departments:
            total += dept.total_salary()
        return total


# ============================================================
# Payroll class: static method
# - no instance needed
# ============================================================
class Payroll:
    @staticmethod
    def generate_salary_slip(employee):
        # Static method: utility method independent of instance
        return {
            "name": employee.name,
            "emp_id": employee.emp_id,
            "salary": employee.salary,
            "bonus": employee.calculate_bonus(),
            "total": employee.salary + employee.calculate_bonus(),
            "date": datetime.now().strftime("%Y-%m-%d")
        }


# ============================================================
# Demo section
# ============================================================
if __name__ == "__main__":
    try:
        # Build a few employees
        emp1 = Developer("Ravi", 28, "ravi@gmail.com", "E101", 90000, ["Python", "SQL"])
        emp2 = Manager("Neha", 32, "neha@gmail.com", "E102", 120000, "Engineering")
        lead = TeamLead("Amit", 35, "amit@gmail.com", "E103", 150000, "Engineering")

        # Create department and add employees
        dept = Department("Engineering")
        dept.add_employee(emp1)
        dept.add_employee(emp2)
        dept.add_employee(lead)

        # Create company and add department
        company = Company("TechNova")
        company.add_department(dept)

        # Display object info
        print(emp1)
        print(emp2)
        print(lead)

        # Polymorphism: same method name with different behavior
        print("\nBonus:")
        print(emp1.calculate_bonus())
        print(emp2.calculate_bonus())
        print(lead.calculate_bonus())

        # Total salary check
        print("\nDepartment total salary:", dept.total_salary())
        print("Company total salary:", company.company_total_salary())

        # Static method usage
        print("\nPayroll slip:")
        print(Payroll.generate_salary_slip(emp1))

        # Class method usage
        print("\nEmployee count:", Person.get_person_count())

        # Equality comparison using __eq__
        print("\nEquality check:")
        print(emp1 == Developer("Ravi", 28, "ravi@gmail.com", "E101", 90000, ["Python", "SQL"]))

        # Abstract method implementation in TeamLead
        print("\nTeam lead task:")
        print(lead.assign_task())

    except ValidationError as e:
        print("Validation Error:", e)
