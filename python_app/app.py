import tkinter
import customtkinter
import serial
import serial.tools.list_ports
import threading
import collections
import time
import os
from PIL import Image, ImageTk

# Configurează aspectul aplicatiei 
customtkinter.set_appearance_mode("Dark")
customtkinter.set_default_color_theme("green")

class App(customtkinter.CTk):# clasa penrtu interfata 
    def __init__(self):
        super().__init__()

        self.title("Dashboard")
        self.alert_threshold = 20 # Prag implicit în cm 
        # Rulare în full screen (fără bara de instrumente/titlu) pentru ecranul de 3.5 inch
        self.geometry("480x640+0+0")
        self.attributes("-fullscreen", True)
        
        # Deoarece butonul de închidere al ferestrei va dispărea, adăugăm posibilitatea de a ieși cu tasta Escape
        self.bind("<Escape>", lambda e: self.on_closing())

        # Layout: tot pe o singură coloană compactă
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # graficul ia spațiul rămas

        # ── Bara de sus: stare conexiune + buton ieșire ──
        self.top_bar = customtkinter.CTkFrame(self, corner_radius=0, fg_color="#2e7d32")
        self.top_bar.grid(row=0, column=0, sticky="ew")
        self.top_bar.grid_columnconfigure(0, weight=1)

        self.status_label = customtkinter.CTkLabel(self.top_bar, text="⏳ Se caută senzorul...",
                                                    font=customtkinter.CTkFont(size=14),
                                                    text_color="white")
        self.status_label.grid(row=0, column=0, padx=(10, 4), pady=8, sticky="w")

        self.exit_btn = customtkinter.CTkButton(self.top_bar, text="✕", width=40, height=40,
                                                 font=customtkinter.CTkFont(size=18, weight="bold"),
                                                 fg_color="#c62828", hover_color="#e53935",
                                                 command=self.on_closing)
        self.exit_btn.grid(row=0, column=1, padx=(0, 6), pady=8)

        # ── Afișare distanța
        self.distance_label = customtkinter.CTkLabel(self, text="-- cm",
                                                      font=customtkinter.CTkFont(size=64, weight="bold"),
                                                      text_color="#4caf50")
        self.distance_label.grid(row=1, column=0, pady=(10, 4))

        # ── Grafic Canvas ──
        self.graph_canvas = tkinter.Canvas(self, bg="#1a1a1a", highlightthickness=0)
        self.graph_canvas.grid(row=2, column=0, padx=6, pady=(4, 2), sticky="nsew")
        self.graph_canvas.bind("<Configure>", self.on_canvas_resize)

        # ── Bara de jos
        self.bottom_bar = customtkinter.CTkFrame(self, corner_radius=0, fg_color="#1b3d1e")
        self.bottom_bar.grid(row=3, column=0, sticky="ew")
        self.bottom_bar.grid_columnconfigure(0, weight=1)

        # Row 0
        self.threshold_label = customtkinter.CTkLabel(self.bottom_bar, text=f"Prag: {self.alert_threshold} cm",
                                                       font=customtkinter.CTkFont(size=14),
                                                       text_color="#81c784")
        self.threshold_label.grid(row=0, column=0, padx=6, pady=(6, 2))

        # Row 1
        self.threshold_controls = customtkinter.CTkFrame(self.bottom_bar, fg_color="transparent")
        self.threshold_controls.grid(row=1, column=0, sticky="ew")
        self.threshold_controls.grid_columnconfigure(1, weight=1)

        self.threshold_minus_btn = customtkinter.CTkButton(self.threshold_controls, text="−", width=50, height=40,
                                                           font=customtkinter.CTkFont(size=22, weight="bold"),
                                                           command=lambda: self.adjust_threshold(-1))
        self.threshold_minus_btn.grid(row=0, column=0, padx=(6, 4), pady=(2, 6))

        self.threshold_slider = customtkinter.CTkSlider(self.threshold_controls, from_=0, to=100, number_of_steps=100,
                                                        command=self.update_threshold, height=20)
        self.threshold_slider.set(self.alert_threshold)
        self.threshold_slider.grid(row=0, column=1, padx=4, pady=(2, 6), sticky="ew")

        self.threshold_plus_btn = customtkinter.CTkButton(self.threshold_controls, text="+", width=50, height=40,
                                                          font=customtkinter.CTkFont(size=22, weight="bold"),
                                                          command=lambda: self.adjust_threshold(1))
        self.threshold_plus_btn.grid(row=0, column=3, padx=(4, 6), pady=(2, 6))

        # Date
        self.data_len = 40  # Fewer data points for narrow portrait screen
        self.data_y = collections.deque([0] * self.data_len, maxlen=self.data_len)
        self.canvas_width = 100 # Substituent inițial

        # Încarcarea imaginii de fundal
        self.bg_image = None
        self.bg_photo = None
        bg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "background.png")
        if os.path.exists(bg_path):
            self.bg_image = Image.open(bg_path)

        # Variabile seriale
        self.serial_conn = None
        self.is_running = True
        self.scan_thread = None

        # Pornește scanarea automată
        self.start_auto_scan()

    def start_auto_scan(self):
        """Pornește scanarea automată a porturilor seriale."""
        self.scan_thread = threading.Thread(target=self.auto_scan_and_connect, daemon=True)
        self.scan_thread.start()

    def auto_scan_and_connect(self):
        """Scanează toate porturile seriale și se conectează automat."""
        while self.is_running:
            ports = serial.tools.list_ports.comports()
            for port in ports:
                if not self.is_running:
                    return
                try:
                    self.serial_conn = serial.Serial(port.device, 115200, timeout=1)
                    # Actualizează interfața - conectat
                    self.after(0, lambda p=port.device: self.status_label.configure(
                        text=f"● Conectat: {p}", text_color="#c8e6c9"))
                    # Citește datele
                    self.read_serial_data()
                    # Dacă ajungem aici, conexiunea s-a pierdut
                    self.after(0, lambda: self.status_label.configure(
                        text="⏳ Reconectare...", text_color="#ffcc80"))
                except Exception:
                    continue
            # Niciun port găsit sau toate au eșuat, reîncearcă
            self.after(0, lambda: self.status_label.configure(
                text="⏳ Se caută senzorul...", text_color="white"))
            time.sleep(2)

    def disconnect(self):
        self.is_running = False
        if self.serial_conn:
            try:
                self.serial_conn.close()
            except Exception:
                pass

    def update_threshold(self, value):
        self.alert_threshold = int(value)
        self.threshold_label.configure(text=f"Prag: {self.alert_threshold} cm")

    def adjust_threshold(self, delta):
        new_val = max(0, min(100, self.alert_threshold + delta))
        self.alert_threshold = new_val
        self.threshold_slider.set(new_val)
        self.threshold_label.configure(text=f"Prag: {self.alert_threshold} cm")

    def read_serial_data(self):
        while self.is_running and self.serial_conn and self.serial_conn.is_open:
            try:
                line = self.serial_conn.readline().decode('utf-8').strip()
                if line:
                    val = None
                    # Parse "Distance changed: X cm" format from ESP
                    if "Distance changed:" in line:
                        try:
                            val = float(line.split(":")[1].replace("cm", "").strip())
                        except (ValueError, IndexError):
                            pass
                    else:
                        # Fallback: try parsing as raw number
                        try:
                            val = float(line)
                        except ValueError:
                            pass

                    if val is not None:
                        self.update_ui(val)

            except Exception as e:
                print(f"Read Error: {e}")
                self.is_running = False
                break


    def update_ui(self, value):
        # Planifică actualizarea pe firul principal
        self.after(0, lambda: self._update_ui_internal(value))

    def _update_ui_internal(self, value):
        # Actualizează textul și culoarea
        if value <= self.alert_threshold:
            self.distance_label.configure(text=f"{int(value)} cm", text_color="#ef5350")
        else:
            self.distance_label.configure(text=f"{int(value)} cm", text_color="#4caf50")
        
        # Actualizează datele graficului
        self.data_y.append(value)
        self.draw_graph()

    def on_canvas_resize(self, event):
        self.canvas_width = event.width
        self._resize_bg(event.width, event.height)
        self.draw_graph()

    def _resize_bg(self, w, h):
        """Redimensionează imaginea de fundal la 4:3 centrat pe canvas."""
        if self.bg_image and w > 1 and h > 1:
            # Calculează dimensiunea 4:3 care încape în canvas
            target_ratio = 4 / 3
            canvas_ratio = w / h
            if canvas_ratio > target_ratio:
                # Canvas mai lat decât 4:3 — limitează după înălțime
                new_h = h
                new_w = int(h * target_ratio)
            else:
                # Canvas mai înalt decât 4:3 — limitează după lățime
                new_w = w
                new_h = int(w / target_ratio)
            img = self.bg_image.resize((new_w, new_h), Image.LANCZOS)
            self.bg_photo = ImageTk.PhotoImage(img)

    def draw_graph(self):
        self.graph_canvas.delete("all")

        width = self.graph_canvas.winfo_width()
        height = self.graph_canvas.winfo_height()

        # Desenează imaginea de fundal
        if self.bg_photo:
            self.graph_canvas.create_image(width // 2, height // 2, image=self.bg_photo)

        if not self.data_y:
            return

        # Scări
        max_dist = max(max(self.data_y), 50) * 1.2
        step_x = width / (self.data_len - 1)
        
        # Creează coordonatele liniei
        coords = []
        for i, val in enumerate(self.data_y):
            x = i * step_x
            # Inversează Y deoarece 0 pe canvas este sus
            y = height - (val / max_dist * height) 
            coords.append(x)
            coords.append(y)
        
        if len(coords) >= 4:
            self.graph_canvas.create_line(coords, fill="#66bb6a", width=2, smooth=True)

    def on_closing(self):
        self.disconnect()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
