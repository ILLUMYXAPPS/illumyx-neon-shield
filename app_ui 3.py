import tkinter as tk

def run_app():
    root = tk.Tk()
    root.title("YourApp UI v1")
    tk.Label(root, text="⚡ YourApp - Neon Bolt Edition", font=("Arial", 16)).pack(pady=20)
    tk.Label(root, text="This is the GUI version of YourApp.").pack(pady=10)
    tk.Button(root, text="Close", command=root.destroy).pack(pady=10)
    root.mainloop()

if __name__ == "__main__":
    run_app()
