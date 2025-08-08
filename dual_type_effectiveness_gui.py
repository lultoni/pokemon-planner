import tkinter as tk
from tkinter import ttk
import os

import global_infos
from type_effectiveness import load_type_chart, get_type_matchups

EFFECT_GROUPS = [0.0, 0.25, 0.5, 1.0, 2.0, 4.0]
EFFECT_LABELS = ["0×", "¼×", "½×", "1×", "2×", "4×"]

ICON_FOLDER = "type_icons"
ICON_FILENAME_PATTERN = "Typ-Icon_{typ}_KAPU.png"

class TypeEffectivenessApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pokémon Typen-Effektivität")

        self.type_chart = load_type_chart()
        self.selected_types = [None, None]

        self.tk_images = {}
        self.inactive_tk_images = {}
        self.load_type_icons()

        self.type_buttons = [{}, {}]
        self.result_labels = {}

        self.selected_display_labels = []
        self.selected_icon_labels = []

        self.setup_type_selectors()
        self.setup_selected_display()
        self.setup_result_table()

    def load_type_icons(self):
        for typ in global_infos.pokemon_types:
            normal_path = os.path.join(ICON_FOLDER, ICON_FILENAME_PATTERN.format(typ=typ))
            faded_path = os.path.join(ICON_FOLDER, ICON_FILENAME_PATTERN.format(typ=typ).replace(".png", "_faded.png"))
            try:
                self.tk_images[typ] = tk.PhotoImage(file=normal_path)
                self.inactive_tk_images[typ] = tk.PhotoImage(file=normal_path) # TODO CHANGE TO faded_path after tweaking the images!
            except Exception as e:
                print(f"Fehler beim Laden der Icons für {typ}: {e}")
                self.tk_images[typ] = None
                self.inactive_tk_images[typ] = None

    def setup_type_selectors(self):
        frame = ttk.LabelFrame(self.root, text="Typen auswählen")
        frame.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.type_frames = []
        for idx in range(2):
            subframe = tk.Frame(frame)
            subframe.grid(row=1, column=idx, padx=(20 if idx == 1 else 0), pady=5)
            self.type_frames.append(subframe)

            label = ttk.Label(subframe, text=f"Typ {idx + 1}", font=('Arial', 11, 'bold'))
            label.grid(row=0, column=0, columnspan=3, pady=(0, 5))

            for i, typ in enumerate(global_infos.pokemon_types):
                row = i % 6 + 1
                col = i // 6
                image = self.tk_images.get(typ)
                faded = self.inactive_tk_images.get(typ)
                if not image or not faded:
                    continue

                btn = tk.Button(subframe, image=faded, relief="flat", bd=1, cursor="hand2", bg="white")
                btn.grid(row=row, column=col, padx=2, pady=2)
                btn.config(command=lambda b=btn, index=idx, t=typ: self.select_type(b, index, t))
                self.type_buttons[idx][typ] = btn

    def setup_selected_display(self):
        frame = ttk.LabelFrame(self.root, text="Ausgewählte Typen")
        frame.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        self.selected_display_labels = []
        self.selected_icon_labels = []

        for i in range(2):
            lbl = ttk.Label(frame, text=f"Typ {i + 1}:")
            lbl.grid(row=0, column=i * 2, padx=10)
            icon = tk.Label(frame)
            icon.grid(row=0, column=i * 2 + 1)
            self.selected_display_labels.append(lbl)
            self.selected_icon_labels.append(icon)

    def setup_result_table(self):
        self.table_frame = ttk.LabelFrame(self.root, text="Effektivitäten")
        self.table_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        for col, label in enumerate(EFFECT_LABELS):
            header = ttk.Label(self.table_frame, text=label, font=("Arial", 12, "bold"))
            header.grid(row=0, column=col, padx=10, pady=5)
            self.result_labels[label] = []

    def select_type(self, button, type_index, typ):
        current = self.selected_types[type_index]
        if current == typ and type_index == 1:
            self.selected_types[type_index] = None
        else:
            self.selected_types[type_index] = typ

        self.update_buttons()
        self.update_table()
        self.update_selected_icons()

    def update_buttons(self):
        for type_index in [0, 1]:
            for typ, btn in self.type_buttons[type_index].items():
                selected = self.selected_types[type_index] == typ
                image = self.tk_images[typ] if selected else self.inactive_tk_images[typ]
                btn.config(image=image)
                btn.image = image
                btn.config(bg="#d0f0ff" if selected else "white", relief="sunken" if selected else "flat")

    def update_selected_icons(self):
        # Zwischenzeile komplett leeren
        for i in [0, 1]:
            self.selected_display_labels[i].config(text="")
            self.selected_icon_labels[i].config(image=tk.PhotoImage(file="type_icons/empty.png"), text="")
            self.selected_icon_labels[i].image = tk.PhotoImage(file="type_icons/empty.png")

        # Typ 1 ist immer vorhanden und wird angezeigt
        if self.selected_types[0]:
            self.selected_display_labels[0].config(text="Typ 1:")
            self.selected_icon_labels[0].config(image=self.tk_images[self.selected_types[0]])
            self.selected_icon_labels[0].image = self.tk_images[self.selected_types[0]]

        # Typ 2 nur anzeigen, wenn gesetzt
        if self.selected_types[1]:
            self.selected_display_labels[1].config(text="Typ 2:")
            self.selected_icon_labels[1].config(image=self.tk_images[self.selected_types[1]])
            self.selected_icon_labels[1].image = self.tk_images[self.selected_types[1]]

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
                lbl.image = icon
                lbl.grid(row=row_index + 1, column=col_index, padx=2, pady=1)
                self.result_labels[EFFECT_LABELS[col_index]].append(lbl)

def main():
    root = tk.Tk()
    app = TypeEffectivenessApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
