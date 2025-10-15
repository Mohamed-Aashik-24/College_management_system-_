from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import pymysql
from pymysql.err import OperationalError, IntegrityError
from datetime import datetime
import traceback
import uuid
from functools import wraps
import os

# NOTE: Use environment variables for any sensitive values. Defaults are intentionally
# non-secret placeholders so credentials are not committed in the repository.
app = Flask(__name__)
CORS(app)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    # Do NOT store real passwords in source. Set DB_PASSWORD in the environment.
    'password': os.getenv('DB_PASSWORD', '<REDACTED_PASSWORD>'),
    'database': os.getenv('DB_NAME', 'smart_exam_cell'),
    'port': int(os.getenv('DB_PORT', 3306))
}

def seed_departments_if_missing():
    """Ensure default departments exist: CSE, IT, AIDS, ECE."""
    connection = get_db_connection()
    if not connection:
        return
    try:
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS department (
                dept_id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100) UNIQUE NOT NULL
            )
        """)

        default_departments = [
            ('CSE',),
            ('IT',),
            ('AIDS',),
            ('ECE',)
        ]

        cursor.executemany(
            "INSERT IGNORE INTO department (name) VALUES (%s)",
            default_departments
        )
        connection.commit()
    except Exception:
        pass
    finally:
        try:
            cursor.close()
            connection.close()
        except Exception:
            pass

def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            port=DB_CONFIG['port']
        )
        print("Database connection successful")
        return connection
    except OperationalError as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# Ensure score table exists with a minimal schema
def ensure_score_table_if_missing():
    connection = get_db_connection()
    if not connection:
        return
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS score (
                score_id INT PRIMARY KEY AUTO_INCREMENT,
                student_id VARCHAR(50) NOT NULL,
                course_id INT NOT NULL,
                score DECIMAL(5,2) NOT NULL,
                semester VARCHAR(20),
                exam_date DATE,
                INDEX idx_score_student (student_id)
            )
            """
        )
        connection.commit()
    except Exception:
        pass
    finally:
        try:
            cursor.close()
            connection.close()
        except Exception:
            pass

# ==================== Authentication ====================

SESSIONS = {}

def get_current_user():
    """Extract user from Bearer token in Authorization header."""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header.split(' ', 1)[1].strip()
    return SESSIONS.get(token)

def require_roles(*allowed_roles):
    """Decorator to enforce role-based access control."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if user is None:
                return jsonify({'error': 'Unauthorized'}), 401
            if allowed_roles and user.get('role') not in allowed_roles:
                return jsonify({'error': 'Forbidden'}), 403
            return func(*args, **kwargs)
        return wrapper
    return decorator

@app.route('/api/login', methods=['POST'])
def login():
    """Handle user login"""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        # Demo users (passwords redacted). For real deployments, integrate with
        # a proper user store and do NOT keep passwords in source control.
        valid_users = {
            'admin@college.edu': {'password': '<REDACTED_PASSWORD>', 'role': 'admin', 'name': 'Admin User'},
            'faculty@college.edu': {'password': '<REDACTED_PASSWORD>', 'role': 'faculty', 'name': 'Faculty User'},
            'student@college.edu': {'password': '<REDACTED_PASSWORD>', 'role': 'student', 'name': 'Student User'}
        }
        
        if email in valid_users and valid_users[email]['password'] == password:
            token = uuid.uuid4().hex
            SESSIONS[token] = {
                'email': email,
                'role': valid_users[email]['role'],
                'name': valid_users[email]['name']
            }
            return jsonify({
                'success': True,
                'token': token,
                'user': {
                    'email': email,
                    'role': valid_users[email]['role'],
                    'name': valid_users[email]['name']
                }
            }), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    """Invalidate the current session token."""
    user = get_current_user()
    if user is None:
        return jsonify({'success': True}), 200
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.split(' ', 1)[1].strip() if ' ' in auth_header else ''
    if token in SESSIONS:
        del SESSIONS[token]
    return jsonify({'success': True}), 200

# ==================== Students ====================

@app.route('/api/students', methods=['GET'])
def get_students():
    """Get all students with their department and program info"""
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        query = """
            SELECT 
                s.student_id,
                s.first_name,
                s.last_name,
                s.dob,
                s.gender,
                s.email,
                s.phone,
                s.address,
                s.admission_year,
                s.status,
                s.program_id,
                p.name as program_name,
                p.level as program_level,
                d.name as department_name,
                d.dept_id
            FROM student s
            LEFT JOIN program p ON s.program_id = p.program_id
            LEFT JOIN department d ON p.dept_id = d.dept_id
            ORDER BY s.student_id
        """
        cursor.execute(query)
        students = cursor.fetchall()
        
        for student in students:
            if student['dob']:
                student['dob'] = student['dob'].strftime('%Y-%m-%d')
        
        cursor.close()
        connection.close()
        return jsonify(students), 200
    except OperationalError as e:
        print(f"Error fetching students: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Add debugging logs to verify data and query execution
@app.route('/api/students', methods=['POST'])
@require_roles('admin')
def add_student():
    """Add a new student"""
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        data = request.json
        print("Received data:", data)  # Debugging log

        cursor = connection.cursor()

        required_fields = ['student_id', 'first_name', 'last_name', 'email']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400

        query = """
            INSERT INTO student 
            (student_id, first_name, last_name, dob, gender, email, phone, 
             address, admission_year, status, program_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            data.get('student_id'),
            data.get('first_name'),
            data.get('last_name'),
            data.get('dob') if data.get('dob') else None,
            data.get('gender', 'Male'),
            data.get('email'),
            data.get('phone'),
            data.get('address'),
            data.get('admission_year', datetime.now().year),
            data.get('status', 'Active'),
            int(data.get('program_id')) if data.get('program_id') else None
        )

        print("Executing query:", query)  # Debugging log
        print("With values:", values)  # Debugging log

        cursor.execute(query, values)
        connection.commit()  # Ensure the transaction is committed
        print("Transaction committed")  # Debugging log

        cursor.close()
        connection.close()

        return jsonify({
            'message': 'Student added successfully',
            'student_id': data.get('student_id')
        }), 201

    except IntegrityError as e:
        print(f"Integrity error: {e}")
        if 'Duplicate entry' in str(e):
            return jsonify({'error': 'Student ID or Email already exists'}), 400
        return jsonify({'error': 'Database integrity error'}), 400
    except Exception as e:
        print(f"Error adding student: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/students/<student_id>', methods=['DELETE'])
@require_roles('admin')
def delete_student(student_id):
    """Delete a student"""
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor()
        
        cursor.execute("SELECT student_id FROM student WHERE student_id = %s", (student_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Student not found'}), 404
        
        # Delete related records first
        cursor.execute("DELETE FROM enrollment WHERE student_id = %s", (student_id,))
        cursor.execute("DELETE FROM attendance WHERE student_id = %s", (student_id,))
        cursor.execute("DELETE FROM score WHERE student_id = %s", (student_id,))
        
        # Delete the student
        query = "DELETE FROM student WHERE student_id = %s"
        cursor.execute(query, (student_id,))
        connection.commit()
        
        cursor.close()
        connection.close()
        
        return jsonify({'message': 'Student deleted successfully'}), 200
        
    except Exception as e:
        print(f"Error deleting student: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ==================== Departments ====================

@app.route('/api/departments', methods=['GET'])
def get_departments():
    """Get all departments"""
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        query = "SELECT * FROM department ORDER BY name"
        cursor.execute(query)
        departments = cursor.fetchall()
        cursor.close()
        connection.close()
        return jsonify(departments), 200
    except OperationalError as e:
        print(f"Error fetching departments: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/departments', methods=['POST'])
@require_roles('admin')
def add_department():
    """Create a new department"""
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        data = request.json or {}
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'Department name is required'}), 400

        cursor = connection.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS department (dept_id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(100) UNIQUE NOT NULL)")
        cursor.execute("INSERT INTO department (name) VALUES (%s)", (name,))
        connection.commit()

        new_id = cursor.lastrowid
        cursor.close()
        connection.close()
        return jsonify({'dept_id': new_id, 'name': name}), 201
    except IntegrityError:
        return jsonify({'error': 'Department already exists'}), 400
    except Exception as e:
        print(f"Error adding department: {e}")
        return jsonify({'error': 'Failed to add department'}), 500

@app.route('/api/departments/<int:dept_id>', methods=['PUT'])
@require_roles('admin')
def update_department(dept_id: int):
    """Update department name"""
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        data = request.json or {}
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'Department name is required'}), 400

        cursor = connection.cursor()
        cursor.execute("UPDATE department SET name=%s WHERE dept_id=%s", (name, dept_id))
        connection.commit()
        affected = cursor.rowcount
        cursor.close()
        connection.close()
        if affected == 0:
            return jsonify({'error': 'Department not found'}), 404
        return jsonify({'dept_id': dept_id, 'name': name}), 200
    except IntegrityError:
        return jsonify({'error': 'Another department with this name already exists'}), 400
    except Exception as e:
        print(f"Error updating department: {e}")
        return jsonify({'error': 'Failed to update department'}), 500

@app.route('/api/departments/<int:dept_id>', methods=['DELETE'])
@require_roles('admin')
def delete_department(dept_id: int):
    """Delete a department"""
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM department WHERE dept_id=%s", (dept_id,))
        connection.commit()
        affected = cursor.rowcount
        cursor.close()
        connection.close()
        if affected == 0:
            return jsonify({'error': 'Department not found'}), 404
        return jsonify({'success': True}), 200
    except IntegrityError as e:
        # Likely foreign key constraint due to programs/courses referencing department
        return jsonify({'error': 'Cannot delete department referenced by other records'}), 400
    except Exception as e:
        print(f"Error deleting department: {e}")
        return jsonify({'error': 'Failed to delete department'}), 500

# ==================== Programs ====================

@app.route('/api/programs', methods=['GET'])
def get_programs():
    """Get all programs with department info"""
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        query = """
            SELECT p.*, d.name as department_name
            FROM program p
            LEFT JOIN department d ON p.dept_id = d.dept_id
            ORDER BY p.name
        """
        cursor.execute(query)
        programs = cursor.fetchall()
        cursor.close()
        connection.close()
        return jsonify(programs), 200
    except OperationalError as e:
        print(f"Error fetching programs: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== Faculty ====================

@app.route('/api/faculty', methods=['GET'])
def get_faculty():
    """Get all faculty members"""
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        query = """
            SELECT f.*, d.name as department_name
            FROM faculty f
            LEFT JOIN department d ON f.dept_id = d.dept_id
            ORDER BY f.faculty_id
        """
        cursor.execute(query)
        faculty = cursor.fetchall()
        cursor.close()
        connection.close()
        return jsonify(faculty), 200
    except OperationalError as e:
        print(f"Error fetching faculty: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/faculty', methods=['POST'])
@require_roles('admin')
def add_faculty():
    """Add a new faculty member"""
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        data = request.json or {}
        required = ['first_name', 'last_name', 'email', 'designation', 'dept_id']
        for field in required:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400

        cursor = connection.cursor()
        query = (
            "INSERT INTO faculty (first_name, last_name, designation, email, phone, dept_id) "
            "VALUES (%s, %s, %s, %s, %s, %s)"
        )
        values = (
            data.get('first_name').strip(),
            data.get('last_name').strip(),
            data.get('designation').strip(),
            data.get('email').strip(),
            (data.get('phone') or '').strip() or None,
            int(data.get('dept_id'))
        )
        cursor.execute(query, values)
        connection.commit()
        new_id = cursor.lastrowid
        cursor.close()
        connection.close()
        return jsonify({'faculty_id': new_id}), 201
    except IntegrityError as e:
        return jsonify({'error': 'Duplicate or invalid data'}), 400
    except Exception as e:
        print(f"Error adding faculty: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Failed to add faculty'}), 500

@app.route('/api/faculty/<int:faculty_id>', methods=['PUT'])
@require_roles('admin')
def update_faculty(faculty_id: int):
    """Update an existing faculty member"""
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        data = request.json or {}
        fields = []
        values = []
        for col in ['first_name', 'last_name', 'designation', 'email', 'phone', 'dept_id']:
            if col in data and data.get(col) is not None:
                fields.append(f"{col}=%s")
                if col == 'dept_id':
                    values.append(int(data.get(col)))
                else:
                    values.append(data.get(col))
        if not fields:
            return jsonify({'error': 'No fields to update'}), 400
        values.append(faculty_id)

        cursor = connection.cursor()
        cursor.execute(f"UPDATE faculty SET {', '.join(fields)} WHERE faculty_id=%s", tuple(values))
        connection.commit()
        affected = cursor.rowcount
        cursor.close()
        connection.close()
        if affected == 0:
            return jsonify({'error': 'Faculty not found'}), 404
        return jsonify({'success': True}), 200
    except IntegrityError:
        return jsonify({'error': 'Duplicate or invalid data'}), 400
    except Exception as e:
        print(f"Error updating faculty: {e}")
        return jsonify({'error': 'Failed to update faculty'}), 500

@app.route('/api/faculty/<int:faculty_id>', methods=['DELETE'])
@require_roles('admin')
def delete_faculty(faculty_id: int):
    """Delete a faculty member"""
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM faculty WHERE faculty_id=%s", (faculty_id,))
        connection.commit()
        affected = cursor.rowcount
        cursor.close()
        connection.close()
        if affected == 0:
            return jsonify({'error': 'Faculty not found'}), 404
        return jsonify({'success': True}), 200
    except IntegrityError:
        return jsonify({'error': 'Cannot delete faculty referenced by other records'}), 400
    except Exception as e:
        print(f"Error deleting faculty: {e}")
        return jsonify({'error': 'Failed to delete faculty'}), 500

# ==================== Courses ====================

@app.route('/api/courses', methods=['GET'])
def get_courses():
    """Get all courses"""
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        query = """
            SELECT c.*, d.name as department_name
            FROM course c
            LEFT JOIN department d ON c.dept_id = d.dept_id
            ORDER BY c.course_id
        """
        cursor.execute(query)
        courses = cursor.fetchall()
        cursor.close()
        connection.close()
        return jsonify(courses), 200
    except OperationalError as e:
        print(f"Error fetching courses: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== Scores ====================

@app.route('/api/scores', methods=['GET'])
def get_scores():
    """Get all scores with student and course info if available"""
    print("=== DEBUG: get_scores() called ===")
    connection = get_db_connection()
    if not connection:
        print("ERROR: Database connection failed")
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        # Simple query to get all scores
        query = "SELECT * FROM score ORDER BY score_id"
        print(f"DEBUG: Executing query: {query}")
        cursor.execute(query)
        scores = cursor.fetchall()
        print(f"DEBUG: Found {len(scores)} scores in database")
        print(f"DEBUG: Scores data: {scores}")
        
        # Format the data for frontend
        formatted_scores = []
        for row in scores:
            formatted_row = {
                'score_id': row['score_id'],
                'student_id': row['student_id'],
                'student_name': row['student_id'],  # Use student_id as name for now
                'assessment_id': row['assessment_id'],
                'course_title': f"Assessment {row['assessment_id']}",  # Use assessment_id as title for now
                'score': row['marks_obtained'],  # Use marks_obtained as score
                'marks_obtained': row['marks_obtained']
            }
            formatted_scores.append(formatted_row)
        
        print(f"DEBUG: Formatted scores: {formatted_scores}")
        cursor.close()
        connection.close()
        return jsonify(formatted_scores), 200
        
    except Exception as e:
        print(f"ERROR: Error fetching scores: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Failed to fetch scores: {str(e)}'}), 500

@app.route('/api/scores', methods=['POST'])
@require_roles('admin', 'faculty')
def add_score():
    """Add a new score"""
    print("=== DEBUG: add_score() called ===")
    print(f"DEBUG: Request data: {request.json}")
    
    connection = get_db_connection()
    if not connection:
        print("ERROR: Database connection failed")
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        data = request.json or {}
        print(f"DEBUG: Parsed data: {data}")
        
        required = ['student_id', 'assessment_id', 'marks_obtained']
        for field in required:
            if not data.get(field):
                print(f"ERROR: Missing required field: {field}")
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        cursor = connection.cursor()
        query = """
            INSERT INTO score (student_id, assessment_id, marks_obtained)
            VALUES (%s, %s, %s)
        """
        values = (
            str(data.get('student_id')).strip(),
            int(data.get('assessment_id')),
            float(data.get('marks_obtained'))
        )
        
        print(f"DEBUG: Executing query: {query}")
        print(f"DEBUG: With values: {values}")
        
        cursor.execute(query, values)
        connection.commit()
        new_id = cursor.lastrowid
        print(f"DEBUG: Successfully added score with ID: {new_id}")
        
        cursor.close()
        connection.close()
        return jsonify({'score_id': new_id, 'message': 'Score added successfully'}), 201
        
    except IntegrityError as e:
        print(f"ERROR: Integrity error: {e}")
        return jsonify({'error': 'Invalid student or course reference'}), 400
    except Exception as e:
        print(f"ERROR: Error adding score: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Failed to add score: {str(e)}'}), 500

@app.route('/api/scores/<int:score_id>', methods=['PUT'])
@require_roles('admin', 'faculty')
def update_score(score_id: int):
    """Update an existing score"""
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        data = request.json or {}
        fields = []
        values = []
        for col in ['student_id', 'assessment_id', 'marks_obtained']:
            if col in data and data.get(col) is not None:
                fields.append(f"{col}=%s")
                if col == 'assessment_id':
                    values.append(int(data.get(col)))
                elif col == 'marks_obtained':
                    values.append(float(data.get(col)))
                else:
                    values.append(data.get(col))
        if not fields:
            return jsonify({'error': 'No fields to update'}), 400
        values.append(score_id)
        cursor = connection.cursor()
        cursor.execute(f"UPDATE score SET {', '.join(fields)} WHERE score_id=%s", tuple(values))
        connection.commit()
        affected = cursor.rowcount
        cursor.close()
        connection.close()
        if affected == 0:
            return jsonify({'error': 'Score not found'}), 404
        return jsonify({'success': True}), 200
    except Exception as e:
        print(f"Error updating score: {e}")
        return jsonify({'error': 'Failed to update score'}), 500

@app.route('/api/scores/<int:score_id>', methods=['DELETE'])
@require_roles('admin')
def delete_score(score_id: int):
    """Delete a score"""
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM score WHERE score_id=%s", (score_id,))
        connection.commit()
        affected = cursor.rowcount
        cursor.close()
        connection.close()
        if affected == 0:
            return jsonify({'error': 'Score not found'}), 404
        return jsonify({'success': True}), 200
    except Exception as e:
        print(f"Error deleting score: {e}")
        return jsonify({'error': 'Failed to delete score'}), 500

# ==================== Dashboard Statistics ====================

@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Get dashboard statistics"""
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(pymysql.cursors.DictCursor)

        total_students = 0
        total_faculty = 0
        total_courses = 0
        total_assessments = 0

        try:
            cursor.execute("SELECT COUNT(*) as count FROM student WHERE status = 'Active'")
            row = cursor.fetchone()
            total_students = row['count'] if row and 'count' in row else 0
        except Exception as e:
            print(f"Dashboard stat 'students' failed: {e}")

        try:
            cursor.execute("SELECT COUNT(*) as count FROM faculty")
            row = cursor.fetchone()
            total_faculty = row['count'] if row and 'count' in row else 0
        except Exception as e:
            print(f"Dashboard stat 'faculty' failed: {e}")

        try:
            cursor.execute("SELECT COUNT(*) as count FROM course")
            row = cursor.fetchone()
            total_courses = row['count'] if row and 'count' in row else 0
        except Exception as e:
            print(f"Dashboard stat 'courses' failed: {e}")

        try:
            cursor.execute("SELECT COUNT(*) as count FROM assessment")
            row = cursor.fetchone()
            total_assessments = row['count'] if row and 'count' in row else 0
        except Exception as e:
            print(f"Dashboard stat 'assessments' failed: {e}")

        cursor.close()
        connection.close()

        return jsonify({
            'total_students': total_students,
            'total_faculty': total_faculty,
            'total_courses': total_courses,
            'total_assessments': total_assessments
        }), 200

    except Exception as e:
        print(f"Error fetching dashboard stats: {e}")
        try:
            cursor.close()
            connection.close()
        except Exception:
            pass
        # Return zeros on unexpected errors to avoid breaking the UI
        return jsonify({
            'total_students': 0,
            'total_faculty': 0,
            'total_courses': 0,
            'total_assessments': 0
        }), 200

# ==================== Health Check ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    connection = get_db_connection()
    if connection:
        connection.close()
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'message': 'Backend is running successfully'
        }), 200
    else:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'message': 'Database connection failed'
        }), 500

@app.route('/api/debug/scores', methods=['GET'])
def debug_scores():
    """Debug endpoint to check score table structure and data"""
    print("=== DEBUG: debug_scores() called ===")
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        
        # Check if score table exists and show its structure
        cursor.execute("DESCRIBE score")
        table_structure = cursor.fetchall()
        print(f"DEBUG: Score table structure: {table_structure}")
        
        # Count total records
        cursor.execute("SELECT COUNT(*) as count FROM score")
        count_result = cursor.fetchone()
        total_count = count_result['count'] if count_result else 0
        print(f"DEBUG: Total records in score table: {total_count}")
        
        # Get all records
        cursor.execute("SELECT * FROM score LIMIT 10")
        all_scores = cursor.fetchall()
        print(f"DEBUG: Sample scores: {all_scores}")
        
        cursor.close()
        connection.close()
        
        # Convert table structure to a more readable format
        readable_structure = []
        for field in table_structure:
            readable_structure.append({
                'Field': field['Field'],
                'Type': field['Type'],
                'Null': field['Null'],
                'Key': field['Key'],
                'Default': field['Default'],
                'Extra': field['Extra']
            })
        
        return jsonify({
            'table_structure': readable_structure,
            'total_count': total_count,
            'sample_data': all_scores,
            'message': 'Debug info retrieved successfully'
        }), 200
        
    except Exception as e:
        print(f"ERROR in debug_scores: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/sample/scores', methods=['POST'])
def add_sample_scores():
    """Add sample score data for testing"""
    print("=== DEBUG: add_sample_scores() called ===")
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = connection.cursor()
        
        # Disable foreign key checks temporarily
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        # Sample score data using correct column names
        sample_scores = [
            ('STU001', 1, 85.5),
            ('STU002', 2, 92.0),
            ('STU003', 1, 78.5),
            ('STU001', 3, 88.0),
            ('STU004', 2, 95.5),
        ]
        
        print(f"DEBUG: About to add {len(sample_scores)} sample scores")
        
        query = """
            INSERT INTO score (student_id, assessment_id, marks_obtained)
            VALUES (%s, %s, %s)
        """
        
        added_count = 0
        for i, score_data in enumerate(sample_scores):
            try:
                print(f"DEBUG: Attempting to add score {i+1}: {score_data}")
                cursor.execute(query, score_data)
                added_count += 1
                print(f"DEBUG: Successfully added sample score: {score_data}")
            except Exception as e:
                print(f"ERROR: Could not add sample score {score_data}: {e}")
                traceback.print_exc()
        
        # Re-enable foreign key checks
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        connection.commit()
        cursor.close()
        connection.close()
        
        return jsonify({
            'message': f'Successfully added {added_count} sample scores',
            'added_count': added_count
        }), 201
        
    except Exception as e:
        print(f"ERROR in add_sample_scores: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ==================== Error Handlers ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ==================== Route to serve the HTML file ====================

@app.route('/')
def home():
    # Provide safe defaults so Jinja loops don't break when visiting '/'
    return render_template('index.html', students=[], faculty=[], departments=[])

# Route to display data from MySQL tables
@app.route('/tables')
def show_tables():
    connection = get_db_connection()
    if not connection:
        print("Database connection failed")  # Debugging log
        return "<h1>Database connection failed</h1>", 500

    try:
        cursor = connection.cursor(pymysql.cursors.DictCursor)

        # Fetch students
        cursor.execute("SELECT * FROM student")
        students = cursor.fetchall()
        print("Fetched students:", students)  # Debugging log

        # Fetch faculty
        cursor.execute("SELECT * FROM faculty")
        faculty = cursor.fetchall()
        print("Fetched faculty:", faculty)  # Debugging log

        # Fetch departments
        cursor.execute("SELECT * FROM department")
        departments = cursor.fetchall()
        print("Fetched departments:", departments)  # Debugging log

        cursor.close()
        connection.close()

        # Pass data to the template
        return render_template('index.html', students=students, faculty=faculty, departments=departments)

    except Exception as e:
        print(f"Error fetching data: {e}")
        return "<h1>Error fetching data</h1>", 500

# ==================== Main ====================

if __name__ == '__main__':
    print("=" * 50)
    print("College Management System - Backend Server")
    print("=" * 50)
    print(f"Starting Flask server on http://localhost:5000")
    print(f"Database: {DB_CONFIG['database']} @ {DB_CONFIG['host']}")
    print("=" * 50)
    # Ensure default departments exist
    seed_departments_if_missing()
    ensure_score_table_if_missing()
    app.run(debug=True, port=5000, host='0.0.0.0')