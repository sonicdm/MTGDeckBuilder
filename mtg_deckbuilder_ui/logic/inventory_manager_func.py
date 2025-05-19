import os

def list_txt_files():
    return [f for f in os.listdir() if f.endswith('.txt')]

def parse_inventory_txt(txt_path):
    rows = []
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(' ', 1)
                if len(parts) == 2 and parts[0].isdigit():
                    rows.append([int(parts[0]), parts[1]])
                else:
                    # fallback: treat as 1 copy if no qty
                    rows.append([1, line])
    except Exception as e:
        return [[0, f"Error: {e}"]]
    return rows

def save_inventory_txt(txt_path, table):
    try:
        with open(txt_path, 'w', encoding='utf-8') as f:
            for row in table:
                if not isinstance(row, (list, tuple)) or len(row) < 2:
                    continue
                qty, name = row[:2]
                if not name or not str(qty).isdigit():
                    continue
                f.write(f"{qty} {name}\n")
        return "Inventory saved."
    except Exception as e:
        return f"Error: {e}"

def import_from_clipboard(clipboard_text):
    rows = []
    for line in clipboard_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(' ', 1)
        if len(parts) == 2 and parts[0].isdigit():
            rows.append([int(parts[0]), parts[1]])
        else:
            rows.append([1, line])
    return rows

