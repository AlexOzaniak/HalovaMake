import bcrypt
1

class User:
    def __init__(self, username, hashed_password):
        self.username = username
        self.password_hash = hashed_password

class LoginSystem:
    def __init__(self):
        # Toto v budúcnosti nahradíš skutočnou databázou
        self.database = {}

    def register_user(self, username, password):
        """Logika pre registráciu - vracia (úspech, správa)"""
        username = username.strip()
        if not username or not password:
            return False, "Meno a heslo nesmú byť prázdne."

        if username in self.database:
            return False, "Používateľ už existuje."

        # Príprava hashu
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        # Uloženie
        new_user = User(username, hashed)
        self.database[username] = new_user
        return True, f"User '{username}' úspešne zaregistrovaný."

    def login_user(self, username, password):
        """Logika pre prihlásenie - vracia (úspech, správa)"""
        username = username.strip()
        user = self.database.get(username)

        if not user:
            return False, "Neplatné údaje."

        if bcrypt.checkpw(password.encode('utf-8'), user.password_hash):
            return True, f"Vitaj, {username}!"

        
        return False, "Neplatné údaje."

# --- Main Program (Terminálové rozhranie) ---
# Toto v budúcnosti jednoducho zahodíš a nahradíš FastAPI endpointmi
def main():
    system = LoginSystem()
    
    while True:
        print("\n1. Reg | 2. Login | 3. Exit")
        choice = input("Vyber si: ").strip()

        if choice == "1":
            u = input("Meno: ")
            p = input("Heslo: ")
            success, message = system.register_user(u, p)
            print(message)

        elif choice == "2":
            u = input("Meno: ")
            p = input("Heslo: ")
            success, message = system.login_user(u, p)
            print(message)

        elif choice == "3":
            print("Končím...")
            break
        
        else:
            # Ošetrenie neplatnej voľby (necrashne to)
            print(f"Chyba: '{choice}' nie je platná voľba. Skús znova (1, 2 alebo 3).")

if __name__ == "__main__":
    main()
