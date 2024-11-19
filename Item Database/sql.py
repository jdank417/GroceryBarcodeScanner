import sqlite3

# Step 1: Connect to the database
connection = sqlite3.connect('example.db')

# Step 2: Create a cursor object
cursor = connection.cursor()

# Step 3: Create a table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        age INTEGER,
        email TEXT
    )
''')

# Step 4: Insert data
cursor.execute('''
    INSERT INTO users (name, age, email)
    VALUES ('Alice', 30, 'alice@example.com')
''')
cursor.execute('''
    INSERT INTO users (name, age, email)
    VALUES (?, ?, ?)
''', ('Bob', 25, 'bob@example.com'))

# Step 5: Query data
cursor.execute('SELECT * FROM users')
rows = cursor.fetchall()
for row in rows:
    print(row)

# Step 6: Commit and close
connection.commit()
connection.close()
