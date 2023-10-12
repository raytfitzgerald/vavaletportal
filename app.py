#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 16 07:25:42 2023

@author: rayfitzgerald
"""

#pip install flask admin

import sqlite3
from flask import Flask, render_template, jsonify, request, redirect, url_for, Response
from datetime import datetime, timedelta
#from flask_admin import Admin


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vavalet.db'
#admin = Admin(app)

today = datetime.today()
start_of_week = today - timedelta(days=today.weekday())  # This gives Monday of the current week
end_of_week = start_of_week + timedelta(days=6)  # This gives Sunday of the current week
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
NEW_EMPLOYEE_PASSCODE = "vavalet"  # Replace 'YOUR_SECRET_PASSCODE' with your desired passcode.
ADMIN_PASSWORD = "admin"  # Replace with your desired password

def init_db():
    with app.app_context():
        db = sqlite3.connect('vavalet.db')
        cursor = db.cursor()

        # Create employees table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            dob DATE NOT NULL
        )''')

        # Create availability table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS availability (
            id INTEGER PRIMARY KEY,
            employee_id INTEGER,
            week_starting_date DATE NOT NULL,
            day TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            notes TEXT,  
            submission_time TEXT NOT NULL,
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )''')
        

        # Create work_logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS work_logs (
                id INTEGER PRIMARY KEY,
                employee_id INTEGER,
                date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                hours_worked NUMERIC,
                tips_earned NUMERIC,
                location TEXT NOT NULL,
                FOREIGN KEY (employee_id) REFERENCES employees(id)
            )''')
            
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS request_time_off (
                id INTEGER PRIMARY KEY,
                employee_id TEXT NOT NULL,
                name TEXT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                reason TEXT
                )''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
                )''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shift_times (
                id INTEGER PRIMARY KEY,
                day TEXT NOT NULL,
                location TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL
            )''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY,
                shift_time_id INTEGER REFERENCES shift_times(id),
                employee_id INTEGER REFERENCES employees(id),
                UNIQUE(shift_time_id, employee_id)
            )''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS master_schedule (
                id INTEGER PRIMARY KEY,
                shift_time_id INTEGER REFERENCES shift_times(id),
                employee_id INTEGER REFERENCES employees(id),
                week_starting DATE NOT NULL,
                UNIQUE(shift_time_id, employee_id, week_starting)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schedule_metadata (
                id INTEGER PRIMARY KEY,
                last_updated DATETIME
            )
        ''')


        db.commit()
        db.close()

@app.route('/save_shift_time', methods=['POST'])
def save_shift_time():
    day = request.form['day']
    location = request.form['location']
    start_time = request.form['start_time']
    end_time = request.form['end_time']

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO shift_times (day, location, start_time, end_time)
            VALUES (?, ?, ?, ?)
        ''', (day, location, start_time, end_time))
        shift_time_id = cursor.lastrowid
        conn.commit()
        return jsonify(status='success', message='Shift time added successfully!', shift_id=shift_time_id)
    except Exception as e:
        return jsonify(status='error', message=str(e))
    finally:
        conn.close()
        
@app.route('/delete_shift_time', methods=['POST'])
def delete_shift_time():
    shift_id = request.form['shift_id']

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # First, delete any associated assignments to the shift time.
        cursor.execute('DELETE FROM shifts WHERE shift_time_id = ?', (shift_id,))
        
        # Next, delete the shift time itself.
        cursor.execute('DELETE FROM shift_times WHERE id = ?', (shift_id,))
        
        conn.commit()
        return jsonify(status='success', message='Shift time deleted successfully!')
    except Exception as e:
        return jsonify(status='error', message=str(e))
    finally:
        conn.close()

    
@app.route('/assign_employee', methods=['POST'])
def assign_employee():
    shift_time_id = request.form['shift_id']
    employee_name = request.form['employee_name']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get employee_id based on employee_name
    cursor.execute("SELECT id FROM employees WHERE name = ?", (employee_name,))
    employee_id = cursor.fetchone()[0]

    try:
        cursor.execute('''
            INSERT INTO shifts (shift_time_id, employee_id)
            VALUES (?, ?)
        ''', (shift_time_id, employee_id))
        conn.commit()
        return jsonify(status='success', message=f'{employee_name} assigned successfully!')
    except Exception as e:
        return jsonify(status='error', message=str(e))
    finally:
        conn.close()
        
@app.route('/unassign_employee', methods=['POST'])
def unassign_employee():
    shift_id = request.form['shift_id']
    employee_name = request.form['employee_name']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch the employee_id using the employee_name
    cursor.execute('SELECT id FROM employees WHERE name = ?', (employee_name,))
    employee = cursor.fetchone()

    if not employee:
        return jsonify(status='error', message=f'Employee {employee_name} not found!')

    employee_id = employee[0]

    try:
        cursor.execute('DELETE FROM shifts WHERE shift_time_id = ? AND employee_id = ?', (shift_id, employee_id))
        conn.commit()
        return jsonify(status='success', message=f'{employee_name} unassigned successfully!')
    except Exception as e:
        return jsonify(status='error', message=str(e))
    finally:
        conn.close()
        
@app.route('/save_location', methods=['POST'])
def save_location():
    location = request.form.get('location')
    if not location:
        return jsonify({"status": "error", "message": "Location name is required!"})

    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Insert the new location into the locations table
    cursor.execute("INSERT INTO locations (name) VALUES (?)", (location,))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": f"Location {location} added successfully!"})

@app.route('/save_shift', methods=['POST'])
def save_shift():
    day = request.form.get('day')
    location = request.form.get('location')
    employee_name = request.form.get('employee_name')
    shift_time = request.form.get('shift_time')
    
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Insert the new shift into the shifts table
    cursor.execute('''
        INSERT INTO shifts (day, location, employee_id, shift_time)
        VALUES (?, ?, (SELECT id FROM employees WHERE name = ?), ?)
    ''', (day, location, employee_name, shift_time))
    
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Shift added successfully!"})

@app.route('/delete_shift', methods=['POST'])
def delete_shift():
    day = request.form.get('day')
    location = request.form.get('location')
    employee_name = request.form.get('employee_name')
    shift_time = request.form.get('shift_time')
    
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Delete the specified shift from the shifts table
    cursor.execute('''
        DELETE FROM shifts
        WHERE day = ? AND location = ? AND employee_id = (SELECT id FROM employees WHERE name = ?) AND shift_time = ?
    ''', (day, location, employee_name, shift_time))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "Shift deleted successfully!"})

@app.route('/fetch_shifts', methods=['GET'])
def fetch_shifts():
    with sqlite3.connect('vavalet.db') as con:
        cursor = con.cursor()

        # Fetch all shifts
        cursor.execute("SELECT day, location, employee_id, shift_time FROM shifts")
        raw_shift_data = cursor.fetchall()

        shifts_data = {}
        for shift in raw_shift_data:
            day, location, employee_id, shift_time = shift
            if employee_id:
                cursor.execute(f"SELECT name FROM employees WHERE id = {employee_id}")
                employee_name = cursor.fetchone()[0]
            else:
                employee_name = None

            if day not in shifts_data:
                shifts_data[day] = {}
            if location not in shifts_data[day]:
                shifts_data[day][location] = []

            shifts_data[day][location].append({"employee_name": employee_name, "time": shift_time})

    return jsonify(shifts_data)

# Utility function to create a database connection
def get_db_connection():
    conn = sqlite3.connect('vavalet.db')
    conn.row_factory = sqlite3.Row  # This allows us to access rows as dictionaries
    return conn

@app.route('/shifts', methods=['GET', 'POST'])
def shifts():
    with sqlite3.connect('vavalet.db') as con:
        cursor = con.cursor()

        # Fetching all locations and employees
        cursor.execute("SELECT name, id FROM employees")
        all_employees = [{"name": row[0], "id": row[1]} for row in cursor.fetchall()]

        cursor.execute("SELECT name FROM locations")
        locations = [location[0] for location in cursor.fetchall()]

        # Initialize shifts_data with all days and locations
        shifts_data = {day: {location: [] for location in locations} for day in DAYS}

        # Fetch all employees assigned to shifts from the `shifts` table
        cursor.execute('''
            SELECT s.shift_time_id, e.name
            FROM shifts s
            JOIN employees e ON s.employee_id = e.id
        ''')
        employees_for_shifts = cursor.fetchall()
        employees_map = {}
        for shift_time_id, employee_name in employees_for_shifts:
            if shift_time_id not in employees_map:
                employees_map[shift_time_id] = []
            employees_map[shift_time_id].append({"name": employee_name})

        # Fetching all shifts with related data
        cursor.execute('''
            SELECT 
                st.id, st.day, st.location, st.start_time, st.end_time
            FROM shift_times st
        ''')
        raw_shift_data = cursor.fetchall()

        for shift in raw_shift_data:
            shift_id, day, location, start_time, end_time = shift

            # Ensure that the day and location from the database exist in shifts_data
            if day.capitalize() not in shifts_data or location not in shifts_data[day.capitalize()]:
                continue

            # Calculate the actual date for the 'day of the week' based on current date
            date = get_date_for_day_of_week(day)

            # Get a list of available employees for this shift time
            available_employee_ids = get_available_employees(day, start_time, end_time, date)

            # Extracting available employee names
            available_employee_names = [e["name"] for e in all_employees if e["id"] in available_employee_ids]

            # Create a new entry for the shift
            shift_detail = {
                "id": shift_id,
                "start_time": start_time,
                "end_time": end_time,
                "available_employee_names": available_employee_names,
                "employees": employees_map.get(shift_id, [])
            }
            shifts_data[day.capitalize()][location].append(shift_detail)

    return render_template('shifts.html', shifts=shifts_data, days=DAYS, locations=locations)


        
@app.route('/employee_portal', methods=['GET'])
def employee_portal():
    return render_template('employee_portal.html')

@app.route('/employee_submissions', methods=['GET'])
def employee_submissions():
    tables = get_all_tables()
    data = {}
    
    for table in tables:
        columns, records = get_records_from_table(table)
        data[table] = {"columns": columns, "records": records}
        
    return render_template('employee_submissions.html', data=data)

@app.route('/availability_sheet', methods=['GET'])
def availability_sheet():
    availability_data = get_availability_data()
        
    return render_template('availability_sheet.html', availability_data=availability_data)

@app.route('/calendar_view', methods=['GET'])
def calendar_view():
    return render_template('calendar_view.html')

        
def get_all_tables():
    """Return list of table names in the database"""
    conn = sqlite3.connect('vavalet.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    conn.close()
    
    return [table[0] for table in tables]  # Convert list of tuples to list of strings


def get_records_from_table(table_name):
    """Return column names and all records from the specified table"""
    conn = sqlite3.connect('vavalet.db')
    cursor = conn.cursor()
    
    cursor.execute(f"SELECT * FROM {table_name} LIMIT 1;")
    col_names = [desc[0] for desc in cursor.description]
    
    cursor.execute(f"SELECT * FROM {table_name};")
    records = cursor.fetchall()
    
    conn.close()
    
    return col_names, records



@app.route('/view_table/<table_name>')
def view_table(table_name):
    # Retrieve the data for the given table
    col_names, records = get_records_from_table(table_name)
    return render_template('table_view.html', table_columns=col_names, table_data=records, table_name=table_name)


def get_availability_data():
    """Format the availability data for the admin view."""
    conn = sqlite3.connect('vavalet.db')
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT name FROM employees")
    employees = [employee[0] for employee in cursor.fetchall()]

    availability_data = {}
    for employee in employees:
        cursor.execute("SELECT day, start_time, end_time FROM availability WHERE employee_id = (SELECT id FROM employees WHERE name = ?) AND week_starting_date = ?", 
               (employee, start_of_week.strftime('%Y-%m-%d')))
        records = cursor.fetchall()
        if not records:
            availability_data[employee] = "has not completed this week's form"
        else:
            availability_data[employee] = {day: (start, end) for day, start, end in records}

    conn.close()
    return availability_data

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/request_time_off', methods=['GET', 'POST'])
def request_time_off():
    if request.method == 'POST':
        name = request.form['Name']
        dob = request.form['dob']
        start_date = request.form['startDate']
        end_date = request.form['endDate']
        reason = request.form.get('reason', '')  # .get() will default to '' if 'reason' doesn't exist

        # Check if the employee exists in the database
        if not name and dob:
            return "Please complete the name and/or DOB section of the form"
        
        employee_id = get_employee_id(name, dob)
    
        if not employee_id:
            return "No employee found with the name/DOB pair provided."

        # If the employee exists, insert the request into the 'request_time_off' table
        conn = sqlite3.connect('vavalet.db')
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO request_time_off (employee_id, name, start_date, end_date, reason) 
            VALUES (?, ?, ?, ?, ?)''', (employee_id, name, start_date, end_date, reason))
        
        conn.commit()
        conn.close()

        return redirect(url_for('index'))

    return render_template('request_time_off.html')


@app.route('/availability_form', methods=['GET', 'POST'])
def availability_form():
    if request.method == 'POST':
        # Ensure today's date is between Monday and Thursday.
        if today.weekday() < 0 or today.weekday() > 3:
            return "Submissions are only allowed from Monday to Thursday!"
        return submit_availability()

    # Display the week at the top of the form
    week_display = f"{start_of_week.strftime('%Y-%m-%d')} to {end_of_week.strftime('%Y-%m-%d')}"
    return render_template('availability_form.html', week_display=week_display)


@app.route('/log_work_form', methods=['GET', 'POST'])
def log_work_form():
    if request.method == 'POST':
        return log_work()
    return render_template('log_work_form.html')

@app.route('/submit_availability', methods=['POST'])
def submit_availability():
    name = request.form['Name']
    dob = request.form['dob']
    notes = request.form['notes']  # <-- Get the notes from the form

    employee_id = get_employee_id(name, dob)
    
    today = datetime.today()
    start_of_week_2 = today - timedelta(days=today.weekday())  # This gives Monday of the current week


    if not employee_id:
        return "No employee found with the name/DOB pair provided."

    conn = sqlite3.connect('vavalet.db')
    cursor = conn.cursor()
    
    # Delete previous entries for this employee
    cursor.execute('DELETE FROM availability WHERE employee_id = ?', (employee_id,))


    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
        all_day = request.form.get(f'allday_{day.lower()}')
        unavailable_all_day = request.form.get(f'unavailableallday_{day.lower()}')
        
        if all_day:  # If the "Available All Day" checkbox is selected
            start_time = "00:00"
            end_time = "23:59"   
        elif unavailable_all_day:
            start_time = "Unavailable"
            end_time = ""
            cursor.execute('''
                SELECT 1 FROM request_time_off 
                WHERE employee_id = ? 
                AND ? BETWEEN start_date AND end_date
            ''', (employee_id, start_of_week_2.strftime('%Y-%m-%d')))
            
            record_exists = cursor.fetchone()
        
            # If no overlapping record exists, insert the new record
            if not record_exists:
                cursor.execute('''
                    INSERT INTO request_time_off (employee_id, name, start_date, end_date, reason) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (employee_id, name, start_of_week_2.strftime('%Y-%m-%d'), start_of_week_2.strftime('%Y-%m-%d'), "Unavailable all day from availability sheet"))
        else:
            start_time = request.form[f'start_time_{day.lower()}']
            end_time = request.form[f'end_time_{day.lower()}']
            if start_time and not end_time:
                    end_time = "23:59"
            elif end_time and not start_time:
                    start_time = "00:00"
                
            # Capture current time
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        start_of_week_2 += timedelta(days=1)
        cursor.execute('''
            INSERT INTO availability (employee_id, week_starting_date, day, start_time, end_time, notes, submission_time) 
            VALUES (?, ?, ?, ?, ?, ?, ?)''', (employee_id, start_of_week.strftime('%Y-%m-%d'), day, start_time, end_time, notes, current_time))  # <-- Added notes here

    conn.commit()
    conn.close()

        # Collect submitted data for the thank you page
    availability_data = {}
    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
        if request.form.get(f'allday_{day.lower()}'):  
            availability_data[day] = ["00:00", "23:59"]
        else:
            availability_data[day] = [request.form[f'start_time_{day.lower()}'], request.form[f'end_time_{day.lower()}']]
    
    # Render thank you page
    return render_template('thank_you.html', availability=availability_data)


@app.route('/log_work', methods=['POST'])
def log_work():
    name = request.form['name']
    dob = request.form['dob']
    date = request.form['date']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    hours_worked = request.form['hours_worked']
    tips_earned = request.form['tips_earned']
    location = request.form['location']

    if not name and dob and date and start_time and end_time and hours_worked and tips_earned and location:
        return "Please complete the entire form"
    
    employee_id = get_employee_id(name, dob)

    if not employee_id:
        return "No employee found with the name/DOB pair provided."

    conn = sqlite3.connect('vavalet.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO work_logs (employee_id, date, start_time, end_time, hours_worked, tips_earned, location) 
        VALUES (?, ?, ?, ?, ?, ?, ?)''', (employee_id, date, start_time, end_time, hours_worked, tips_earned, location))
    conn.commit()
    conn.close()

    shift_data = {
        'date': request.form['date'],
        'start_time': request.form['start_time'],
        'end_time': request.form['end_time'],
        'hours_worked': request.form['hours_worked'],
        'tips_earned': request.form['tips_earned'],
        'location': request.form['location'],
        # ... any other fields you have ...
    }

    # Render the thank you page with the submitted data
    return render_template('shift_logged.html', shift=shift_data)

@app.route('/get_employees', methods=['GET'])
def get_employees():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM employees")
    employees = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(employees)



def get_employee_id(name, dob):
    """Return employee id if exists else return None"""
    conn = sqlite3.connect('vavalet.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM employees WHERE name = ? AND dob = ?', (name, dob,))
    employee = cursor.fetchone()
    
    conn.close()
    
    if not employee:
        return None
    
    return employee[0]

@app.route('/get_time_off_requests', methods=['GET'])
def get_time_off_requests():
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    # Fetch requests from the database between the start and end dates
    conn = sqlite3.connect('vavalet.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT name, start_date, end_date, reason FROM request_time_off WHERE start_date >= ? AND end_date <= ?", (start_date, end_date))
    requests = cursor.fetchall()
    
    conn.close()
    
    # Convert to a format suitable for the frontend
    result = [{"title": f"{row[0]} - {row[3]}", "start": row[1], "end": row[2]} for row in requests]
    
    return jsonify(result)

@app.route('/new_employee', methods=['GET'])
def new_employee():
    return render_template('new_employee.html')

@app.route('/add_employee', methods=['POST'])
def add_employee():
    name = request.form['name']
    dob = request.form['dob']
    passcode = request.form['passcode']

    if passcode != NEW_EMPLOYEE_PASSCODE:
        return "Invalid passcode. Please try again."

    conn = sqlite3.connect('vavalet.db')
    cursor = conn.cursor()

    cursor.execute("INSERT INTO employees (name, dob) VALUES (?, ?)", (name, dob))
    conn.commit()
    conn.close()

    return "Employee added successfully!"

@app.route('/admin_login', methods=['GET'])
def admin_login():
    return render_template('admin_login.html')



@app.route('/admin_check', methods=['POST'])
def admin_check():
    entered_password = request.form['password']

    if entered_password == ADMIN_PASSWORD:
        return redirect(url_for('admin_view'))
    else:
        return "Invalid admin password. Please try again.", 401

@app.route('/admin_view')
def admin_view():
    table_names = get_all_tables()
    return render_template('admin_view.html', tables=table_names)

def get_available_employees(day, start_time, end_time, date):
    """
    Get a list of employees available for a specific shift time.

    Parameters:
    - day: Day of the week (e.g., "Monday")
    - start_time: Start time of the shift (e.g., "09:00")
    - end_time: End time of the shift (e.g., "17:00")
    - date: Actual date for the day of the week (e.g., "2023-09-29")

    Returns:
    - A list of available employee IDs.
    """
    
    # Connect to the SQLite database
    conn = sqlite3.connect('vavalet.db')
    cursor = conn.cursor()
    
    day = day.capitalize()

    # 1. Filtering by Availability:
    cursor.execute('''
        SELECT employee_id FROM availability 
        WHERE day = ? 
        AND start_time <= ? 
        AND end_time >= ?''', (day, start_time, end_time))
    available_employees = [row[0] for row in cursor.fetchall()]
    #print("After availability filter:", available_employees, 'day:', day, 'start time:', start_time, 'end_time:', end_time)

    day = day.lower()
    # 2. Filtering by Existing Shifts:
    cursor.execute('''
        SELECT DISTINCT s.employee_id 
        FROM shifts s
        JOIN shift_times st ON s.shift_time_id = st.id
        WHERE st.day = ?
        AND (
            (st.start_time <= ? AND st.end_time >= ?) OR
            (st.start_time BETWEEN ? AND ?) OR 
            (st.end_time BETWEEN ? AND ?) OR
            (st.start_time >= ? AND st.end_time <= ?)
        )
        ''',((day, start_time, end_time, start_time, end_time, start_time, end_time, start_time, end_time)))
    busy_employees = [row[0] for row in cursor.fetchall()]
    for emp in busy_employees:
        if emp in available_employees:
            available_employees.remove(emp)

    # 3. Filtering by Time Off Requests:
    # Check the 'request_time_off' table to see if the shift date is between any start_date and end_date for an employee
    cursor.execute('''
        SELECT employee_id FROM request_time_off
        WHERE ? BETWEEN start_date AND end_date''',
        (date,))
    time_off_employees = [row[0] for row in cursor.fetchall()]
    for emp in time_off_employees:
        if emp in available_employees:
            available_employees.remove(emp)

    conn.close()
    return available_employees


def get_date_for_day_of_week(target_day):
    current_day = datetime.now().weekday()
    days = {
        'Monday': 0,
        'Tuesday': 1,
        'Wednesday': 2,
        'Thursday': 3,
        'Friday': 4,
        'Saturday': 5,
        'Sunday': 6
    }
    target_day_index = days[target_day.capitalize()]
    days_difference = target_day_index - current_day + 7  # Adding 7 to move to the next week
    target_date = datetime.now() + timedelta(days=days_difference)
    return target_date.date()

@app.route('/master_schedule')
def master_schedule():
    days = [day.lower() for day in DAYS]
    monday_of_week = today - timedelta(days=today.weekday())

    with sqlite3.connect('vavalet.db') as con:
        cursor = con.cursor()

        # Fetch all employees and locations
        cursor.execute("SELECT name FROM employees")
        all_employees = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT name FROM locations")
        all_locations = [row[0] for row in cursor.fetchall()]

        # Fetch all shifts with related data directly from master_schedule
        cursor.execute('''
            SELECT 
                st.day, st.location, st.start_time, st.end_time, e.name
            FROM master_schedule ms
            JOIN shift_times st ON ms.shift_time_id = st.id
            JOIN employees e ON ms.employee_id = e.id
        ''')
        raw_shift_data = cursor.fetchall()

        # Initialize data structures with all employees and locations
        location_schedule = {loc: {day: [] for day in days} for loc in all_locations}
        employee_schedule = {emp: {day: [] for day in days} for emp in all_employees}

        for shift in raw_shift_data:
            day, location, start_time, end_time, employee_name = shift

            # Populate the location-based view:
            if employee_name:  # Check if an employee is assigned to the shift
                location_schedule[location][day].append({
                    'employee': employee_name,
                    'time': f"{start_time} - {end_time}"
                })

            # Populate the employee-based view:
            if employee_name:  # Check if an employee is assigned to the shift
                employee_schedule[employee_name][day].append({
                    'location': location,
                    'time': f"{start_time} - {end_time}"
                })

        cursor.execute('SELECT last_updated FROM schedule_metadata WHERE id = 1')
        last_updated = cursor.fetchone()

    return render_template('master_schedule.html',
                           location_schedule=location_schedule,
                           employee_schedule=employee_schedule,
                           days=DAYS,
                           week_starting=monday_of_week,
                           last_updated=last_updated[0] if last_updated else None)

@app.route('/update_schedule', methods=['POST'])
def update_schedule():
    monday_of_week = today - timedelta(days=today.weekday())
    
    with sqlite3.connect('vavalet.db') as con:
        cursor = con.cursor()
        
        # Update the last_updated timestamp
        current_timestamp = datetime.now()
        cursor.execute('''
            INSERT OR REPLACE INTO schedule_metadata (id, last_updated)
            VALUES (1, ?)
        ''', (current_timestamp,))
        con.commit()

        # Delete all entries from the master_schedule table
        cursor.execute('DELETE FROM master_schedule')

        # Copy all entries from the shifts table to the master_schedule table
        cursor.execute('''
            INSERT INTO master_schedule (shift_time_id, employee_id, week_starting)
            SELECT shift_time_id, employee_id, ?
            FROM shifts 
        ''', (monday_of_week,))
        con.commit()

    # After updating, redirect to the shifts page
    return redirect(url_for('shifts'))

@app.route('/clear_schedule', methods=['POST'])
def clear_schedule():
    with sqlite3.connect('vavalet.db') as con:
        cursor = con.cursor()
        
        # Remove all employees from the shifts table
        cursor.execute('DELETE FROM shifts')
        con.commit()

    # Redirect back to the shifts page after clearing
    return redirect(url_for('shifts'))

@app.route('/export_location_schedule_csv')
def export_location_schedule_csv():
    
    with sqlite3.connect('vavalet.db') as con:
        cursor = con.cursor()

        # Your existing query to fetch shifts
        cursor.execute('''
            SELECT 
                st.day, st.location, st.start_time, st.end_time, e.name
            FROM master_schedule ms
            JOIN shift_times st ON ms.shift_time_id = st.id
            JOIN employees e ON ms.employee_id = e.id
        ''')
        raw_shift_data = cursor.fetchall()

        csv_content = "Day,Location,Start Time,End Time,Employee\n"
        for shift in raw_shift_data:
            csv_content += ",".join(map(str, shift)) + "\n"

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=location_schedule.csv"}
    )

@app.route('/export_employee_schedule_csv')
def export_employee_schedule_csv():
    
    with sqlite3.connect('vavalet.db') as con:
        cursor = con.cursor()

        # Your existing query to fetch shifts
        cursor.execute('''
            SELECT 
                st.day, st.location, st.start_time, st.end_time, e.name
            FROM master_schedule ms
            JOIN shift_times st ON ms.shift_time_id = st.id
            JOIN employees e ON ms.employee_id = e.id
        ''')
        raw_shift_data = cursor.fetchall()

        # Process the raw data into the employee-based view
        employee_schedule = {}
        for shift in raw_shift_data:
            day, location, start_time, end_time, employee_name = shift
            if employee_name not in employee_schedule:
                employee_schedule[employee_name] = {}
            if day not in employee_schedule[employee_name]:
                employee_schedule[employee_name][day] = []
            employee_schedule[employee_name][day].append({
                'location': location,
                'time': f"{start_time} - {end_time}"
            })

        # Convert the employee schedule data into CSV content
        csv_content = "Employee,Day,Location,Time\n"
        for employee_name, days_data in employee_schedule.items():
            for day, shifts in days_data.items():
                for shift in shifts:
                    csv_content += f"{employee_name},{day},{shift['location']},{shift['time']}\n"

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=employee_schedule.csv"}
    )



if __name__ == '__main__':
    init_db()  # Initialize the database
    app.run(debug=True)

