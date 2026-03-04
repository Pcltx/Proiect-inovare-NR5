import tkinter
import customtkinter
import serial
import serial.tools.list_ports
import threading
import collections
import platform
import os
import time

# Verifică sistemul de operare pentru sunet
system_os = platform.system()
if system_os == "Windows":
    import winsound

# Configurează aspectul aplicatiei 
customtkinter.set_appearance_mode("Dark")
customtkinter.set_default_color_theme("blue")

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("Dashboard")
        self.alert_threshold = 20 # Prag implicit în cm 
        self.geometry("320x480")
        self.resizable(False, False)

        # Layout: tot pe o singură coloană compactă
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # graficul ia spațiul rămas

        # ── Bara de sus: port + connect (stacked for portrait) ──
        self.top_bar = customtkinter.CTkFrame(self, corner_radius=0)
        self.top_bar.grid(row=0, column=0, sticky="ew")
        self.top_bar.grid_columnconfigure(0, weight=1)

        # Row 0: Connect button + status indicator
        self.top_row = customtkinter.CTkFrame(self.top_bar, fg_color="transparent")
        self.top_row.grid(row=0, column=0, sticky="ew")
        self.top_row.grid_columnconfigure(0, weight=1)

        self.connect_btn = customtkinter.CTkButton(self.top_row, text="Connect", height=40,
                                                     font=customtkinter.CTkFont(size=14),
                                                     command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=0, padx=(6, 4), pady=(6, 2), sticky="ew")

        self.connect_info = customtkinter.CTkLabel(self.top_row, text="●", text_color="gray",
                                                     font=customtkinter.CTkFont(size=18), width=28)
        self.connect_info.grid(row=0, column=1, padx=(0, 8), pady=(6, 2))

        # Row 1: Port dropdown + refresh
        self.port_row = customtkinter.CTkFrame(self.top_bar, fg_color="transparent")
        self.port_row.grid(row=1, column=0, sticky="ew")
        self.port_row.grid_columnconfigure(0, weight=1)

        self.com_port_var = customtkinter.StringVar(value="Port")
        self.port_menu = customtkinter.CTkOptionMenu(self.port_row, variable=self.com_port_var,
                                                      values=self.get_available_ports(),
                                                      height=40,
                                                      font=customtkinter.CTkFont(size=13))
        self.port_menu.grid(row=0, column=0, padx=(6, 4), pady=(2, 6), sticky="ew")

        self.refresh_btn = customtkinter.CTkButton(self.port_row, text="↻", width=46, height=40,
                                                     font=customtkinter.CTkFont(size=20),
                                                     command=self.refresh_ports)
        self.refresh_btn.grid(row=0, column=1, padx=(4, 6), pady=(2, 6))

        # ── Afișare distanță (centru) ──
        self.distance_label = customtkinter.CTkLabel(self, text="-- cm",
                                                      font=customtkinter.CTkFont(size=64, weight="bold"))
        self.distance_label.grid(row=1, column=0, pady=(10, 4))

        # ── Grafic Canvas ──
        self.graph_canvas = tkinter.Canvas(self, bg="#2b2b2b", highlightthickness=0)
        self.graph_canvas.grid(row=2, column=0, padx=6, pady=(4, 2), sticky="nsew")
        self.graph_canvas.bind("<Configure>", self.on_canvas_resize)

        # ── Bara de jos: threshold (stacked for portrait) ──
        self.bottom_bar = customtkinter.CTkFrame(self, corner_radius=0)
        self.bottom_bar.grid(row=3, column=0, sticky="ew")
        self.bottom_bar.grid_columnconfigure(0, weight=1)

        # Row 0: Label
        self.threshold_label = customtkinter.CTkLabel(self.bottom_bar, text=f"Prag: {self.alert_threshold} cm",
                                                       font=customtkinter.CTkFont(size=14))
        self.threshold_label.grid(row=0, column=0, padx=6, pady=(6, 2))

        # Row 1: − slider +
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

        # Variabile seriale
        self.serial_conn = None
        self.is_running = False
        self.thread = None
        
        # Stare alertă audio
        self.last_beep_time = 0

    def get_available_ports(self):
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports] if ports else ["No Ports"]

    def refresh_ports(self):
        self.port_menu.configure(values=self.get_available_ports())

    def toggle_connection(self):
        if self.serial_conn and self.serial_conn.is_open:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        port = self.com_port_var.get()
        if port in ("Select Port", "Selecteaza portul", "No Ports"):
            return

        try:
            self.serial_conn = serial.Serial(port, 115200, timeout=1)
            self.is_running = True
            self.connect_btn.configure(text="Disconnect", fg_color="red", hover_color="darkred")
            self.connect_info.configure(text="●", text_color="#00d26a")
            
            # Pornește firul de execuție pentru citire
            self.thread = threading.Thread(target=self.read_serial_data, daemon=True)
            self.thread.start()
        except Exception as e:
            self.connect_info.configure(text="●", text_color="red")
            print(e)

    def disconnect(self):
        self.is_running = False
        if self.serial_conn:
            self.serial_conn.close()
        self.connect_btn.configure(text="Connect", fg_color="#1f538d", hover_color="#14375e")
        self.connect_info.configure(text="●", text_color="gray")

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
                        self.check_alert(val)
                        self.update_ui(val)

            except Exception as e:
                print(f"Read Error: {e}")
                self.is_running = False
                break
    
    def check_alert(self, val):
        # Alertă dacă este sub prag
        if 2 <= val <= self.alert_threshold:
            current_time = time.time()
            # Limitează frecvența beep-urilor (de exemplu, maxim la fiecare 500ms dacă e necesar, dar aici dăm beep la fiecare pachet de date care e distanțat de delay-ul de 50ms al Arduino)
            # Intervalul de 50ms ar putea fi prea rapid pentru beep-uri continue, așa că să-l limităm.
            if current_time - self.last_beep_time > 0.3: # Beep maxim la fiecare 300ms
                if system_os == "Windows":
                    # Beep non-blocant nu este ușor posibil cu winsound.Beep (blochează).
                    # Folosirea PlaySound cu SND_ASYNC ar putea fi mai bună, dar necesită un fișier wav.
                    # Vom folosi Beep dar îl vom ține scurt (de exemplu 100ms)
                    try:
                        winsound.Beep(1000, 100)
                    except:
                        pass
                else:
                    # Mac/Linux
                    print('\a')
                self.last_beep_time = current_time

    def update_ui(self, value):
        # Planifică actualizarea pe firul principal
        self.after(0, lambda: self._update_ui_internal(value))

    def _update_ui_internal(self, value):
        # Actualizează textul și culoarea
        if value <= self.alert_threshold:
            self.distance_label.configure(text=f"{int(value)} cm", text_color="red")
        else:
            self.distance_label.configure(text=f"{int(value)} cm", text_color=("black", "white")) # Resetează la modul implicit al temei
        
        # Actualizează datele graficului
        self.data_y.append(value)
        self.draw_graph()

    def on_canvas_resize(self, event):
        self.canvas_width = event.width
        self.draw_graph()

    def draw_graph(self):
        self.graph_canvas.delete("all")
        
        if not self.data_y:
            return

        # Scări
        max_dist = max(max(self.data_y), 50) * 1.2
        width = self.graph_canvas.winfo_width()
        height = self.graph_canvas.winfo_height()
        
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
            self.graph_canvas.create_line(coords, fill="#3B8ED0", width=2, smooth=True)

    def on_closing(self):
        self.disconnect()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
