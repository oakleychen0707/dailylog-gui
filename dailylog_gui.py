import os
import json
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from datetime import datetime, timedelta
import tkinter.font as tkfont

DATA_DIR = os.path.expanduser("~/.dailylog")
DATA_FILE = os.path.join(DATA_DIR, "data.json")

def ensure_data_file():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump({}, f)

def load_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def today():
    return datetime.now().strftime("%Y-%m-%d")

def yesterday():
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

def find_previous_day_with_data():
    data = load_data()
    dates = sorted(data.keys(), reverse=True)
    today_str = today()
    for d in dates:
        if d < today_str:
            return d
    return None

def next_working_day(start=None):
    d = datetime.now() if start is None else datetime.strptime(start, "%Y-%m-%d")
    while True:
        d += timedelta(days=1)
        if d.weekday() < 5:
            return d.strftime("%Y-%m-%d")

def add_log(start, end, desc):
    d = today()
    data = load_data()
    if d not in data:
        data[d] = {"jira": [], "logs": [], "next_date": next_working_day(d), "next_jira": []}
    data[d]["logs"].append({"start": start, "end": end, "desc": desc})
    save_data(data)

def update_log(index, start, end):
    d = today()
    data = load_data()
    if d in data and 0 <= index < len(data[d]["logs"]):
        data[d]["logs"][index]["start"] = start
        data[d]["logs"][index]["end"] = end
        save_data(data)
        return True
    return False

def add_jira(link, future=False):
    d = today()
    data = load_data()
    if d not in data:
        data[d] = {"jira": [], "logs": [], "next_date": next_working_day(d), "next_jira": []}
    key = "next_jira" if future else "jira"
    data[d][key].append(link)
    save_data(data)

def set_next_date(date_str):
    d = today()
    data = load_data()
    if d not in data:
        data[d] = {"jira": [], "logs": [], "next_date": date_str, "next_jira": []}
    else:
        data[d]["next_date"] = date_str
    save_data(data)

def delete_log(index):
    d = today()
    data = load_data()
    if d in data and 0 <= index < len(data[d]["logs"]):
        removed = data[d]["logs"].pop(index)
        save_data(data)
        return removed
    return None

def delete_jira(index, future=False):
    d = today()
    data = load_data()
    key = "next_jira" if future else "jira"
    if d in data and 0 <= index < len(data[d][key]):
        removed = data[d][key].pop(index)
        save_data(data)
        return removed
    return None

def get_logs():
    d = today()
    data = load_data()
    return data.get(d, {}).get("logs", [])

def get_jiras(future=False):
    d = today()
    data = load_data()
    key = "next_jira" if future else "jira"
    return data.get(d, {}).get(key, [])

def get_next_date():
    d = today()
    data = load_data()
    return data.get(d, {}).get("next_date", next_working_day(d))

def calc_total_hours(logs):
    total = 0.0
    for log in logs:
        t1 = datetime.strptime(log["start"], "%H:%M")
        t2 = datetime.strptime(log["end"], "%H:%M")
        delta = (t2 - t1).seconds / 3600
        total += delta
    return round(total, 1)

def format_date(d):
    return datetime.strptime(d, "%Y-%m-%d").strftime("%Y/%m/%d")

def prune_old_logs(days=5):
    data = load_data()
    cutoff = datetime.now() - timedelta(days=days)
    to_delete = [date for date in data if datetime.strptime(date, "%Y-%m-%d") < cutoff]
    for d in to_delete:
        del data[d]
    save_data(data)

def gui():
    prune_old_logs(days=5)

    sorted_log_indices = []  # 用來記錄排序後 listbox 每列對應原始 logs 的 index

    def refresh():
        nonlocal sorted_log_indices
        log_list.delete(0, tk.END)
        logs = get_logs()
        indexed_logs = list(enumerate(logs))
        indexed_logs.sort(key=lambda x: x[1]["start"])
        sorted_log_indices = [idx for idx, _ in indexed_logs]

        for _, log in indexed_logs:
            log_list.insert(tk.END, f"{log['start']} → {log['end']} {log['desc']}")

        jira_list.delete(0, tk.END)
        for link in get_jiras():
            jira_list.insert(tk.END, link)

        next_jira_list.delete(0, tk.END)
        for link in get_jiras(True):
            next_jira_list.insert(tk.END, link)

        total_label.config(text=f"今日總時數：{calc_total_hours(logs)} 小時")

        next_entry.delete(0, tk.END)
        next_entry.insert(0, get_next_date())

        # ✅ 自動產生群組貼文（若有 Jira 或 next_jira）
        section = load_data().get(today(), {})
        if section.get("jira") or section.get("next_jira"):
            lines = []
            lines.append(format_date(today()))
            for i, link in enumerate(section.get("jira", []), 1):
                lines.append(f"{i}. {link}")
            lines.append("")
            lines.append(format_date(section.get("next_date", next_working_day(today()))) + " 預計")
            for i, link in enumerate(section.get("next_jira", []), 1):
                lines.append(f"{i}. {link}")
            post_text.delete(1.0, tk.END)
            post_text.insert(tk.END, "\n".join(lines))

    def copy_yesterday_jira():
        d = today()
        prev = find_previous_day_with_data()
        if not prev:
            messagebox.showinfo("資訊", "找不到之前有紀錄的日期可複製")
            return

        data = load_data()
        if d not in data:
            data[d] = {"jira": [], "logs": [], "next_date": next_working_day(d), "next_jira": []}

        prev_jira = data[prev].get("jira", [])
        prev_next_jira = data[prev].get("next_jira", [])
        today_jira = set(data[d].get("jira", []))
        today_next_jira = set(data[d].get("next_jira", []))

        new_jira = [j for j in prev_jira if j not in today_jira]
        new_next_jira = [j for j in prev_next_jira if j not in today_next_jira]

        data[d]["jira"].extend(new_jira)
        data[d]["next_jira"].extend(new_next_jira)
        save_data(data)

        messagebox.showinfo("成功", f"已從 {prev} 複製 Jira({len(new_jira)}) 和預計 Jira({len(new_next_jira)})")
        refresh()

    def add_log_dialog():
        dialog = tk.Toplevel(root)
        dialog.title("新增工作紀錄")
        dialog.geometry("300x240")
        dialog.transient(root)  # 視窗關聯主視窗
        dialog.grab_set()       # Modal

        ttk.Label(dialog, text="開始時間 (HH:MM):").pack(pady=(10, 0))
        start_entry = ttk.Entry(dialog)
        start_entry.pack()

        ttk.Label(dialog, text="結束時間 (HH:MM):").pack(pady=(10, 0))
        end_entry = ttk.Entry(dialog)
        end_entry.pack()

        ttk.Label(dialog, text="工作描述:").pack(pady=(10, 0))
        desc_entry = ttk.Entry(dialog)
        desc_entry.pack()

        def on_ok():
            start = start_entry.get().strip()
            end = end_entry.get().strip()
            desc = desc_entry.get().strip()
            if not start or not end or not desc:
                messagebox.showwarning("警告", "請完整填寫所有欄位")
                return
            # 時間格式檢查
            try:
                datetime.strptime(start, "%H:%M")
                datetime.strptime(end, "%H:%M")
            except ValueError:
                messagebox.showerror("格式錯誤", "時間格式錯誤，請輸入 HH:MM")
                return
            add_log(start, end, desc)
            dialog.destroy()
            refresh()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=15)
        ttk.Button(btn_frame, text="確定", command=on_ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=10)

        start_entry.focus()
        dialog.bind("<Return>", lambda event: on_ok())

    def edit_log_time():
        sel = log_list.curselection()
        if not sel:
            messagebox.showwarning("警告", "請先選擇要修改的工作紀錄")
            return
        display_idx = sel[0]
        real_idx = sorted_log_indices[display_idx]
        logs = get_logs()
        log = logs[real_idx]

        dialog = tk.Toplevel(root)
        dialog.title("修改工作紀錄")
        dialog.geometry("300x260")
        dialog.transient(root)
        dialog.grab_set()

        ttk.Label(dialog, text="開始時間 (HH:MM):").pack(pady=(10, 0))
        start_entry = ttk.Entry(dialog)
        start_entry.insert(0, log["start"])
        start_entry.pack()

        ttk.Label(dialog, text="結束時間 (HH:MM):").pack(pady=(10, 0))
        end_entry = ttk.Entry(dialog)
        end_entry.insert(0, log["end"])
        end_entry.pack()

        ttk.Label(dialog, text="工作描述:").pack(pady=(10, 0))
        desc_entry = ttk.Entry(dialog)
        desc_entry.insert(0, log["desc"])
        desc_entry.pack()

        def on_ok():
            new_start = start_entry.get().strip()
            new_end = end_entry.get().strip()
            new_desc = desc_entry.get().strip()

            if not new_start or not new_end or not new_desc:
                messagebox.showwarning("警告", "請完整填寫所有欄位")
                return

            try:
                datetime.strptime(new_start, "%H:%M")
                datetime.strptime(new_end, "%H:%M")
            except ValueError:
                messagebox.showerror("格式錯誤", "時間格式錯誤，請輸入 HH:MM")
                return

            d = today()
            data = load_data()
            if d in data and 0 <= real_idx < len(data[d]["logs"]):
                data[d]["logs"][real_idx]["start"] = new_start
                data[d]["logs"][real_idx]["end"] = new_end
                data[d]["logs"][real_idx]["desc"] = new_desc
                save_data(data)
                messagebox.showinfo("成功", "工作紀錄已更新")
                dialog.destroy()
                refresh()
            else:
                messagebox.showerror("錯誤", "更新失敗")

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=15)
        ttk.Button(btn_frame, text="確定", command=on_ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=10)

        start_entry.focus()
        dialog.bind("<Return>", lambda event: on_ok())


    def add_jira_dialog(future=False):
        url = simpledialog.askstring("新增 Jira", "請輸入 Jira 連結")
        if url:
            add_jira(url, future)
            refresh()

    def generate_group_post():
        d = today()
        data = load_data()
        if d not in data:
            messagebox.showerror("錯誤", "今日尚無資料")
            return
        section = data[d]
        lines = []
        lines.append(format_date(d))
        for i, link in enumerate(section.get("jira", []), 1):
            lines.append(f"{i}. {link}")
        lines.append("")
        lines.append(format_date(section.get("next_date")) + " 預計")
        for i, link in enumerate(section.get("next_jira", []), 1):
            lines.append(f"{i}. {link}")
        post_text.delete(1.0, tk.END)
        post_text.insert(tk.END, "\n".join(lines))

    def copy_to_clipboard():
        content = post_text.get(1.0, tk.END).strip()
        if content:
            root.clipboard_clear()
            root.clipboard_append(content)
            root.update()
            messagebox.showinfo("複製成功", "群組貼文已複製到剪貼簿")

    def update_next_date():
        val = next_entry.get()
        try:
            datetime.strptime(val, "%Y-%m-%d")
            set_next_date(val)
            messagebox.showinfo("成功", f"已更新預計日期為 {val}")
            refresh()
        except ValueError:
            messagebox.showerror("格式錯誤", "請輸入正確日期格式：YYYY-MM-DD")

    def delete_selected_log():
        sel = log_list.curselection()
        if not sel:
            messagebox.showwarning("警告", "請先選擇要刪除的工作紀錄")
            return
        display_idx = sel[0]
        real_idx = sorted_log_indices[display_idx]
        removed = delete_log(real_idx)
        if removed:
            messagebox.showinfo("刪除成功", f"已刪除：{removed['start']} → {removed['end']} {removed['desc']}")
            refresh()

    def delete_selected_jira(future=False):
        lst = next_jira_list if future else jira_list
        sel = lst.curselection()
        if not sel:
            messagebox.showwarning("警告", "請先選擇要刪除的 Jira 項目")
            return
        idx = sel[0]
        removed = delete_jira(idx, future)
        if removed:
            messagebox.showinfo("刪除成功", f"已刪除 Jira：{removed}")
            refresh()

            # 新增這個函式在 gui() 裡面
    def copy_all_desc():
        logs = get_logs()
        descs = [log["desc"] for log in logs if log.get("desc")]
        content = "\n".join(descs)
        if content:
            root.clipboard_clear()
            root.clipboard_append(content)
            root.update()
            messagebox.showinfo("複製成功", "所有描述已複製到剪貼簿")
        else:
            messagebox.showinfo("提示", "今日沒有工作描述可複製")


    root = tk.Tk()
    root.title("📅 DailyLog GUI")
    root.geometry("650x750")

    top_frame = ttk.Frame(root)
    top_frame.pack(pady=(10, 6), padx=10)

    # 在 top_frame 用 grid 排列兩個 Label
    label = ttk.Label(top_frame, text="✔️ 今日工作紀錄：")
    label.grid(row=0, column=0)

    bold_font = tkfont.Font(weight="bold")
    total_label = ttk.Label(top_frame, text="", font=bold_font)
    total_label.grid(row=0, column=1, padx=(5, 0))

    # 讓 top_frame 裡的兩個欄位寬度剛好，整個 top_frame 再用 pack 置中
    top_frame.pack(anchor='center')

    log_list = tk.Listbox(root, width=60, height=7)
    log_list.pack(pady=(3))

    log_btn_frame = ttk.Frame(root)
    log_btn_frame.pack(pady=2)
    ttk.Button(log_btn_frame, text="➕ 新增工作紀錄", command=add_log_dialog).pack(side=tk.LEFT, padx=4)
    ttk.Button(log_btn_frame, text="✏️ 修改選取時間", command=edit_log_time).pack(side=tk.LEFT, padx=4)
    ttk.Button(log_btn_frame, text="🗑 刪除選取工作紀錄", command=delete_selected_log).pack(side=tk.LEFT, padx=4)
    ttk.Button(log_btn_frame, text="📋 複製描述", command=copy_all_desc).pack(side=tk.LEFT, padx=4)

    ttk.Label(root, text="📌 今日 Jira 任務：").pack()
    jira_list = tk.Listbox(root, width=60, height=5)
    jira_list.pack(pady=3)
    jira_btn_frame = ttk.Frame(root)
    jira_btn_frame.pack(pady=2)
    ttk.Button(jira_btn_frame, text="➕ 新增今天 Jira", command=lambda: add_jira_dialog(False)).pack(side=tk.LEFT, padx=4)
    ttk.Button(jira_btn_frame, text="🗑 刪除選取今天 Jira", command=lambda: delete_selected_jira(False)).pack(side=tk.LEFT, padx=4)
    ttk.Button(jira_btn_frame, text="📥 複製上次 Jira 與預計 Jira", command=copy_yesterday_jira).pack(side=tk.LEFT, padx=4)

    ttk.Label(root, text="📍 預計下次 Jira 任務：").pack()
    next_jira_list = tk.Listbox(root, width=60, height=5)
    next_jira_list.pack(pady=3)
    next_jira_btn_frame = ttk.Frame(root)
    next_jira_btn_frame.pack(pady=2)
    ttk.Button(next_jira_btn_frame, text="➕ 新增下次 Jira", command=lambda: add_jira_dialog(True)).pack(side=tk.LEFT, padx=4)
    ttk.Button(next_jira_btn_frame, text="🗑 刪除選取下次 Jira", command=lambda: delete_selected_jira(True)).pack(side=tk.LEFT, padx=4)

    date_frame = ttk.Frame(root)
    date_frame.pack(pady=6)
    ttk.Label(date_frame, text="📆 預計日期 (YYYY-MM-DD)：").pack(side=tk.LEFT, padx=(0,8))
    next_entry = ttk.Entry(date_frame, width=20)
    next_entry.pack(side=tk.LEFT)
    ttk.Button(date_frame, text="📅 更新日期", command=update_next_date).pack(side=tk.LEFT, padx=8)

    ttk.Label(root, text="📍 群組貼文：").pack()

    post_text = tk.Text(root, height=8, width=60)
    post_text.pack(pady=4)

    post_btn_frame = ttk.Frame(root)
    post_btn_frame.pack(pady=4)
    ttk.Button(post_btn_frame, text="📝 產生群組貼文", command=generate_group_post).pack(side=tk.LEFT, padx=8)
    ttk.Button(post_btn_frame, text="📋 複製貼文到剪貼簿", command=copy_to_clipboard).pack(side=tk.LEFT, padx=8)

    refresh()
    root.mainloop()

if __name__ == "__main__":
    ensure_data_file()
    gui()