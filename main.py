import random 
from flask import Flask, render_template, jsonify
import csv
import os


class Database:
    """Class to manage all database-related data"""
    
    FIRST_NAMES = [


    DEPARTMENTS = ["Computer science", "Electronics and communication", "IT", "Mechanical engineering", "Chemical engineering", "biomedical engineering", "Robotics and IOT", "Civil engineering", "Electrical engineering"]
    SECTIONS = ["A", "B", "C", "D", "E", "F"]


class Student:
    """Class to represent a student"""
    
    def __init__(self, start=22002903100, count=100_00000):
        self.start = start
        self.count = count
        self.roll_numbers = [str(start + i) for i in range(count)]
    
    def generate_student(self):
        """Generate random student data"""
        names = f"{random.choice(Database.FIRST_NAMES)} {random.choice(Database.LAST_NAMES)}"
        department = random.choice(Database.DEPARTMENTS)
        section = random.choice(Database.SECTIONS)
        roll_number = random.choice(self.roll_numbers)
        attendance = round(random.uniform(70, 100), 2)
        
        return {
            "name": names,
            "department": department,
            "section": section,
            "roll_number": roll_number,
            "attendance": attendance
        }


class StudentApp:
    """Main Flask application for managing students"""
    
    def __init__(self):
        self.app = Flask(__name__)
        self.student = Student()
        self.setup_routes()
    
    def setup_routes(self):
        """Setup Flask routes"""
        @self.app.route('/')
        def index():
            return render_template('index.html')
        
        @self.app.route('/api/student', methods=['GET'])
        def get_student():
            return jsonify(self.student.generate_student())
    
    def run(self, debug=False, host='localhost', port=5000):
        """Run the Flask application"""
        self.app.run(debug=debug, host=host, port=port)


if __name__ == '__main__':
    app = StudentApp()
    app.run(debug=True) 