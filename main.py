import customtkinter as ctk
from entity_screen import EntityScreen

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Payment Management System")
        self.geometry("1280x780")
        self.minsize(960, 600)
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._show_entity_screen()

    def _on_close(self):
        self.quit()
        self.destroy()

    def _show_entity_screen(self):
        for w in self.winfo_children():
            w.destroy()
        screen = EntityScreen(self, on_select_entity=self._open_entity)
        screen.pack(fill="both", expand=True)
        self.update()

    def _open_entity(self, entity_name, db_path):
        from main_window import MainWindow
        for w in self.winfo_children():
            w.destroy()
        MainWindow(self, entity_name=entity_name, db_path=db_path,
                   on_back=self._show_entity_screen)
        self.update()


if __name__ == "__main__":
    app = App()
    app.mainloop()
