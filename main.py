import sqlite3

class Book:
    def __init__(self, title, author, isbn):
        self._title = title
        self._author = author
        self._isbn = isbn
        self._is_borrowed = False

    @property
    def title(self):
        return self._title

    @property
    def author(self):
        return self._author

    @property
    def isbn(self):
        return self._isbn

    @property
    def is_borrowed(self):
        return self._is_borrowed

    @is_borrowed.setter
    def is_borrowed(self, status):
        if isinstance(status, bool):
            self._is_borrowed = status

    def borrow(self):
        if not self._is_borrowed:
            self._is_borrowed = True
            return True
        return False

    def return_book(self):
        if self._is_borrowed:
            self._is_borrowed = False
            return True
        return False

    def __str__(self):
        status = "Borrowed" if self._is_borrowed else "Available"
        return f"Title: {self.title}, Author: {self.author}, ISBN: {self.isbn}, Status: {status}"


class User:
    def __init__(self, name, user_id):
        self._name = name
        self._user_id = user_id
        self._borrowed_books_isbns = []

    @property
    def name(self):
        return self._name

    @property
    def user_id(self):
        return self._user_id

    @property
    def borrowed_books_isbns(self):
        return self._borrowed_books_isbns.copy()

    def add_borrowed_book_isbn(self, isbn):
        if isbn not in self._borrowed_books_isbns:
            self._borrowed_books_isbns.append(isbn)

    def remove_borrowed_book_isbn(self, isbn):
        if isbn in self._borrowed_books_isbns:
            self._borrowed_books_isbns.remove(isbn)

    def __str__(self):
        return f"User: {self.name} (ID: {self.user_id}), Borrowed Books: {len(self._borrowed_books_isbns)}"


class Library:
    def __init__(self, db_file='library.db'):
        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS books (
            isbn TEXT PRIMARY KEY,
            title TEXT,
            author TEXT,
            is_borrowed INTEGER
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS borrowed_books (
            user_id TEXT,
            isbn TEXT,
            PRIMARY KEY (user_id, isbn),
            FOREIGN KEY(user_id) REFERENCES users(user_id),
            FOREIGN KEY(isbn) REFERENCES books(isbn)
        )''')
        self.conn.commit()

    def add_book(self, book):
        try:
            self.conn.execute("INSERT INTO books (isbn, title, author, is_borrowed) VALUES (?, ?, ?, ?)",
                              (book.isbn, book.title, book.author, 0))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def remove_book(self, isbn):
        cursor = self.conn.cursor()
        cursor.execute("SELECT is_borrowed FROM books WHERE isbn = ?", (isbn,))
        row = cursor.fetchone()
        if not row or row["is_borrowed"]:
            return False
        self.conn.execute("DELETE FROM books WHERE isbn = ?", (isbn,))
        self.conn.commit()
        return True

    def register_user(self, user):
        try:
            self.conn.execute("INSERT INTO users (user_id, name) VALUES (?, ?)", (user.user_id, user.name))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def remove_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM borrowed_books WHERE user_id = ?", (user_id,))
        if cursor.fetchone()[0] > 0:
            return False
        self.conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        self.conn.commit()
        return True

    def borrow_book(self, isbn, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT is_borrowed FROM books WHERE isbn = ?", (isbn,))
        book = cursor.fetchone()
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

        if not book or not user or book["is_borrowed"]:
            return False

        self.conn.execute("UPDATE books SET is_borrowed = 1 WHERE isbn = ?", (isbn,))
        self.conn.execute("INSERT INTO borrowed_books (user_id, isbn) VALUES (?, ?)", (user_id, isbn))
        self.conn.commit()
        return True

    def return_book(self, isbn, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM borrowed_books WHERE user_id = ? AND isbn = ?", (user_id, isbn))
        if not cursor.fetchone():
            return False

        self.conn.execute("DELETE FROM borrowed_books WHERE user_id = ? AND isbn = ?", (user_id, isbn))
        self.conn.execute("UPDATE books SET is_borrowed = 0 WHERE isbn = ?", (isbn,))
        self.conn.commit()
        return True

    def search_book(self, query):
        query = f"%{query.lower()}%"
        cursor = self.conn.cursor()
        cursor.execute('''SELECT * FROM books
                          WHERE LOWER(title) LIKE ? OR LOWER(author) LIKE ? OR isbn LIKE ?''',
                       (query, query, query))
        rows = cursor.fetchall()
        return [Book(row["title"], row["author"], row["isbn"]) for row in rows]

    def display_all_books(self, show_available_only=False):
        cursor = self.conn.cursor()
        if show_available_only:
            cursor.execute("SELECT * FROM books WHERE is_borrowed = 0")
        else:
            cursor.execute("SELECT * FROM books")
        for row in cursor.fetchall():
            book = Book(row["title"], row["author"], row["isbn"])
            book.is_borrowed = bool(row["is_borrowed"])
            print(book)

    def display_all_users(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users")
        for row in cursor.fetchall():
            cursor.execute("SELECT isbn FROM borrowed_books WHERE user_id = ?", (row["user_id"],))
            borrowed = [r["isbn"] for r in cursor.fetchall()]
            user = User(row["name"], row["user_id"])
            for isbn in borrowed:
                user.add_borrowed_book_isbn(isbn)
            print(user)

    def display_user_borrowed_books(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''SELECT b.* FROM books b
                          JOIN borrowed_books bb ON b.isbn = bb.isbn
                          WHERE bb.user_id = ?''', (user_id,))
        rows = cursor.fetchall()
        if not rows:
            print("No borrowed books or user not found.")
        for row in rows:
            book = Book(row["title"], row["author"], row["isbn"])
            book.is_borrowed = True
            print(book)


def main():
    lib = Library()

    while True:
        print("\n--- Library Management ---")
        print("1. Add Book")
        print("2. Remove Book")
        print("3. Register User")
        print("4. Remove User")
        print("5. Borrow Book")
        print("6. Return Book")
        print("7. Search Book")
        print("8. Display All Books")
        print("9. Display All Users")
        print("10. Display User's Borrowed Books")
        print("0. Exit")

        choice = input("Enter your choice: ")

        if choice == "1":
            title = input("Book title: ")
            author = input("Author: ")
            isbn = input("ISBN: ")
            book = Book(title, author, isbn)
            print("Book added!" if lib.add_book(book) else "Book already exists.")

        elif choice == "2":
            isbn = input("ISBN to remove: ")
            print("Book removed!" if lib.remove_book(isbn) else "Could not remove book.")

        elif choice == "3":
            name = input("User name: ")
            uid = input("User ID: ")
            user = User(name, uid)
            print("User registered!" if lib.register_user(user) else "User already exists.")

        elif choice == "4":
            uid = input("User ID to remove: ")
            print("User removed!" if lib.remove_user(uid) else "Could not remove user.")

        elif choice == "5":
            uid = input("User ID: ")
            isbn = input("Book ISBN: ")
            print("Book borrowed!" if lib.borrow_book(isbn, uid) else "Borrow failed.")

        elif choice == "6":
            uid = input("User ID: ")
            isbn = input("Book ISBN: ")
            print("Book returned!" if lib.return_book(isbn, uid) else "Return failed.")

        elif choice == "7":
            query = input("Search: ")
            matches = lib.search_book(query)
            if matches:
                for book in matches:
                    print(book)
            else:
                print("No matches found.")

        elif choice == "8":
            lib.display_all_books()

        elif choice == "9":
            lib.display_all_users()

        elif choice == "10":
            uid = input("User ID: ")
            lib.display_user_borrowed_books(uid)

        elif choice == "0":
            print("Goodbye!")
            break

        else:
            print("Invalid choice. Try again.")

if __name__ == "__main__":
    main()