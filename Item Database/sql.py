import sqlite3

class DatabaseManager:
    def __init__(self, db_name):
        self.db_name = db_name

    def connect(self):
        """Connect to the SQLite database."""
        self.connection = sqlite3.connect(self.db_name)
        self.cursor = self.connection.cursor()

    def create_table(self):
        """Create the users table."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER,
                email TEXT
            )
        ''')
        self.connection.commit()

    def insert_user(self, name, age, email):
        """Insert a new user into the users table."""
        self.cursor.execute('''
            INSERT INTO users (name, age, email)
            VALUES (?, ?, ?)
        ''', (name, age, email))
        self.connection.commit()

    def fetch_all_users(self):
        """Fetch all rows from the users table."""
        self.cursor.execute('SELECT * FROM users')
        return self.cursor.fetchall()

    def fetch_user_by_id(self, user_id):
        """Fetch a single user by their ID."""
        self.cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        return self.cursor.fetchone()

    def update_user(self, user_id, name=None, age=None, email=None):
        """Update a user's details."""
        fields = []
        values = []
        if name:
            fields.append("name = ?")
            values.append(name)
        if age:
            fields.append("age = ?")
            values.append(age)
        if email:
            fields.append("email = ?")
            values.append(email)
        values.append(user_id)
        query = f"UPDATE users SET {', '.join(fields)} WHERE id = ?"
        self.cursor.execute(query, values)
        self.connection.commit()

    def delete_user(self, user_id):
        """Delete a user by their ID."""
        self.cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        self.connection.commit()

    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()

# Main method
def main():
    # Initialize DatabaseManager
    db = DatabaseManager('example.db')

    # Connect to the database
    db.connect()

    # Create the table
    db.create_table()

    # Insert users
    db.insert_user('Alice', 30, 'alice@example.com')
    db.insert_user('Bob', 25, 'bob@example.com')

    # Fetch and display all users
    print("All users:")
    users = db.fetch_all_users()
    for user in users:
        print(user)

    # Fetch a single user by ID
    print("\nUser with ID 1:")
    user = db.fetch_user_by_id(1)
    print(user)

    # Update a user
    print("\nUpdating user with ID 1...")
    db.update_user(1, name='Alice Cooper', age=31)
    updated_user = db.fetch_user_by_id(1)
    print("Updated user:", updated_user)

    # Delete a user
    print("\nDeleting user with ID 2...")
    db.delete_user(2)
    print("All users after deletion:")
    users = db.fetch_all_users()
    for user in users:
        print(user)

    # Close the connection
    db.close()

if __name__ == '__main__':
    main()
