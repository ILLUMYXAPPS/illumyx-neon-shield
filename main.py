import tkinter as tk
from tkinter import messagebox

def launch_app():
    window = tk.Tk()
    window.title("ILLUMYX App - v1.0")
    window.geometry("400x250")

    label = tk.Label(window, text="✨ Welcome to the ILLUMYX App ✨", font=("Arial", 14), fg="purple")
    label.pack(pady=20)

    def show_message():
        messagebox.showinfo("ILLUMYX", "🔥 Thank you for supporting Aaron Paszek & ILLUMYX 🔥")

    btn = tk.Button(window, text="Click Me", command=show_message, bg="black", fg="white")
    btn.pack(pady=10)

    footer = tk.Label(window, text="© 2025 Aaron Paszek | ILLUMYX", font=("Arial", 8))
    footer.pack(side="bottom", pady=5)

    window.mainloop()

if __name__ == "__main__":
    launch_app()
