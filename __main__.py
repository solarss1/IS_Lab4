from typing import List, Tuple, Dict
from dataclasses import dataclass
import sys
import tkinter as tk
from tkinter import messagebox

# ======================= МОДЕЛЬ CSP =======================

@dataclass
class Slot:
    id: int
    cells: List[Tuple[int, int]]  # список координат (row, col) для цього слова


def parse_grid(raw: List[str]):
    """
    raw – список рядків з символами:
      '#' – стіна (чорна клітинка)
      '.' – порожня клітинка
      'A'..'Z' – зафіксована літера
    """
    if not raw:
        raise ValueError("Порожня сітка")

    h = len(raw)
    w = len(raw[0])
    for row in raw:
        if len(row) != w:
            raise ValueError("Усі рядки сітки мають бути однакової довжини")

    grid = [list(row) for row in raw]
    slots: List[Slot] = []
    sid = 0

    # Горизонтальні слоти
    for r in range(h):
        c = 0
        while c < w:
            if grid[r][c] != '#':
                # початок слота, якщо зліва стіна або край сітки
                if c == 0 or grid[r][c - 1] == '#':
                    start = c
                    while c < w and grid[r][c] != '#':
                        c += 1
                    length = c - start
                    if length > 1:
                        slots.append(Slot(sid, [(r, cc) for cc in range(start, c)]))
                        sid += 1
                    continue
            c += 1

    # Вертикальні слоти
    for c in range(w):
        r = 0
        while r < h:
            if grid[r][c] != '#':
                # початок слота, якщо зверху стіна або край
                if r == 0 or grid[r - 1][c] == '#':
                    start = r
                    while r < h and grid[r][c] != '#':
                        r += 1
                    length = r - start
                    if length > 1:
                        slots.append(Slot(sid, [(rr, c) for rr in range(start, r)]))
                        sid += 1
                    continue
            r += 1

    return grid, slots


def slot_length(slot: Slot) -> int:
    return len(slot.cells)


def build_domains(slots: List[Slot], dictionary: List[str]) -> Dict[int, List[str]]:
    """
    Для кожного слота підбираємо слова відповідної довжини.
    """
    by_len: Dict[int, List[str]] = {}
    for w in dictionary:
        w = w.strip()
        if not w:
            continue
        by_len.setdefault(len(w), []).append(w.upper())

    domains: Dict[int, List[str]] = {}
    for slot in slots:
        domains[slot.id] = list(by_len.get(slot_length(slot), []))
    return domains


def is_consistent(word: str, slot: Slot, grid: List[List[str]]) -> bool:
    """
    Перевіряємо, чи слово сумісне з уже заповненими літерами в сітці.
    """
    for ch, (r, c) in zip(word, slot.cells):
        if grid[r][c] != '.' and grid[r][c] != ch:
            return False
    return True


def apply_word(word: str, slot: Slot, grid: List[List[str]]):
    """
    Вписуємо слово в сітку, повертаємо список попередніх значень для відкату.
    """
    prev_state = []
    for ch, (r, c) in zip(word, slot.cells):
        prev_state.append((r, c, grid[r][c]))
        grid[r][c] = ch
    return prev_state


def undo(prev_state, grid: List[List[str]]):
    """
    Відкат змін у сітці.
    """
    for r, c, ch in prev_state:
        grid[r][c] = ch


def select_unassigned_slot(
    slots: List[Slot],
    assignment: Dict[int, str],
    domains: Dict[int, List[str]],
    grid: List[List[str]],
):
    """
    Вибрати наступний слот для присвоєння (MRV – мінімум допустимих значень).
    """
    best_slot = None
    best_count = None

    for slot in slots:
        if slot.id in assignment:
            continue

        count = 0
        for w in domains[slot.id]:
            if is_consistent(w, slot, grid):
                count += 1

        if best_count is None or count < best_count:
            best_count = count
            best_slot = slot

        if best_count == 0:
            break

    return best_slot, best_count


def backtrack(
    slots: List[Slot],
    grid: List[List[str]],
    domains: Dict[int, List[str]],
    assignment: Dict[int, str],
    forbid_reuse: bool,
) -> bool:
    """
    Пошук у глибину з відкатами (backtracking).
    """
    if len(assignment) == len(slots):
        return True  # всі слоти заповнені

    slot, count = select_unassigned_slot(slots, assignment, domains, grid)
    if slot is None or count == 0:
        return False

    for word in domains[slot.id]:
        if forbid_reuse and word in assignment.values():
            continue
        if not is_consistent(word, slot, grid):
            continue

        prev_state = apply_word(word, slot, grid)
        assignment[slot.id] = word

        if backtrack(slots, grid, domains, assignment, forbid_reuse):
            return True

        # відкат
        del assignment[slot.id]
        undo(prev_state, grid)

    return False


def solve_crossword(raw_grid: List[str], dictionary: List[str], forbid_reuse: bool = False):
    """
    Повертає:
      success: bool – чи знайдено розв’язок
      solved_grid: List[str] – заповнена сітка (як список рядків)
      assignment: Dict[int, str] – {id_слота: слово}
      slots: список слотів, щоб при бажанні подивитись координати
    """
    grid, slots = parse_grid(raw_grid)
    if not slots:
        raise ValueError("У сітці немає жодного слота (послідовності довжини ≥ 2)")
    domains = build_domains(slots, dictionary)
    assignment: Dict[int, str] = {}

    success = backtrack(slots, grid, domains, assignment, forbid_reuse)
    solved_grid = ["".join(row) for row in grid]
    return success, solved_grid, assignment, slots

# ======================= ЧИТАННЯ З ФАЙЛІВ =======================

def read_grid_from_file(path: str) -> List[str]:
    """
    grid.txt:
      кожен рядок – строка кросворду.
      Використовуються символи: '#', '.', 'A'..'Z'
    """
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f]
    # відкидаємо порожні рядки по краях
    lines = [ln for ln in lines if ln.strip() != ""]
    return lines


def read_dict_from_file(path: str) -> List[str]:
    """
    dict.txt:
      по одному слову в рядок.
    """
    with open(path, "r", encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]
    return words

# ======================= CLI-РЕЖИМ =======================

def run_cli(grid_path: str = "grid.txt", dict_path: str = "dict.txt", forbid_reuse: bool = False):
    print(f"Читаю сітку з: {grid_path}")
    print(f"Читаю словник з: {dict_path}")
    raw_grid = read_grid_from_file(grid_path)
    dictionary = read_dict_from_file(dict_path)

    print("\nПочаткова сітка:")
    for row in raw_grid:
        print(row)

    success, solved, assignment, slots = solve_crossword(raw_grid, dictionary, forbid_reuse)

    if success:
        print("\nЗнайдено розв’язок:")
        for row in solved:
            print(row)
        print("\nПрисвоєння слотів (id_слота: слово):")
        for slot in slots:
            print(f"Slot {slot.id} {slot.cells}: {assignment.get(slot.id)}")
    else:
        print("\nРозв’язку немає. Можливі причини:")
        print("- недостатньо слів потрібної довжини у словнику;")
        print("- сітка несумісна з заданими словами;")
        print("- у grid є зафіксовані літери, які конфліктують з можливими словами.")

# ======================= GUI НА TKINTER =======================

class CrosswordGUI:
    def __init__(self, master, grid_path="grid.txt", dict_path="dict.txt"):
        self.master = master
        self.master.title("CSP Crossword Solver")

        self.grid_path = grid_path
        self.dict_path = dict_path

        # завантажуємо дані
        try:
            self.raw_grid = read_grid_from_file(self.grid_path)
            self.dictionary = read_dict_from_file(self.dict_path)
        except Exception as e:
            messagebox.showerror("Помилка читання файлів", str(e))
            self.raw_grid = [
                "#####",
                "#..##",
                "#..##",
                "##..#",
                "#####",
            ]
            self.dictionary = ["AT", "NO", "ON", "AN", "TOO"]

        self.forbid_reuse_var = tk.BooleanVar(value=False)

        self.cells_widgets: List[List[tk.Label]] = []

        control_frame = tk.Frame(master)
        control_frame.pack(side=tk.TOP, pady=5)

        solve_button = tk.Button(control_frame, text="Розв’язати", command=self.on_solve)
        solve_button.pack(side=tk.LEFT, padx=5)

        reuse_check = tk.Checkbutton(
            control_frame,
            text="Заборонити повторне використання слів",
            variable=self.forbid_reuse_var,
        )
        reuse_check.pack(side=tk.LEFT, padx=5)

        reload_button = tk.Button(control_frame, text="Перечитати файли", command=self.on_reload)
        reload_button.pack(side=tk.LEFT, padx=5)

        self.status_label = tk.Label(master, text="", fg="blue")
        self.status_label.pack(side=tk.TOP, pady=5)

        self.grid_frame = tk.Frame(master)
        self.grid_frame.pack(side=tk.TOP, pady=5)

        self.draw_grid(self.raw_grid)

    def clear_grid_widgets(self):
        for row in self.cells_widgets:
            for lbl in row:
                lbl.destroy()
        self.cells_widgets = []

    def draw_grid(self, raw_grid: List[str]):
        self.clear_grid_widgets()
        for r, row in enumerate(raw_grid):
            row_widgets = []
            for c, ch in enumerate(row):
                bg = "white"
                fg = "black"
                text = ch
                if ch == "#":
                    bg = "black"
                    fg = "white"
                    text = " "
                elif ch == ".":
                    text = " "

                lbl = tk.Label(
                    self.grid_frame,
                    text=text,
                    width=2,
                    height=1,
                    borderwidth=1,
                    relief="solid",
                    bg=bg,
                    fg=fg,
                    font=("Consolas", 14),
                )
                lbl.grid(row=r, column=c, padx=1, pady=1)
                row_widgets.append(lbl)
            self.cells_widgets.append(row_widgets)

    def update_grid_display(self, solved_grid: List[str]):
        for r, row in enumerate(solved_grid):
            for c, ch in enumerate(row):
                lbl = self.cells_widgets[r][c]
                if ch == "#":
                    lbl.config(text=" ", bg="black", fg="white")
                elif ch == ".":
                    lbl.config(text=" ", bg="white", fg="black")
                else:
                    lbl.config(text=ch, bg="white", fg="blue")

    def on_solve(self):
        try:
            forbid_reuse = self.forbid_reuse_var.get()
            success, solved, assignment, slots = solve_crossword(
                self.raw_grid, self.dictionary, forbid_reuse
            )
            if success:
                self.update_grid_display(solved)
                self.status_label.config(text="Розв’язок знайдено ✅", fg="green")
            else:
                self.status_label.config(text="Розв’язку немає ❌", fg="red")
        except Exception as e:
            messagebox.showerror("Помилка", str(e))

    def on_reload(self):
        try:
            self.raw_grid = read_grid_from_file(self.grid_path)
            self.dictionary = read_dict_from_file(self.dict_path)
            self.draw_grid(self.raw_grid)
            self.status_label.config(text="Файли перечитані ✅", fg="blue")
        except Exception as e:
            messagebox.showerror("Помилка читання файлів", str(e))


def run_gui(grid_path="grid.txt", dict_path="dict.txt"):
    root = tk.Tk()
    app = CrosswordGUI(root, grid_path, dict_path)
    root.mainloop()

# ======================= MAIN =======================

if __name__ == "__main__":
    # Режими:
    #   python crossword_csp.py             -> CLI, grid.txt + dict.txt, можна редагувати кодом forbid_reuse
    #   python crossword_csp.py gui         -> GUI, grid.txt + dict.txt
    #   python crossword_csp.py cli no-reuse -> CLI, заборонено повтор слів
    args = sys.argv[1:]

    if not args:
        # За замовчуванням – простий CLI
        run_cli()
    elif args[0].lower() == "gui":
        run_gui()
    else:
        forbid_reuse = False
        if len(args) >= 1 and args[0].lower() == "cli":
            if len(args) >= 2 and args[1].lower() == "no-reuse":
                forbid_reuse = True
        run_cli(forbid_reuse=forbid_reuse)
