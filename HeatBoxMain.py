import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import serial.tools.list_ports
import serial
import threading
from datetime import datetime
from datetime import timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs'))


class HeatBox:
    def __init__(self, root):
        self.root = root
        self.root.title("HeatBox GUI")
        self.root.geometry("1200x650")  # Set initial size

        # Initialize data variables and serial connection
        self.serial_connection = None
        self.is_reading = False
        self.time_data = []
        self.temp1_data = []
        self.temp2_data = []
        self.temp3_data = []
        self.temp4_data = []
        self.meanTemp_data = []
        self.power_data = []
        self.setPoint_data = []
        self.setPoint_data = []
        self.pid_values = []
        self.chosenSensor = []

        # Initialize instance attributes for frames
        self.left_frame = None
        self.middle_frame = None
        self.monitor_frame = None

        # Initialize instance attributes for sub frames and local elements
        # serial_frame
        self.serial_frame = None
        self.label = None
        self.selected_port = None
        self.port_dropdown = None
        self.refresh_button = None

        # experiment_frame
        self.experiment_frame = None
        self.confirm_button = None
        self.stop_button = None
        # self.reset_button = None
        self.finished_experiment = False

        # save_frame
        self.log_frame = None
        self.save_instruction_label = None
        self.save_button = None
        self.save_location_label = None
        self.save_path = ""
        self.comment_button = None
        self.save_comment = ""

        # setPoint_frame
        self.setPoint_frame = None
        self.setPoint_label = None
        self.setPoint_entry = None
        self.send_setPoint_button = None

        # pid_frame
        self.PID_frame = None
        self.PID_label = None
        self.sensor_value_label = None

        # plot_frame
        self.checkbox_frame = None
        self.fig = None
        self.ax1 = None
        self.ax2 = None
        self.line1_temp1 = None
        self.line1_temp2 = None
        self.line1_temp3 = None
        self.line1_temp4 = None
        self.line1_meanTemp = None
        self.line1_setPoint = None
        self.line2_power = None
        self.canvas = None
        self.canvas_widget = None
        self.show_temp1 = None
        self.show_temp2 = None
        self.show_temp3 = None
        self.show_temp4 = None
        self.show_meanTemp = None
        self.temp1_checkbox = None
        self.temp2_checkbox = None
        self.temp3_checkbox = None
        self.temp4_checkbox = None
        self.meanTemp_checkbox = None

        # monitor_frame
        self.monitor_label = None
        self.serial_monitor_text = None
        self.monitor_scrollbar = None

        # Create main frames: Left (controls), Middle (plot), Right (text monitor)
        self.create_frames()

        # Create UI sections in each frame
        self.create_serial_frame()  # in left frame
        self.create_experiment_frame()  # in left frame
        self.create_save_location_frame()  # in left frame
        self.create_setpoint_frame()  # in left frame
        self.create_pid_frame()  # in left frame
        self.create_plot()  # in middle frame
        self.create_monitor_frame()  # in right frame

        # Create a separate thread for reading serial data
        self.serial_thread = threading.Thread(target=self.read_serial_data)
        self.serial_thread.daemon = True
        self.serial_thread.start()

        # Start the plot update loop
        self.update_freq = 500  # milliseconds
        self.root.after(self.update_freq, self.update_plot)

        # Bind resize event to adjust font sizes and wraplengths
        self.root.bind("<Configure>", self.on_resize)

        # Initialize available ports
        self.refresh_ports()

    def create_frames(self):
        """Creates three main frames: left (controls), middle (plot), right (monitor)"""
        # Left Frame for Controls
        self.left_frame = tk.Frame(self.root)
        self.left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.left_frame.grid_columnconfigure(0, weight=1)  # Allow widgets inside to expand

        # Middle Frame for the Plot
        self.middle_frame = tk.Frame(self.root)
        self.middle_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        # Right Frame for the Text Monitor
        self.monitor_frame = tk.Frame(self.root)
        self.monitor_frame.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")

        # Frame proportions
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1, minsize=200)  # Left frame
        self.root.grid_columnconfigure(1, weight=2, minsize=400)  # Middle frame (gets more space for plots)
        self.root.grid_columnconfigure(2, weight=1, minsize=250)  # Right frame

        # Allow middle frame to expand dynamically
        self.middle_frame.grid_rowconfigure(1, weight=1)
        self.middle_frame.grid_columnconfigure(0, weight=1)

    def create_serial_frame(self):
        """Creates the Serial Port section in the left frame."""
        self.serial_frame = tk.Frame(self.left_frame)
        self.serial_frame.grid(row=0, column=0, pady=10, sticky="ew")
        self.serial_frame.grid_columnconfigure(0, weight=1)

        self.label = tk.Label(self.serial_frame, text="Select a Serial Port:")
        self.label.grid(row=0, column=0, pady=5, sticky="ew")

        self.selected_port = tk.StringVar()
        self.port_dropdown = ttk.Combobox(self.serial_frame, textvariable=self.selected_port, state="readonly")
        self.port_dropdown.grid(row=1, column=0, pady=5, sticky="ew")

        self.refresh_button = tk.Button(self.serial_frame, text="Refresh Ports", command=self.refresh_ports)
        self.refresh_button.grid(row=2, column=0, pady=5, sticky="ew")

    def create_experiment_frame(self):
        """Creates the experiment controls section in the left frame."""
        self.experiment_frame = tk.Frame(self.left_frame)
        self.experiment_frame.grid(row=1, column=0, pady=20, sticky="ew")
        self.experiment_frame.grid_columnconfigure(0, weight=1)

        self.confirm_button = tk.Button(self.experiment_frame, text="Start Experiment", command=self.start_reading)
        self.confirm_button.grid(row=0, column=0, pady=5, sticky="ew")

        self.stop_button = tk.Button(self.experiment_frame, text="Finish Experiment", command=self.finish_experiment)
        self.stop_button.grid(row=1, column=0, pady=5, sticky="ew")

        # self.reset_button = tk.Button(self.experiment_frame, text="Reset Data", command=self.reset_experiment)
        # self.reset_button.grid(row=2, column=0, pady=5, sticky="ew")

    def create_save_location_frame(self):
        """Creates the save location section in the left frame."""
        self.log_frame = tk.Frame(self.left_frame)
        self.log_frame.grid(row=2, column=0, pady=15, sticky="ew")
        self.log_frame.grid_columnconfigure(0, weight=1)

        # Instruction label above the button
        self.save_instruction_label = tk.Label(self.log_frame, text="Select location to save data:")
        self.save_instruction_label.grid(row=0, column=0, pady=1, sticky="ew")

        # Button to choose save location
        self.save_button = tk.Button(self.log_frame, text="Choose Save Location", command=self.choose_save_location)
        self.save_button.grid(row=1, column=0, pady=5, sticky="ew")

        # Label to display the chosen save location.
        self.save_location_label = tk.Label(self.log_frame, text="", anchor="w", justify="left", wraplength=250)
        self.save_location_label.grid(row=2, column=0, pady=5, sticky="w")

        # Button to add a comment to the Excel file
        self.comment_button = tk.Button(self.log_frame, text="Add comment to file", command=self.add_comment)
        self.comment_button.grid(row=3, column=0, pady=5, sticky="ew")

    def create_setpoint_frame(self):
        """Creates the Set Point temperature control section in the left frame."""
        self.setPoint_frame = tk.Frame(self.left_frame)
        self.setPoint_frame.grid(row=3, column=0, pady=10, sticky="ew")
        self.setPoint_frame.grid_columnconfigure(0, weight=1)

        self.setPoint_label = tk.Label(self.setPoint_frame, text="Set point temperature:")
        self.setPoint_label.grid(row=0, column=0, pady=5, sticky="ew")

        self.setPoint_entry = tk.Entry(self.setPoint_frame)
        self.setPoint_entry.grid(row=1, column=0, pady=5, sticky="ew")

        self.send_setPoint_button = tk.Button(self.setPoint_frame, text="Change set point",
                                              command=self.send_setpoint_command)
        self.send_setPoint_button.grid(row=2, column=0, pady=5, sticky="ew")

    def create_pid_frame(self):
        """Creates the PID information section in the left frame."""
        self.PID_frame = tk.Frame(self.left_frame)
        self.PID_frame.grid(row=4, column=0, pady=10, sticky="ew")
        self.PID_frame.grid_columnconfigure(0, weight=1)

        self.PID_label = tk.Label(self.PID_frame, text="PID reference sensor(s):")
        self.PID_label.grid(row=0, column=0, pady=5, sticky="w")
        self.sensor_value_label = tk.Label(self.PID_frame, text="...")
        self.sensor_value_label.grid(row=0, column=1, pady=5, sticky="e")

    def create_monitor_frame(self):
        """Creates the Monitor text widget in the right frame."""
        self.monitor_label = tk.Label(self.monitor_frame, text="Serial Monitor Output:")
        self.monitor_label.grid(row=0, column=0, pady=10, sticky="w")
        self.serial_monitor_text = tk.Text(self.monitor_frame, height=60, width=40, wrap=tk.WORD, state=tk.DISABLED)
        self.serial_monitor_text.grid(row=1, column=0, pady=0, padx=(0, 5))

        # Ensure the monitor frame expands properly
        self.monitor_frame.grid_rowconfigure(1, weight=1)
        self.monitor_frame.grid_columnconfigure(0, weight=1)

        self.monitor_scrollbar = tk.Scrollbar(self.monitor_frame, command=self.serial_monitor_text.yview)
        self.monitor_scrollbar.grid(row=1, column=1, sticky="ns")

        self.serial_monitor_text.config(yscrollcommand=self.monitor_scrollbar.set)

    def append_to_serial_monitor(self, message):
        """Append a message to the serial monitor text widget."""
        self.serial_monitor_text.config(state=tk.NORMAL)  # Enable editing temporarily
        self.serial_monitor_text.insert(tk.END, message + "\n")  # Insert new message
        self.serial_monitor_text.config(state=tk.DISABLED)  # Disable editing again
        self.serial_monitor_text.yview(tk.END)  # Scroll to the bottom

    def create_plot(self):
        """Sets up the Matplotlib plot in the middle frame."""
        self.checkbox_frame = tk.Frame(self.middle_frame)
        self.checkbox_frame.grid(row=0, column=0, pady=(10, 0), sticky="w")

        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, gridspec_kw={'height_ratios': [2, 1]})

        # Temperature Plot
        self.line1_temp1, = self.ax1.plot([], [], label="Temp 1")
        self.line1_temp2, = self.ax1.plot([], [], label="Temp 2")
        self.line1_temp3, = self.ax1.plot([], [], label="Temp 3")
        self.line1_temp4, = self.ax1.plot([], [], label="Temp 4")
        self.line1_meanTemp, = self.ax1.plot([], [], label="Mean Temp")
        self.line1_setPoint, = self.ax1.plot([], [], label="Setpoint")
        self.ax1.set_title("Temperature Readings", fontsize=12)
        self.ax1.set_ylabel("Temperature", fontsize=6)
        self.ax1.legend(fontsize=6)

        # Power Plot
        self.line2_power, = self.ax2.plot([], [], label="Power")
        self.ax2.set_title("Power Readings", fontsize=12)
        self.ax2.set_xlabel("Time (s)", fontsize=6)
        self.ax2.set_ylabel("Power", fontsize=6)
        self.ax2.legend(fontsize=6)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.middle_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=1, column=0, sticky="nsew")

        # Checkboxes for toggling data visibility
        self.show_temp1 = tk.BooleanVar(value=True)
        self.show_temp2 = tk.BooleanVar(value=True)
        self.show_temp3 = tk.BooleanVar(value=True)
        self.show_temp4 = tk.BooleanVar(value=True)
        self.show_meanTemp = tk.BooleanVar(value=True)

        self.temp1_checkbox = tk.Checkbutton(
            self.checkbox_frame, text="Temp 1",
            variable=self.show_temp1, command=self.toggle_temperature
        )
        self.temp1_checkbox.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.temp2_checkbox = tk.Checkbutton(
            self.checkbox_frame, text="Temp 2",
            variable=self.show_temp2, command=self.toggle_temperature
        )
        self.temp2_checkbox.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.temp3_checkbox = tk.Checkbutton(
            self.checkbox_frame, text="Temp 3",
            variable=self.show_temp3, command=self.toggle_temperature
        )
        self.temp3_checkbox.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        self.temp4_checkbox = tk.Checkbutton(
            self.checkbox_frame, text="Temp 4",
            variable=self.show_temp4, command=self.toggle_temperature
        )
        self.temp4_checkbox.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        self.meanTemp_checkbox = tk.Checkbutton(
            self.checkbox_frame, text="Mean Temp",
            variable=self.show_meanTemp, command=self.toggle_temperature
        )
        self.meanTemp_checkbox.grid(row=0, column=4, padx=5, pady=5, sticky="w")

    def refresh_ports(self):
        """Refresh the list of available serial ports."""
        ports = serial.tools.list_ports.comports()
        port_names = [port.device for port in ports]
        self.port_dropdown["values"] = port_names
        if port_names:
            self.port_dropdown.current(0)
        else:
            self.port_dropdown.set("")

    def start_reading(self):
        """Start reading data from the selected serial port."""
        selected = self.selected_port.get()
        if selected:
            try:
                self.serial_connection = serial.Serial(selected, 115200, timeout=1)
                self.is_reading = True
                self.append_to_serial_monitor(f"Reading from: {selected}\n")
                self.read_serial_data()
            except serial.SerialException as e:
                self.append_to_serial_monitor(f"Error: {e}")
        else:
            self.append_to_serial_monitor("No port selected!")

    def send_setpoint_command(self):
        """Send a set point command to Arduino."""
        try:
            setPoint_value = float(self.setPoint_entry.get())
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.write(f"setpoint: {setPoint_value}\n".encode())
                self.append_to_serial_monitor(f"Sent set point value: {setPoint_value}")
            else:
                self.append_to_serial_monitor("Error: No active serial connection.")
        except ValueError:
            self.append_to_serial_monitor("Invalid set point value. Please enter a correct number.")

    def finish_experiment(self):
        """Finish the experiment and log data if needed."""
        if self.save_path:
            self.is_reading = False
            self.log_data_to_excel()
            self.clear_data()
        else:
            res = messagebox.askyesno("Info", "You have not chosen a save location, do you want to save the data?")
            if not res:
                self.is_reading = False
                self.append_to_serial_monitor("Finished experiment without saving data.")
                print("Finished experiment without saving data.")
                self.clear_data()
                self.finished_experiment = True
            else:
                messagebox.showinfo("Info", "Please choose a saving location for the data.")

    def process_data(self, data_string):
        """Process incoming serial data."""
        sensorVals = data_string.split('\t')
        if sensorVals[0] == 'pid values:':
            self.pid_values.append(float(sensorVals[1]))
            self.pid_values.append(float(sensorVals[2]))
            self.pid_values.append(float(sensorVals[3]))
            print(f'PID values: Kp = {sensorVals[1]}, Ki: {sensorVals[2]}, Kd: {sensorVals[3]}')
            return False
        if sensorVals[0] == 'DHT22 Heat Dim Test: Temperature setpoint at':
            chosenSensorValue = int(sensorVals[4])
            self.chosenSensor.append(chosenSensorValue)
            print(f'Initial Set Point Temperature = {sensorVals[1]}')
            if chosenSensorValue >= 1 & chosenSensorValue <= 4:
                self.sensor_value_label.config(text=str(self.chosenSensor))
                print(f'PID reference sensor(s) = {chosenSensorValue}')
            elif chosenSensorValue == 5:
                self.sensor_value_label.config(text="Mean")
                print('PID reference sensor(s) = Mean of all')
            else:
                self.sensor_value_label.config(text="error")
                print('No appropriate PID reference sensor, check Arduino Code')
            return False
        if sensorVals[0] == 'Dim Power:':
            self.time_data.append((float(sensorVals[11])) / 1000)  # ms to s
            self.temp1_data.append(float(sensorVals[3]))
            self.temp2_data.append(float(sensorVals[5]))
            self.temp3_data.append(float(sensorVals[7]))
            self.temp4_data.append(float(sensorVals[9]))
            self.meanTemp_data.append(float(sensorVals[16]))
            self.power_data.append(float(sensorVals[1]))
            self.setPoint_data.append(float(sensorVals[12]))
            hhmmss = timedelta(seconds=int((float(sensorVals[11])) / 1000))
            print(
                f'Time: {hhmmss}, Temp 1: {sensorVals[3]}, Temp 2: {sensorVals[5]}, Temp 3: {sensorVals[7]}, Temp 4: {sensorVals[9]}, Mean Temp: {sensorVals[16]}, Power: {sensorVals[1]}, setpoint: {sensorVals[12]}')
            return True
        return False

    def read_serial_data(self):
        """Reads data from the serial connection"""
        if self.is_reading and self.serial_connection.in_waiting > 0:
            try:
                raw_data = self.serial_connection.readline().decode('utf-8').strip()
                self.process_data(raw_data)
            except ValueError:
                pass

        if self.is_reading:
            self.root.after(self.update_freq, self.read_serial_data)

    def toggle_temperature(self):
        """Toggle visibility of temperature data."""
        self.update_plot()

    def update_plot(self):
        """Update the plot with new data."""
        # List to store active lines and labels for the legend
        active_lines = []
        active_labels = []
        width, height = self.fig.get_size_inches()
        font_size = max(8, min(width, height) // 100)

        # Check and update each temperature line
        if self.setPoint_data and self.time_data:
            self.line1_setPoint.set_data(self.time_data, self.setPoint_data)
            active_lines.append(self.line1_setPoint)
            active_labels.append("Setpoint")

        if self.temp1_data and self.time_data:
            if self.show_temp1.get():
                self.line1_temp1.set_data(self.time_data, self.temp1_data)
                active_lines.append(self.line1_temp1)
                active_labels.append("Temp 1")
            else:
                self.line1_temp1.set_data([], [])

        if self.temp2_data and self.time_data:
            if self.show_temp2.get():
                self.line1_temp2.set_data(self.time_data, self.temp2_data)
                active_lines.append(self.line1_temp2)
                active_labels.append("Temp 2")
            else:
                self.line1_temp2.set_data([], [])

        if self.temp3_data and self.time_data:
            if self.show_temp3.get():
                self.line1_temp3.set_data(self.time_data, self.temp3_data)
                active_lines.append(self.line1_temp3)
                active_labels.append("Temp 3")
            else:
                self.line1_temp3.set_data([], [])

        if self.temp4_data and self.time_data:
            if self.show_temp4.get():
                self.line1_temp4.set_data(self.time_data, self.temp4_data)
                active_lines.append(self.line1_temp4)
                active_labels.append("Temp 4")
            else:
                self.line1_temp4.set_data([], [])

        if self.meanTemp_data and self.time_data:
            if self.show_meanTemp.get():
                self.line1_meanTemp.set_data(self.time_data, self.meanTemp_data)
                active_lines.append(self.line1_meanTemp)
                active_labels.append("Mean Temp")
            else:
                self.line1_meanTemp.set_data([], [])

        self.ax1.legend(active_lines, active_labels, fontsize=font_size - 4)
        self.ax1.relim()
        self.ax1.autoscale_view()

        if self.power_data and self.time_data:
            self.line2_power.set_data(self.time_data, self.power_data)
            self.ax2.relim()
            self.ax2.autoscale_view()

        self.canvas.draw_idle()
        self.root.after(self.update_freq, self.update_plot)

    def clear_data(self):
        """Clears stored data."""
        self.time_data.clear()
        self.temp1_data.clear()
        self.temp2_data.clear()
        self.temp3_data.clear()
        self.temp4_data.clear()
        self.meanTemp_data.clear()
        self.power_data.clear()
        self.setPoint_data.clear()
        self.setPoint_data.clear()
        self.pid_values.clear()
        self.chosenSensor.clear()

    def reset_experiment(self):
        """Resets experiment data and GUI"""
        res = messagebox.askyesno("Info", "Are you sure you want to clear the data?")
        #   if res:
        #  self.clear_data()
        #    self.update_plot()

    def add_comment(self):
        """Opens a dialog to enter a comment and stores it."""
        self.save_comment = simpledialog.askstring("Add Comment", "Enter your comment:")
        if self.save_comment:
            messagebox.showinfo("Comment Saved", "Your comment has been added!")
            self.append_to_serial_monitor(f"Comment added: \n {self.save_comment}")

    def choose_save_location(self):
        """Prompt the user to choose a file save location."""
        self.save_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")]
        )
        if self.save_path:
            self.append_to_serial_monitor(f"Save Location: {self.save_path}")
            self.save_location_label.config(text=f"Save Location: {self.save_path}")

    def log_data_to_excel(self):
        """Log the collected data to an Excel file."""
        now = datetime.now()
        d = now.strftime("%d/%m/%y")
        t = now.strftime("%H:%M")
        df = pd.DataFrame({'Time (s)': self.time_data,
                           'Temperature 1 (dht22)': self.temp1_data,
                           'Temperature 2 (dht22)': self.temp2_data,
                           'Temperature 3 (dht22)': self.temp3_data,
                           'Temperature 4 (dht22)': self.temp4_data,
                           'Mean Temperature': self.meanTemp_data,
                           'Set point': self.setPoint_data,
                           'Lamp Power (0-255)': self.power_data})
        df_pid = pd.DataFrame({'Kp': [self.pid_values[0]],
                               'Ki': [self.pid_values[1]],
                               'Kd': [self.pid_values[2]]})
        df_other = pd.DataFrame({'Date': [d],
                                 'Time': [t],
                                'Comment': [self.save_comment]})
        with pd.ExcelWriter(self.save_path) as excel_writer:
            df.to_excel(excel_writer, sheet_name='Sheet1', float_format="%.2f", index=False)
            df_pid.to_excel(excel_writer, sheet_name='Sheet1', float_format="%.2f", index=False, startcol=9)
            df_other.to_excel(excel_writer, sheet_name='Sheet1', float_format="%.2f", index=False, startcol=12)
        self.append_to_serial_monitor(f"Experiment finished. Data logged to: {self.save_path}\n")
        print(f"Experiment finished. Data logged to: {self.save_path}")
        self.finished_experiment = True

    def on_resize(self, event):
        """Handle window resize event and adjust layout fonts and wrap lengths."""
        width, height = event.width, event.height
        font_size = max(8, min(width, height) // 100)

        self.ax1.set_title("Temperature Readings", fontsize=font_size - 2)
        self.ax1.set_ylabel("Temperature", fontsize=font_size - 3)
        self.ax1.legend(fontsize=font_size - 4)

        self.ax2.set_title("Power Readings", fontsize=font_size - 2)
        self.ax2.set_xlabel("Time (s)", fontsize=font_size - 3)
        self.ax2.set_ylabel("Power", fontsize=font_size - 3)
        self.ax2.legend(fontsize=font_size - 4)

        self.ax1.tick_params(axis="x", labelsize=font_size - 3)
        self.ax1.tick_params(axis="y", labelsize=font_size - 3)
        self.ax2.tick_params(axis="x", labelsize=font_size - 3)
        self.ax2.tick_params(axis="y", labelsize=font_size - 3)

        self.fig.tight_layout()
        self.canvas.draw_idle()

        # Update the wraplength for the save location label so that it matches to the frame width.
        if self.log_frame is not None and self.save_location_label is not None:
            new_wraplength = self.log_frame.winfo_width() - 10
            self.save_location_label.config(wraplength=new_wraplength)

    def on_close(self):
        """Handles window close event."""
        if messagebox.askyesno("Exit", "Are you sure you want to exit? Data will be cleared."):
            self.clear_data()
            root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = HeatBox(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
