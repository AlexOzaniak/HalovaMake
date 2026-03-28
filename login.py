import bcrypt

class User:
    def __init__(self, username, hashed_password):
        self.username = username
        self.password_hash = hashed_password  # Storing the hash, not the password

class LoginSystem:
    def __init__(self):
        self.database = {}

    def register(self):
        print("\n--- Secure Registration ---")
        username = input("Enter username: ").strip()
        
        if username in self.database:
            print("Username already exists.")
            return

        password = input("Enter password: ").strip().encode('utf-8')
        
        # Generate a salt and hash the password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password, salt)
        
        # Create User with the HASH11
        new_user = User(username, hashed)
        self.database[username] = new_user
        print(f"User '{username}' registered securely!")

    def login(self):
        print("\n--- Secure Login ---")
        username = input("Username: ").strip()
        password_input = input("Password: ").strip().encode('utf-8')

        user = self.database.get(username)

        # Check if user exists and if the provided password matches the hash
        if user and bcrypt.checkpw(password_input, user.password_hash):
            print(f"Access Granted. Welcome, {username}!")
            return True
        else:
            print("Invalid credentials.")
            return False

# --- Main Program ---
def main():
    system = LoginSystem()
    while True:
        choice = input("\n1. Reg | 2. Login | 3. Exit: ")
        if choice == "1": system.register()
        elif choice == "2": system.login()
        elif choice == "3": break

if __name__ == "__main__":
    main()


    