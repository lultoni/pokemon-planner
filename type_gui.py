import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os

from type_effectiveness import load_type_chart, get_type_matchups

TYPE_LIST = [
    "Normal", "Feuer", "Wasser", "Elektro", "Pflanze", "Eis",
    "Kampf", "Gift", "Boden", "Flug", "Psycho", "Käfer",
    "Gestein", "Geist", "Drache", "Unlicht", "Stahl", "Fee"
]

EFFECT_GROUPS = [0.0, 0.25, 0.5, 1.0, 2.0, 4.0]
EFFECT_LABELS = ["0×", "¼×", "½×", "1×", "2×", "4×"]

ICON_FOLDER = "type_icons"
ICON_SIZE = (40, 40)

class TypeEffectivenessApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pokémon Typen-Effektivität")

        self.type_chart = load_type_chart()
        self.selected_types = [None, None]

        self.type_images = {}
        self.tk_images = {}
        self.load_type_icons()

        self.type_buttons = [{}, {}]
        self.result_labels = {}

        self.setup_type_selectors()
        self.setup_result_table()

    def load_type_icons(self):
        for typ in TYPE_LIST:
            path = os.path.join(ICON_FOLDER, f"Typ-Icon_{typ}_KAPU.png")
            try:
                img = Image.open(path).resize(ICON_SIZE, Image.ANTIALIAS)
                self.tk_images[typ] = ImageTk.PhotoImage(img)
            except Exception as e:
                print(f"Fehler beim Laden von {path}: {e}")
                self.tk_images[typ] = None

    def setup_type_selectors(self):
        frame = ttk.LabelFrame(self.root, text="Typen auswählen")
        frame.grid(row=0, column=0, padx=10, pady=10)

        for idx in range(2):
            label = ttk.Label(frame, text=f"Typ {idx + 1}:", font=('Arial', 10, 'bold'))
            label.grid(row=0, column=idx, padx=10)

            for i, typ in enumerate(TYPE_LIST):
                row = i % 6 + 1
                col = i // 6 + idx * 3

                image = self.tk_images.get(typ)
                if not image:
                    continue

                btn = tk.Button(frame, image=image, relief="raised", bd=2, cursor="hand2")
                btn.grid(row=row, column=col, padx=2, pady=2)
                btn.config(command=lambda b=btn, index=idx, t=typ: self.select_type(b, index, t))
                self.type_buttons[idx][typ] = btn

    def select_type(self, button, type_index, typ):
        current = self.selected_types[type_index]
        if current == typ and type_index == 1:
            self.selected_types[type_index] = None
            button.config(relief="raised", bg="SystemButtonFace")
        else:
            self.selected_types[type_index] = typ
            for btn in self.type_buttons[type_index].values():
                btn.config(relief="raised", bg="SystemButtonFace")
            button.config(relief="sunken", bg="#a3d5ff")

        self.update_table()

    def setup_result_table(self):
        self.table_frame = ttk.LabelFrame(self.root, text="Effektivitäten")
        self.table_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        for col, label in enumerate(EFFECT_LABELS):
            header = ttk.Label(self.table_frame, text=label, font=("Arial", 10, "bold"))
            header.grid(row=0, column=col, padx=10, pady=5)
            self.result_labels[label] = []

    def update_table(self):
        for label_list in self.result_labels.values():
            for widget in label_list:
                widget.destroy()
            label_list.clear()

        if self.selected_types[0] is None:
            return

        defense = [self.selected_types[0]]
        if self.selected_types[1]:
            defense.append(self.selected_types[1])

        matchups = get_type_matchups(self.type_chart, defense)

        groups = {key: [] for key in EFFECT_GROUPS}
        for typ, value in matchups.items():
            groups.setdefault(value, []).append(typ)

        for col_index, multiplier in enumerate(EFFECT_GROUPS):
            typelist = groups.get(multiplier, [])
            for row_index, typ in enumerate(typelist):
                icon = self.tk_images.get(typ)
                if not icon:
                    continue
                lbl = tk.Label(self.table_frame, image=icon)
                lbl.image = icon  # Referenz behalten
                lbl.grid(row=row_index + 1, column=col_index, padx=6, pady=3)
                self.result_labels[EFFECT_LABELS[col_index]].append(lbl)

def main():
    root = tk.Tk()
    app = TypeEffectivenessApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
