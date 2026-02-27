-- Insert departments
INSERT INTO departments (id, name, code, budget) VALUES
    ('d0000001-0000-0000-0000-000000000001', 'Computer Science',    'CS',   2400000),
    ('d0000002-0000-0000-0000-000000000002', 'Mathematics',         'MATH', 1800000),
    ('d0000003-0000-0000-0000-000000000003', 'Physics',             'PHY',  2100000),
    ('d0000004-0000-0000-0000-000000000004', 'Electrical Engineering', 'EE', 2600000),
    ('d0000005-0000-0000-0000-000000000005', 'Mechanical Engineering', 'ME', 2200000)
ON CONFLICT DO NOTHING;

-- Insert faculty
INSERT INTO faculty (id, first_name, last_name, email, department_id, rank) VALUES
    ('f0000001-0000-0000-0000-000000000001', 'Rajesh',   'Kumar',    'rajesh.k@uni.edu',    'd0000001-0000-0000-0000-000000000001', 'professor'),
    ('f0000002-0000-0000-0000-000000000002', 'Priya',    'Sharma',   'priya.s@uni.edu',     'd0000001-0000-0000-0000-000000000001', 'assistant_professor'),
    ('f0000003-0000-0000-0000-000000000003', 'David',    'Johnson',  'david.j@uni.edu',     'd0000002-0000-0000-0000-000000000002', 'associate_professor'),
    ('f0000004-0000-0000-0000-000000000004', 'Sarah',    'Williams', 'sarah.w@uni.edu',     'd0000003-0000-0000-0000-000000000003', 'professor'),
    ('f0000005-0000-0000-0000-000000000005', 'Michael',  'Brown',    'michael.b@uni.edu',   'd0000004-0000-0000-0000-000000000004', 'professor'),
    ('f0000006-0000-0000-0000-000000000006', 'Ananya',   'Patel',    'ananya.p@uni.edu',    'd0000002-0000-0000-0000-000000000002', 'lecturer'),
    ('f0000007-0000-0000-0000-000000000007', 'James',    'Wilson',   'james.w@uni.edu',     'd0000005-0000-0000-0000-000000000005', 'associate_professor'),
    ('f0000008-0000-0000-0000-000000000008', 'Fatima',   'Hassan',   'fatima.h@uni.edu',    'd0000003-0000-0000-0000-000000000003', 'assistant_professor')
ON CONFLICT DO NOTHING;

-- Insert courses
INSERT INTO courses (id, code, title, department_id, credits, capacity, instructor_id) VALUES
    ('c0000001-0000-0000-0000-000000000001', 'CS101',   'Introduction to Computer Science',  'd0000001-0000-0000-0000-000000000001', 3, 120, 'f0000001-0000-0000-0000-000000000001'),
    ('c0000002-0000-0000-0000-000000000002', 'CS201',   'Data Structures & Algorithms',      'd0000001-0000-0000-0000-000000000001', 4,  80, 'f0000002-0000-0000-0000-000000000002'),
    ('c0000003-0000-0000-0000-000000000003', 'CS301',   'Operating Systems',                 'd0000001-0000-0000-0000-000000000001', 3,  60, 'f0000001-0000-0000-0000-000000000001'),
    ('c0000004-0000-0000-0000-000000000004', 'MATH201', 'Linear Algebra',                    'd0000002-0000-0000-0000-000000000002', 3,  90, 'f0000003-0000-0000-0000-000000000003'),
    ('c0000005-0000-0000-0000-000000000005', 'MATH301', 'Probability & Statistics',           'd0000002-0000-0000-0000-000000000002', 3,  75, 'f0000006-0000-0000-0000-000000000006'),
    ('c0000006-0000-0000-0000-000000000006', 'PHY101',  'Classical Mechanics',               'd0000003-0000-0000-0000-000000000003', 4, 100, 'f0000004-0000-0000-0000-000000000004'),
    ('c0000007-0000-0000-0000-000000000007', 'PHY201',  'Electromagnetism',                  'd0000003-0000-0000-0000-000000000003', 4,  70, 'f0000008-0000-0000-0000-000000000008'),
    ('c0000008-0000-0000-0000-000000000008', 'EE201',   'Circuit Analysis',                  'd0000004-0000-0000-0000-000000000004', 3,  65, 'f0000005-0000-0000-0000-000000000005'),
    ('c0000009-0000-0000-0000-000000000009', 'ME101',   'Engineering Mechanics',             'd0000005-0000-0000-0000-000000000005', 3,  80, 'f0000007-0000-0000-0000-000000000007')
ON CONFLICT DO NOTHING;

SELECT COUNT(*) as "Departments loaded" FROM departments;
