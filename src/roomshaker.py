###############################################################################
#   Copyright (c) 2025, Nick Blanchard
#
#   This software is distributed under the MIT license and may be used and
#   modified without restrictions.
#
#   File:               roomshaker.py
#   Author:             Nick Blanchard
#   Contact:            nnblanchardaz@gmail.com
#   Date:               6/15/2025
#   Revision:           -
#   Description:        This file hold source code for the ROOM SHAKER GUI
#                       application.
#   Application Notes:  
#   Known Bugs:
#   TODO:
###############################################################################


###############################################################################
## DEPENDENCIES
###############################################################################


import tkinter as tk
from tkinter import *
from tkinter import filedialog
from tkinter import ttk
from PIL import ImageTk, Image
import serial
import serial.tools.list_ports
import struct
import os
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from scipy import signal
import numpy as np
import math
import time
import threading
import csv


###############################################################################
## AUXILIARY CLASSES AND FUNCTIONS
###############################################################################


# Function to create widgets with all options
def create_widget(parent, widget_type, **options):
    return widget_type(parent, **options)


# Class to load filter parameters from external files
class floader:

    def store_fields(self, fields):
        self.fields = fields

    def set_fields(self, vals):
        for i in range(len(vals)):
            if i < len(self.fields):
                self.fields[i].delete(0, tk.END)
                self.fields[i].insert(0, vals[i])
            else:
                print("ERROR at " + str(vals[i]))

    # Function for opening the file explorer window to select BEQ file
    def browse_files(self, is_txt):

        # Open file explorer
        filename = filedialog.askopenfilename(initialdir = "/", title = "Select a File", filetypes = (("Text files", "*.txt*"), ("all files", "*.*")))
        
        # Load biquad filter parameters from file
        data_list = []
        with open(filename, 'r', newline='') as f:
            csv_reader = csv.reader(f)
            for row in csv_reader:
                for word in row:
                    data_list.append(word)
        # print(data_list)
        self.set_fields(data_list)


# Class to interact with the serial port
class sport:

    ser = NONE

    # Function to enumerate available COM ports
    def open_com_port(self, cbox):
        ports = serial.tools.list_ports.comports()
        vals = []
        for port, desc, hwid in sorted(ports):
            # print(f"{port}: {desc} [{hwid}]")
            vals.append(port)
        cbox['values'] = vals

    # Function to open a specific COM port
    def bind(self, event, portname, buttons):
        if portname != "Select COM Port..." and portname != '':
            try:
                self.ser = serial.Serial(portname, 9600)
            except Exception as e:
                print(f"An error occurred: {e}")
            
            for button in buttons:
                button["state"] = "active"

    # Function to upload filter parameters over COM port
    def upload_filters(self, values):
        
        # Convert data to bytes
        raw = bytearray()
        for val in values:
            raw.extend(struct.pack('f', val))

        # Split data into two USB packets
        # The maximum FS USB packet size is 64 bytes. We need to
        # send 4 * 4 * 5 = 80 bytes. By pre-emptively
        # splitting the data into two packets, we can control
        # when/where the data is split and insert our own
        # headers.

        # BYTE 0: NUMBER OF FILTERS PARAMETERs IN THIS PACKET
        # BYTE 1: STARTING FILTER INDEX
        # BYTES 2 to n: FILTER PARAMETERS

        # Filter parameters are stored in an array of size 20.
        # {b0 b1 b2 a0 a1}, maximum of 4 stages
        # ...

        # First packet transmission
        first_msg = bytearray()
        first_msg.extend(b'\x0A')       # 10 parameters in first message (2 filters)
        first_msg.extend(b'\x00')       # Start at the 0th index   
        first_msg.extend(raw[0:39])
        self.ser.write(first_msg)

        # Second packet transmission
        second_msg = bytearray()
        second_msg.extend(b'\x0A')      # 10 parameters in second message (2 filters)
        second_msg.extend(b'\x28')      # Start at the 40th index   
        second_msg.extend(raw[40:79])
        self.ser.write(second_msg)

    def enable_autoeq(self):
        
        # Send all 1s to indicate auto EQ mode is enabled
        raw = bytearray()
        for i in range(100):
            raw.extend((255).to_bytes(1, byteorder='big'))
        self.ser.write(raw)

    def receive_response(self, widget):

        # Check if data has been received
        if isinstance(self.ser, serial.Serial):
            if self.ser.in_waiting > 0:
                data = str(self.ser.read(self.ser.in_waiting)) + "\n"
                widget.insert(tk.END, data)

        window.after(100, lambda:_sport.receive_response(widget))


# Class to represent bode plot
class plot:

    def __init__(self, fs):
        self.fs = fs

    def create(self, parent, toolbar_true, fields):

        # Figure
        self.fig, self.ax = plt.subplots(figsize=(4, 2), dpi=100)

        # Place in tkinter window
        self.canvas = FigureCanvasTkAgg(self.fig, master = parent)  
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=7, rowspan=7)

        # Optional: Add toolbar
        if (toolbar_true):
            self.toolbar = NavigationToolbar2Tk(self.canvas, parent)
            self.toolbar.update()
            self.toolbar.grid(row=7, column=7, rowspan=1)

        # Save data fields
        self.data_fields = fields

        # Update plot
        self.update()

    def update(self):

        # Get biquad parameters
        try:
            values = get_values(self.data_fields)
        except:
            return

        # Create 4 biquads
        try:
            W1, H1 = signal.freqz(b=values[0:3], a=([1.0] + values[3:5]), worN=int(self.fs/2), fs=self.fs)
            W2, H2 = signal.freqz(b=values[5:8], a=([1.0] + values[8:10]), worN=int(self.fs/2), fs=self.fs)
            W3, H3 = signal.freqz(b=values[10:13], a=([1.0] + values[13:15]), worN=int(self.fs/2), fs=self.fs)
            W4, H4 = signal.freqz(b=values[15:18], a=([1.0] + values[18:20]), worN=int(self.fs/2), fs=self.fs)
        except Exception as e:
            print("ERROR: Are all 20 coefficients being passed to the plot.update() function? " + e)
            W1, H1 = 0, 0
            W2, H2 = 0, 0
            W3, H3 = 0, 0
            W4, H4 = 0, 0

        # Cascade all 4 biquads
        H = H1 * H2 * H3 * H4                             # Multiply frequency responses
        magnitude_db = 20 * np.log10(abs(H))                # Extract gain in dB
        # phase_degrees = np.angle(H, deg=True)             # Extract phase in degrees
        freq_degrees = W2

        # Clear previously plotted curve
        self.ax.clear()

        # Create bode plots
        self.ax.semilogx(freq_degrees[0:400], magnitude_db[0:400])
        self.ax.set_title("Frequency Response")
        self.ax.set_xlabel("Frequency (Hz)")
        self.ax.set_ylabel("Gain (dB)")
        self.ax.xaxis.set_major_locator(mticker.LogLocator(base=10.0, numticks=5))
        self.ax.locator_params(axis='y', nbins=6)
        plt.tight_layout()
        self.canvas.draw()

def plot_loop():
    while 1:
        _plot.update()

def get_values(fields):
    values = []
    for field in fields:
        values.append(float(field.get()))
    return values

def hz_to_rads(hz):
    return (hz * math.pi / 180)

def rads_to_hz(rads):
    return (rads * 180 / math.pi)

    

###############################################################################
## GLOBAL VARIABLES
###############################################################################


# MAIN WINDOW
window = tk.Tk()

# Serial port
_sport = sport()

# Bode plot
_plot = plot(fs=48000)  # Sampling frequency = 48kHz

# File loader
_floader = floader()


###############################################################################
## MAIN FUNCTION
###############################################################################


def main():

    ## MAIN WINDOW
    window.minsize(950, 650)
    # window.maxsize(1000, 650)
    window.title("ROOM SHAKER")
    icon = PhotoImage(file = os.path.join(os.path.dirname(__file__), "imgs\\icon.png"))
    window.iconphoto(False, icon)
    window.update()

    ## FIRST ROW
    first_row = create_widget(window, tk.Frame, height=2*window.winfo_height()/20, width=window.winfo_width())
    first_row.grid(row=0, column=0)
    first_row.columnconfigure(0, weight=1)
    first_row.columnconfigure(1, weight=1)
    first_row.columnconfigure(2, weight=1)
    first_row.grid_propagate(False)
    first_row.update()

    # Logo
    bg = Image.open(os.path.join(os.path.dirname(__file__), "imgs\\room_shaker_transparent.png"))
    resize_factor = 1.0 * min(first_row.winfo_width()/bg.width, first_row.winfo_height()/bg.height)
    img = bg.resize((int(bg.width * resize_factor), int(bg.height * resize_factor)), Image.Resampling.LANCZOS)
    tk_bg = ImageTk.PhotoImage(img)
    image_label = create_widget(first_row, tk.Label, image=tk_bg)
    image_label.grid(row=0, column=1)

    ## SECOND ROW
    second_row = create_widget(window, tk.Frame, height=2*window.winfo_height()/20, width=window.winfo_width())
    second_row.grid(row=1, column=0)
    second_row.columnconfigure(0, weight=1)
    second_row.columnconfigure(1, weight=1)
    second_row.columnconfigure(2, weight=1)
    second_row.grid_propagate(False)
    second_row.update()
    chart = Image.open(os.path.join(os.path.dirname(__file__), "imgs\\flow.png"))
    chart_resize_factor = 0.9 * min((second_row.winfo_width()*.75)/chart.width, second_row.winfo_height()/chart.height)
    chart_img = chart.resize((int(chart.width * chart_resize_factor), int(chart.height * chart_resize_factor)), Image.Resampling.LANCZOS)
    chart_bg = ImageTk.PhotoImage(chart_img)
    chart_label = create_widget(second_row, tk.Label, image=chart_bg)
    chart_label.grid(row=0, column=1)

    ## THIRD ROW
    third_row = create_widget(window, tk.Frame, height=2*window.winfo_height()/5, width=window.winfo_width())
    third_row.grid(row=2, column=0)
    third_row.columnconfigure(0, weight=10)
    third_row.columnconfigure(1, weight=1)
    third_row.columnconfigure(2, weight=1)
    third_row.columnconfigure(3, weight=1)
    third_row.columnconfigure(4, weight=1)
    third_row.columnconfigure(5, weight=1)
    third_row.columnconfigure(6, weight=1)
    third_row.columnconfigure(7, weight=1)
    third_row.columnconfigure(8, weight=10)
    third_row.rowconfigure(0, weight=1)
    # third_row.rowconfigure(1, weight=1)
    # third_row.rowconfigure(3, weight=1)
    # third_row.rowconfigure(4, weight=1)
    # third_row.rowconfigure(5, weight=1)
    third_row.rowconfigure(6, weight=1)
    third_row.grid_propagate(False)
    third_row.update()

    # Biquad expression
    bqd = Image.open(os.path.join(os.path.dirname(__file__), "imgs\\biquad_transparent.png"))
    bqd_resize_factor = 1.0 * min((second_row.winfo_width()*.25)/bqd.width, (second_row.winfo_height()*.75)/bqd.height)
    bqd_img = bqd.resize((int(bqd.width * bqd_resize_factor), int(bqd.height * bqd_resize_factor)), Image.Resampling.LANCZOS)
    bqd_bg = ImageTk.PhotoImage(bqd_img)
    bqd_label = create_widget(third_row, tk.Label, image=bqd_bg)
    bqd_label.grid(row=0, column=1, columnspan=4)

    # Labels
    b0_label = create_widget(third_row, tk.Label, text="b0", font=("Helvetica", 12, "bold"))
    b0_label.grid(row=1, column=1)
    b1_label = create_widget(third_row, tk.Label, text="b1", font=("Helvetica", 12, "bold"))
    b1_label.grid(row=1, column=2)
    b2_label = create_widget(third_row, tk.Label, text="b2", font=("Helvetica", 12, "bold"))
    b2_label.grid(row=1, column=3)
    a1_label = create_widget(third_row, tk.Label, text="a1", font=("Helvetica", 12, "bold"))
    a1_label.grid(row=1, column=4)
    a2_label = create_widget(third_row, tk.Label, text="a2", font=("Helvetica", 12, "bold"))
    a2_label.grid(row=1, column=5)

    # Filter 1
    f1_label = create_widget(third_row, tk.Label, text="Biquad 1", font=("Helvetica", 12, "bold"))
    f1_label.grid(row=2, column=0)
    f1_b0_entry = create_widget(third_row, tk.Entry, width=10)
    f1_b0_entry.grid(row=2, column=1)
    f1_b1_entry = create_widget(third_row, tk.Entry, width=10)
    f1_b1_entry.grid(row=2, column=2)
    f1_b2_entry = create_widget(third_row, tk.Entry, width=10)
    f1_b2_entry.grid(row=2, column=3)
    f1_a1_entry = create_widget(third_row, tk.Entry, width=10)
    f1_a1_entry.grid(row=2, column=4)
    f1_a2_entry = create_widget(third_row, tk.Entry, width=10)
    f1_a2_entry.grid(row=2, column=5)

    # Filter 2
    f2_label = create_widget(third_row, tk.Label, text="Biquad 2", font=("Helvetica", 12, "bold"))
    f2_label.grid(row=3, column=0)
    f2_b0_entry = create_widget(third_row, tk.Entry, width=10)
    f2_b0_entry.grid(row=3, column=1)
    f2_b1_entry = create_widget(third_row, tk.Entry, width=10)
    f2_b1_entry.grid(row=3, column=2)
    f2_b2_entry = create_widget(third_row, tk.Entry, width=10)
    f2_b2_entry.grid(row=3, column=3)
    f2_a1_entry = create_widget(third_row, tk.Entry, width=10)
    f2_a1_entry.grid(row=3, column=4)
    f2_a2_entry = create_widget(third_row, tk.Entry, width=10)
    f2_a2_entry.grid(row=3, column=5)

    # Filter 3
    f3_label = create_widget(third_row, tk.Label, text="Biquad 3", font=("Helvetica", 12, "bold"))
    f3_label.grid(row=4, column=0)
    f3_b0_entry = create_widget(third_row, tk.Entry, width=10)
    f3_b0_entry.grid(row=4, column=1)
    f3_b1_entry = create_widget(third_row, tk.Entry, width=10)
    f3_b1_entry.grid(row=4, column=2)
    f3_b2_entry = create_widget(third_row, tk.Entry, width=10)
    f3_b2_entry.grid(row=4, column=3)
    f3_a1_entry = create_widget(third_row, tk.Entry, width=10)
    f3_a1_entry.grid(row=4, column=4)
    f3_a2_entry = create_widget(third_row, tk.Entry, width=10)
    f3_a2_entry.grid(row=4, column=5)

    # Filter 4
    f4_label = create_widget(third_row, tk.Label, text="Biquad 4", font=("Helvetica", 12, "bold"))
    f4_label.grid(row=5, column=0)
    f4_b0_entry = create_widget(third_row, tk.Entry, width=10)
    f4_b0_entry.grid(row=5, column=1)
    f4_b1_entry = create_widget(third_row, tk.Entry, width=10)
    f4_b1_entry.grid(row=5, column=2)
    f4_b2_entry = create_widget(third_row, tk.Entry, width=10)
    f4_b2_entry.grid(row=5, column=3)
    f4_a1_entry = create_widget(third_row, tk.Entry, width=10)
    f4_a1_entry.grid(row=5, column=4)
    f4_a2_entry = create_widget(third_row, tk.Entry, width=10)
    f4_a2_entry.grid(row=5, column=5)

    # Default filter values
    f1_b0_entry.insert(0, "1.0000000")
    f1_b1_entry.insert(0, "0.0000000")
    f1_b2_entry.insert(0, "0.0000000")
    f1_a1_entry.insert(0, "0.0000000")
    f1_a2_entry.insert(0, "0.0000000")
    # f1_b0_entry.insert(0, "0.00001067424")
    # f1_b1_entry.insert(0, "0.00002134847")
    # f1_b2_entry.insert(0, "0.00001067424")
    # f1_a1_entry.insert(0, "-1.99343371333")
    # f1_a2_entry.insert(0, "0.99347641028")
    f2_b0_entry.insert(0, "1.0000000")
    f2_b1_entry.insert(0, "0.0000000")
    f2_b2_entry.insert(0, "0.0000000")
    f2_a1_entry.insert(0, "0.0000000")
    f2_a2_entry.insert(0, "0.0000000")
    f3_b0_entry.insert(0, "1.0000000")
    f3_b1_entry.insert(0, "0.0000000")
    f3_b2_entry.insert(0, "0.0000000")
    f3_a1_entry.insert(0, "0.0000000")
    f3_a2_entry.insert(0, "0.0000000")
    f4_b0_entry.insert(0, "1.0000000")
    f4_b1_entry.insert(0, "0.0000000")
    f4_b2_entry.insert(0, "0.0000000")
    f4_a1_entry.insert(0, "0.0000000")
    f4_a2_entry.insert(0, "0.0000000")

    # Create frequency response plot
    _plot.create(parent=third_row, toolbar_true=False, fields=[f1_b0_entry, f1_b1_entry, f1_b2_entry, f1_a1_entry, f1_a2_entry, f2_b0_entry, f2_b1_entry, f2_b2_entry, f2_a1_entry, f2_a2_entry, f3_b0_entry, f3_b1_entry, f3_b2_entry, f3_a1_entry, f3_a2_entry, f4_b0_entry, f4_b1_entry, f4_b2_entry, f4_a1_entry, f4_a2_entry])

    ## FOURTH ROW
    fourth_row = create_widget(window, tk.Frame, height=window.winfo_height()/10, width=window.winfo_width())
    fourth_row.grid(row=3, column=0)
    fourth_row.grid_propagate(False)
    fourth_row.columnconfigure(0, weight=1)
    fourth_row.columnconfigure(1, weight=1)
    fourth_row.columnconfigure(2, weight=1)
    fourth_row.columnconfigure(3, weight=1)
    fourth_row.rowconfigure(0, weight=1)
    fourth_row.rowconfigure(1, weight=1)
    fourth_row.rowconfigure(2, weight=1)

    # Upload TXT
    txt = create_widget(fourth_row, tk.Button, text="Load biquad filters from .txt file...", command=lambda:_floader.browse_files(is_txt=True), font=("Helvetica", 12, "bold"))
    txt.grid(row=1, column=1)
    
    # Upload BEQ
    beq = create_widget(fourth_row, tk.Button, text="Load biquad filters from BEQDesigner file...", command=lambda:_floader.browse_files(is_txt=False), font=("Helvetica", 12, "bold"))
    beq.grid(row=1, column=2)
    beq["state"] = "disabled" # Disable this button until it is fully implemented
    

    ## FIFTH ROW
    fifth_row = create_widget(window, tk.Frame, height=window.winfo_height()/10, width=window.winfo_width())
    fifth_row.grid(row=4, column=0)
    fifth_row.grid_propagate(False)
    fifth_row.columnconfigure(0, weight=1)
    fifth_row.columnconfigure(1, weight=1)
    fifth_row.columnconfigure(2, weight=1)
    fifth_row.columnconfigure(3, weight=1)
    fifth_row.columnconfigure(4, weight=1)
    fifth_row.rowconfigure(0, weight=1)
    fifth_row.rowconfigure(1, weight=1)
    fifth_row.rowconfigure(2, weight=1)
    fifth_row.grid_propagate(False)
    fifth_row.update()

    # Upload Filters
    upload = create_widget(fifth_row, tk.Button, text="Upload Filters", command=lambda:_sport.upload_filters([float(f1_b0_entry.get()), float(f1_b1_entry.get()), float(f1_b2_entry.get()), float(f1_a1_entry.get()), float(f1_a2_entry.get()), float(f2_b0_entry.get()), float(f2_b1_entry.get()), float(f2_b2_entry.get()), float(f2_a1_entry.get()), float(f2_a2_entry.get()), float(f3_b0_entry.get()), float(f3_b1_entry.get()), float(f3_b2_entry.get()), float(f3_a1_entry.get()), float(f3_a2_entry.get()), float(f4_b0_entry.get()), float(f4_b1_entry.get()), float(f4_b2_entry.get()), float(f4_a1_entry.get()), float(f4_a2_entry.get())]), font=("Helvetica", 12, "bold"))
    upload["state"] = "disabled"
    upload.grid(row=1, column=2)

    # Enable Auto EQ
    autoeq = create_widget(fifth_row, tk.Button, text="Enable Auto EQ", command=_sport.enable_autoeq, font=("Helvetica", 12, "bold"))
    autoeq["state"] = "disabled"
    autoeq.grid(row=1, column=3)

    # Select COM Port
    port = tk.StringVar()
    com = create_widget(fifth_row, ttk.Combobox, textvariable=port, postcommand=lambda:_sport.open_com_port(com), font=("Helvetica", 12, "bold"))
    com.set('Select COM Port...')
    com.bind("<<ComboboxSelected>>", lambda event: _sport.bind(event, port.get(), [upload, autoeq]))
    com.grid(row=1, column=1)

    ## SIXTH ROW
    sixth_row = create_widget(window, tk.Frame, height=window.winfo_height()/5, width=window.winfo_width())
    sixth_row.grid(row=5, column=0)
    sixth_row.columnconfigure(0, weight=1)
    sixth_row.columnconfigure(1, weight=1)
    sixth_row.columnconfigure(2, weight=1)
    sixth_row.rowconfigure(0, weight=1)
    sixth_row.rowconfigure(1, weight=1)
    sixth_row.rowconfigure(2, weight=1)
    sixth_row.grid_propagate(False)
    sixth_row.update()

    # Text box
    output = create_widget(sixth_row, tk.Text, height=6, width=100)
    output.grid(row=1, column=1)

    # Store entry fields for file loader
    _floader.store_fields(fields=[f1_b0_entry, f1_b1_entry, f1_b2_entry, f1_a1_entry, f1_a2_entry, f2_b0_entry, f2_b1_entry, f2_b2_entry, f2_a1_entry, f2_a2_entry, f3_b0_entry, f3_b1_entry, f3_b2_entry, f3_a1_entry, f3_a2_entry, f4_b0_entry, f4_b1_entry, f4_b2_entry, f4_a1_entry, f4_a2_entry])

    # Checking for received data
    _sport.receive_response(output)

    # Thread
    t1 = threading.Thread(target=plot_loop)
    t1.start()

    ## BEGIN TKINTER EVENT LOOP
    window.mainloop()
    

main()


###############################################################################
# Author                Revision                Date
#
# N Blanchard           -                       6/15/2025
###############################################################################