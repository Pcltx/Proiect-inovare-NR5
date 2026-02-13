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
        self.geometry("900x600")

        # Configurare aspect
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Cadru bară laterală
        self.sidebar_frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="Sensor", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Controale conexiune
        self.com_port_var = customtkinter.StringVar(value="Selecteaza portul")
        self.port_menu = customtkinter.CTkOptionMenu(self.sidebar_frame, variable=self.com_port_var, values=self.get_available_ports())
        self.port_menu.grid(row=1, column=0, padx=20, pady=10)

        self.refresh_btn = customtkinter.CTkButton(self.sidebar_frame, text="Refresh", command=self.refresh_ports)
        self.refresh_btn.grid(row=2, column=0, padx=20, pady=10)

        self.connect_btn = customtkinter.CTkButton(self.sidebar_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=3, column=0, padx=20, pady=10)
        
        self.connect_info = customtkinter.CTkLabel(self.sidebar_frame, text="Status: Disconnected", text_color="gray")
        self.connect_info.grid(row=4, column=0, padx=20, pady=10, sticky="s")

        # Control prag
        self.threshold_label = customtkinter.CTkLabel(self.sidebar_frame, text=f"Threshold: {self.alert_threshold} cm")
        self.threshold_label.grid(row=5, column=0, padx=20, pady=(20, 0))
        
        self.threshold_slider = customtkinter.CTkSlider(self.sidebar_frame, from_=0, to=100, number_of_steps=100, command=self.update_threshold)
        self.threshold_slider.set(self.alert_threshold)
        self.threshold_slider.grid(row=6, column=0, padx=20, pady=(0, 20))

        # Zona principală de conținut
        self.main_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)

        # Afișare distanță
        self.value_frame = customtkinter.CTkFrame(self.main_frame, fg_color="transparent")
        self.value_frame.grid(row=0, column=0, pady=(20, 0))
        
        self.distance_label = customtkinter.CTkLabel(self.value_frame, text="-- cm", font=customtkinter.CTkFont(size=80, weight="bold"))
        self.distance_label.pack()


        # Grafic Canvas
        self.graph_height = 300
        self.graph_canvas = tkinter.Canvas(self.main_frame, height=self.graph_height, bg="#2b2b2b", highlightthickness=0)
        self.graph_canvas.grid(row=2, column=0, padx=20, pady=20, sticky="nsew")
        
        # Leagă evenimentul de redimensionare pentru a redesena graficul
        self.graph_canvas.bind("<Configure>", self.on_canvas_resize)

        # Date
        self.data_len = 100
        self.data_y = collections.deque([0] * self.data_len, maxlen=self.data_len)
        self.canvas_width = 100 # Substituent inițial

        # Variabile seriale
        self.serial_conn = None
        self.is_running = False
        self.thread = None
        
        # Stare alertă audio
        self.last_beep_time = 0
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
        if port == "Select Port" or port == "No Ports":
            return

        try:
            self.serial_conn = serial.Serial(port, 9600, timeout=1)
            self.is_running = True
            self.connect_btn.configure(text="Disconnect", fg_color="red", hover_color="darkred")
            self.connect_info.configure(text="Status: Connected", text_color="green")
            
            # Pornește firul de execuție pentru citire
            self.thread = threading.Thread(target=self.read_serial_data, daemon=True)
            self.thread.start()
        except Exception as e:
            self.connect_info.configure(text=f"Error: {e}", text_color="red")
            print(e)

    def disconnect(self):
        self.is_running = False
        if self.serial_conn:
            self.serial_conn.close()
        self.connect_btn.configure(text="Connect", fg_color="#1f538d", hover_color="#14375e") # restabilește albastrul implicit
        self.connect_info.configure(text="Status: Disconnected", text_color="gray")

    def update_threshold(self, value):
        self.alert_threshold = int(value)
        self.threshold_label.configure(text=f"Threshold: {self.alert_threshold} cm")

    def read_serial_data(self):
        while self.is_running and self.serial_conn and self.serial_conn.is_open:
            try:
                line = self.serial_conn.readline().decode('utf-8').strip()
                if line:
                    try:
                        val = float(line)
                        self.check_alert(val)
                        self.update_ui(val)
                    except ValueError:
                        pass 

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
