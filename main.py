import random 
from flask import Flask, render_template, jsonify
import csv
import os
import flask

app = Flask(__name__)

start = 22002903100
count = 100_00000

first_names = [
    # --- Indian (100) ---
    "Aarav","Vivaan","Aditya","Arjun","Ishaan","Kabir","Vihaan","Atharv","Reyansh","Krish",
    "Rudra","Om","Aadi","Advait","Armaan","Rohan","Rohit","Nikhil","Siddharth","Dhruv",
    "Kunal","Veer","Pranav","Harsh","Yash","Varun","Abhinav","Shaurya","Tejas","Dev",
    "Keshav","Nakul","Lakshya","Ayush","Tanmay","Neel","Parth","Aniket","Samar","Aarush",
    "Jai","Uday","Sanjay","Sameer","Sumit","Amit","Sandeep","Deepak","Rajesh","Rakesh",
    "Prakash","Sunil","Anil","Ashish","Pankaj","Vineet","Vikas","Vinay","Vipin","Gaurav",
    "Rajat","Abhishek","Mayank","Mohit","Manoj","Saurabh","Shubham","Akash","Alok","Ankit",
    "Piyush","Raj","Rahul","Tarun","Tushar","Vimal","Viren","Viraj","Yuvraj","Zubin",
    "Aanya","Ananya","Anika","Anushka","Aishwarya","Priya","Neha","Riya","Rhea","Diya",
    "Isha","Ishita","Kavya","Kriti","Meera","Naina","Nandini","Radhika","Sakshi","Shreya",

    # --- Arabic (100) ---
    "Ahmed","Muhammad","Mohammed","Ahmad","Omar","Umar","Ali","Hassan","Hussein","Yusuf",
    "Youssef","Yasin","Ibrahim","Ismail","Khalid","Khaled","Saad","Faisal","Fahad","Imran",
    "Salman","Bilal","Zaid","Zayd","Zain","Zayn","Hamza","Tariq","Nasser","Nasir",
    "Majid","Anas","Ayman","Ayub","Bashir","Basim","Jamal","Jamil","Karim","Kareem",
    "Kamal","Khalil","Latif","Malik","Sami","Samir","Rami","Rayyan","Rashid","Sabir",
    "Shakir","Wael","Walid","Waleed","Yahya","Zakaria","Zakariya","Mustafa","Mostafa","Nabil",
    "Nadeem","Ridwan","Rafiq","Habib","Hakim","Idris","Ilyas","Junaid","Khalifa","Luqman",
    "Marwan","Mazen","Mehdi","Munir","Nizar","Qasim","Sadiq","Suleiman","Sulaiman","Taha",
    "Aisha","Ayesha","Fatima","Maryam","Mariam","Khadija","Zainab","Salma","Samira","Layla",
    "Leila","Noor","Noura","Huda","Hana","Amal","Amira","Rania","Reem","Dina",

    # --- US/Anglophone (100) ---
    "James","John","Robert","Michael","William","David","Richard","Joseph","Thomas","Charles",
    "Christopher","Daniel","Matthew","Anthony","Mark","Steven","Paul","Andrew","Joshua","Kevin",
    "Brian","George","Timothy","Edward","Jason","Jeffrey","Ryan","Jacob","Nicholas","Eric",
    "Jonathan","Stephen","Larry","Justin","Brandon","Benjamin","Adam","Samuel","Alexander","Jack",
    "Tyler","Aaron","Henry","Peter","Nathan","Zachary","Kyle","Jeremy","Ethan","Logan",
    "Mary","Patricia","Jennifer","Linda","Elizabeth","Barbara","Susan","Jessica","Sarah","Karen",
    "Nancy","Lisa","Margaret","Ashley","Emily","Michelle","Carol","Amanda","Melissa","Stephanie",
    "Rebecca","Laura","Cynthia","Amy","Angela","Helen","Anna","Nicole","Katherine","Samantha",
    "Emma","Olivia","Sophia","Isabella","Ava","Mia","Charlotte","Abigail","Harper","Evelyn",
    "Grace","Chloe","Lily","Ella","Scarlett","Aria","Penelope","Nora","Riley","Zoe"
]

last_names = [
    # --- Indian (100) ---
    "Sharma","Verma","Gupta","Agarwal","Mehta","Shah","Patel","Singh","Kaur","Kumar",
    "Reddy","Rao","Iyer","Iyengar","Menon","Nair","Pillai","Shetty","Gowda","Naidu",
    "Yadav","Choudhary","Chaudhary","Choudhury","Chatterjee","Mukherjee","Banerjee","Ghosh","Bose","Sen",
    "Saha","Das","Dutta","Datta","Roy","Pal","Srivastava","Tripathi","Tiwari","Dubey",
    "Pandey","Mishra","Shukla","Saxena","Chaurasia","Pathak","Upadhyay","Bhatt","Bhattacharya","Bhatnagar",
    "Kulkarni","Deshmukh","Deshpande","Joshi","Patil","Jadhav","Shinde","Gaikwad","Pawar","Chavan",
    "More","Salunkhe","Waghmare","Bansal","Goel","Jain","Khandelwal","Maheshwari","Laddha","Somani",
    "Singhania","Poddar","Jalan","Lodha","Mittal","Narang","Malhotra","Kapoor","Khanna","Mehra",
    "Bedi","Bhatia","Anand","Arora","Ahuja","Duggal","Gulati","Oberoi","Puri","Soni",
    "Sood","Talwar","Wadhwa","Ahluwalia","Chawla","Gill","Grewal","Sandhu","Sidhu","Dhillon",

    # --- Arabic / MENA & South Asian Muslim (100) ---
    "Ahmed","Mohammed","Ali","Hassan","Hussein","Ibrahim","Ismail","Khalid","Khalil","Karim",
    "Saleh","Salem","Said","Saeed","Hamdan","Hamid","Farah","Fadel","Habib","Hakim",
    "Mansour","Mahmoud","Mustafa","Mostafa","Nasser","Nasir","Najjar","Naji","Qasim","Qureshi",
    "Siddiqui","Ansari","Khan","Sheikh","Shaikh","Mirza","Baig","Syed","Rizvi","Naqvi",
    "Zaidi","Kazmi","Hashmi","Haider","Hussain","Noor","Rahman","Rehman","Rahim","Azhar",
    "Awan","Butt","Chaudhry","Dar","Darwish","Issa","Jaber","Jamal","Jamil","Jawad",
    "Kabir","Kader","Latif","Luqman","Majeed","Malik","Mir","Naveed","Omar","Osman",
    "Qadir","Sabri","Saber","Safi","Sadiq","Salim","Sami","Shafi","Shakil","Shakir",
    "Suleiman","Taha","Tahir","Tariq","Wali","Yasin","Zaman","Zayed","Zaki","Faruqi",

    # --- US/Anglophone (100) ---
    "Smith","Johnson","Williams","Brown","Jones","Miller","Davis","Garcia","Rodriguez","Martinez",
    "Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas","Taylor","Moore","Jackson","Martin",
    "Lee","Perez","Thompson","White","Harris","Sanchez","Clark","Ramirez","Lewis","Robinson",
    "Walker","Young","Allen","King","Wright","Scott","Torres","Nguyen","Hill","Flores",
    "Green","Adams","Nelson","Baker","Hall","Rivera","Campbell","Mitchell","Carter","Roberts",
    "Gomez","Phillips","Evans","Turner","Diaz","Parker","Cruz","Edwards","Collins","Reyes",
    "Stewart","Morris","Morales","Murphy","Cook","Rogers","Gutierrez","Ortiz","Morgan","Cooper",
    "Peterson","Bailey","Reed","Kelly","Howard","Ramos","Kim","Cox","Ward","Richardson",
    "Watson","Brooks","Wood","James","Bennett","Gray","Mendoza","Ruiz","Hughes","Price",
    "Alvarez","Castillo","Sanders","Patel","Myers","Long","Ross","Foster","Powell","Jenkins"
]

departments = ["Computer science", "Electronics and communication", "IT", "Mechanical engineering", "Chemical engineering","biomedical engineering", "Robotics and IOT", "Civil engineering", "Electrical engineering"]
Sections = ["A", "B", "C", "D", "E","F"]
roll_numbers = [str(start + i) for i in range(count)]

def main():
    names = f"{random.choice(first_names)} {random.choice(last_names)}"
    depts = f"{random.choice(departments)}"
    section = f"{random.choice(Sections)}"    
    rollnum = f"{random.choice(roll_numbers)}"
    attendance = round(random.uniform(70, 100), 2)  
    print(f"The student named {names} from the {depts} department, roll number {rollnum}, section {section}, has an attendance of {attendance}%.")
    
#api endpoints to get students 
@app.route('/api/students')
def get_students_api():
    students = get_students()
    return jsonify(students)

#we will use this as frontend route to display student 
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True) 