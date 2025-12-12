###############################################################################
#   Copyright (c) 2025, Nick Blanchard
#
#   This software is distributed under the MIT license and may be used and
#   modified without restrictions.
#
#   File:               roomshaker.py
#   Author:             Nick Blanchard
#   Contact:            nblanchardaz@gmail.com
#   Date:               6/15/2025
#   Revision:           -
#   Description:        This file hold source code for the ROOM SHAKER GUI
#                       application.
#   Application Notes:  
#   Known Bugs:         Exception raised when the user selects 'cancel' instead of choosing a file to load parameters from.
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
from ctypes import windll


###############################################################################
## Enable DPI awareness for Windows 8.1 and higher
###############################################################################


try:
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass



###############################################################################
## AUXILIARY CLASSES AND FUNCTIONS
###############################################################################


coefs = []


###############################################################################
## AUXILIARY CLASSES AND FUNCTIONS
###############################################################################


# Function to create widgets with all options
def create_widget(parent, widget_type, **options):
    return widget_type(parent, **options)


# Class to load filter parameters from external files
class floader:

    def store_fields(self, fields):

        # Store fields and the number of filters
        self.fields = fields
        self.num_filters = len(fields)

        # Store the number of parameters per filter
        if (self.num_filters) > 0:
            self.num_parameters = len(fields[0])
        else:
            self.num_parameters = 0
    
    def set_single_filter_fields(self, _vals, _fields):

        # For each parameter that was read in
        for i in range(len(_vals)):
            if (i < len(_fields)):
                _fields[i].delete(0, tk.END)
                _fields[i].insert(0, _vals[i])
            else:
                print("ERROR at " + str(_vals[i]))

    def set_all_fields(self, vals):

        # For each filter we have
        for i in range(len(vals)):
            
            if (len(vals[i]) == len(self.fields[i])):
                # Set the fields for this filter
                self.set_single_filter_fields(vals[i], self.fields[i])

    # Function for opening the file explorer window to select BEQ file
    def browse_files(self, is_txt, is_single, filter_index=0):

        # Open file explorer
        filename = filedialog.askopenfilename(initialdir = "/", title = "Select a File", filetypes = (("Text files", "*.txt*"), ("all files", "*.*")))
        
        # Load biquad filter parameters from file
        row_data=[]
        data_list = []
        with open(filename, 'r', newline='') as f:
            csv_reader = csv.reader(f)
            for row in csv_reader:
                for word in row:
                    row_data.append(word)
                data_list.append(row_data)
                row_data = []

        if (is_single==True):
            self.set_single_filter_fields(data_list[0], self.fields[filter_index])
        else:
            self.set_all_fields(data_list)

    # Function to load a 10dB low shelf with a cutoff at 50 Hz
    def enable_super_bass(self):
        params = []
        for i in range(4):
            params.extend(create_low_shelf())  
        self.set_fields(params)


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

        # BYTE 0: NUMBER OF FILTERS PARAMETERS IN THIS PACKET
        # BYTE 1: STARTING FILTER INDEX
        # BYTES 2 to n: FILTER PARAMETERS

        # Filter parameters are stored in an array of size 20.
        # {b0 b1 b2 a0 a1}, maximum of 4 stages
        # ...

        # First packet transmission
        first_msg = bytearray()
        first_msg.extend(b'\x0A')       # 10 parameters in first message (2 filters)
        first_msg.extend(b'\x00')       # Start at the 0th index   
        first_msg.extend(raw[0:40])     # Filter parameters
        first_msg.extend(b'\xAA')       # Ending the message with 0xAA indicates to NOT update the stored filter parameters yet, because more are coming
        self.ser.write(first_msg)

        # Second packet transmission
        second_msg = bytearray()
        second_msg.extend(b'\x0A')      # 10 parameters in second message (2 filters)
        second_msg.extend(b'\x28')      # Start at the 40th index   
        second_msg.extend(raw[40:80])   # Filter parameters
        second_msg.extend(b'\xBB')      # Ending the message with 0xBB indicates to update the stored filter parameters, because all have been sent
        self.ser.write(second_msg)      

    def enable_autoeq(self):
        
        # Send 0xDE to indicate auto EQ mode is enabled
        raw = bytearray()
        raw.extend(b'\xDE')
        self.ser.write(raw)

    def receive_response(self, widget):

        # Check if data has been received
        if isinstance(self.ser, serial.Serial):
            if self.ser.in_waiting > 0:
                data = ((str(self.ser.read(self.ser.in_waiting)))[2:-1]).replace("\\n", "\n") + "\n"  # Newline characters that come via serial port are interpreted as literals, hence the need to replace them with true newline characters
                widget.insert(tk.END, data)

        window.after(100, lambda:_sport.receive_response(widget))


# Class to represent bode plot
class plot:

    def __init__(self, fs):
        self.fs = fs
        self.previous_coefs = []

    def create(self, parent, toolbar_true, fields):

        # Figure
        self.fig, self.ax = plt.subplots(figsize=(4, 2), dpi=100)
        self.phase_fig, self.phase_ax = plt.subplots(figsize=(4,2), dpi=100)

        # Place in tkinter window
        self.fig.set_layout_engine('constrained')
        self.canvas = FigureCanvasTkAgg(self.fig, master = parent)  
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(pady=10)

        self.phase_fig.set_layout_engine('constrained')
        self.phase_canvas = FigureCanvasTkAgg(self.phase_fig, master = parent)  
        self.phase_canvas.draw()
        self.phase_canvas.get_tk_widget().pack(pady=10)

        # Optional: Add toolbar
        if (toolbar_true):
            self.toolbar = NavigationToolbar2Tk(self.canvas, parent)
            self.toolbar.update()
            self.toolbar.grid(row=7, column=7, rowspan=1)

        # Save data fields
        self.data_fields = fields

        # Update plot
        # self.update()

    def update(self, entries):

        # Get biquad parameters
        values = get_vals(entries)

        # Check for a change
        if (self.previous_coefs == values):
            window.after(250, self.update, entries)
            return
            
        # Store for next check
        self.previous_coefs = values
        
        # Negate all a coefficients to reverse signs on a-coefficients; this is due to a mismatch in difference equation forms between the signal.freqz library and the CMSIS-DSP library
        for index in range(len(values)):
            if (index % 5 == 3 or index % 5 == 4):
                values[index] = -1*values[index]

        # Create 4 biquads
        try:
            # NOTE: all a coefficients are negated relative to what the Room Shaker gets; this is due to a mismatch in difference equation forms between the signal.freqz library and the CMSIS-DSP library
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
        phase_degrees = np.angle(H, deg=True)             # Extract phase in degrees
        freq_degrees = W1

        # Clear previously plotted curve
        self.ax.clear()
        self.phase_ax.clear()

        # Create bode plots
        self.ax.semilogx(freq_degrees[0:400], magnitude_db[0:400])
        self.ax.set_title("Filter Frequency Response")
        self.ax.set_xlabel("Frequency (Hz)")
        self.ax.set_ylabel("Gain (dB)")
        self.ax.xaxis.set_major_locator(mticker.LogLocator(base=10.0, numticks=5))
        self.ax.axis([1, 400, -15, 15])
        self.ax.locator_params(axis='y', nbins=6)
        # plt.tight_layout()
        self.canvas.draw()

        self.phase_ax.semilogx(freq_degrees[0:400], phase_degrees[0:400])
        self.phase_ax.set_title("Filter Phase Response")
        self.phase_ax.set_xlabel("Frequency (Hz)")
        self.phase_ax.set_ylabel("Phase (Degrees)")
        self.phase_ax.xaxis.set_major_locator(mticker.LogLocator(base=10.0, numticks=5))
        self.phase_ax.axis([1, 400, -180, 180])
        self.phase_ax.locator_params(axis='y', nbins=6)
        # plt.tight_layout()
        self.phase_canvas.draw()

        window.after(250, self.update, entries)

# def plot_loop():
#     while 1:
#         _plot.update()

def hz_to_rads(hz):
    return (hz * math.pi / 180)

def rads_to_hz(rads):
    return (rads * 180 / math.pi)

def create_low_shelf(FS=48076, F0=50, SHELF_GAIN_dB=3, S=1):
    # Modeled after the online Biquad Cookbook
    # https://webaudio.github.io/Audio-EQ-Cookbook/audio-eq-cookbook.html

    # Intermediate variables
    A = 10**(SHELF_GAIN_dB/40)
    w0 = 2 * math.pi*F0/FS
    cosw0 = math.cos(w0)
    sinw0 = math.sin(w0)
    alpha = (sinw0/2)*math.sqrt((A + 1/A) * (1/S - 1) + 2)

    # Lowshelf filter parameters
    b0 = A*((A+1)-(A-1)*cosw0+2*math.sqrt(A)*alpha)
    b1 = 2*A*((A-1)-(A+1)*cosw0)
    b2 = A*((A+1)-(A-1)*cosw0-2*math.sqrt(A)*alpha)
    a0 = (A+1)+(A-1)*cosw0+2*math.sqrt(A)*alpha
    a1 = -1 * (-2*((A-1)+(A+1)*cosw0))                  # Negate to comply with CMSIS-DSP
    a2 = -1* ((A+1)+(A-1)*cosw0-2*math.sqrt(A)*alpha)   # Negate to comply with CMSIS-DSP
    
    # Normalize
    return [b0/a0, b1/a0, b2/a0, a1/a0, a2/a0]

def get_vals(entries):
    # Retrieve values from Tkinter fields
    values = []
    for i in range(len(entries)):
        for j in range(len(entries[i])):
            values.append(float(entries[i][j].get()))

    return values


###############################################################################
## GLOBAL VARIABLES
###############################################################################


# MAIN WINDOW
window = tk.Tk()

# Serial port
_sport = sport()

# Bode plot
_plot = plot(fs=48076)  # Sampling frequency = 48kHz

# File loader
_floader = floader()


###############################################################################
## MAIN FUNCTION
###############################################################################


def main():

    ## MAIN WINDOW
    screenheight = window.winfo_screenheight()
    screenwidth = window.winfo_screenwidth()
    window.minsize(int(0.7*screenwidth), int(0.7*screenheight))
    window.maxsize(int(0.7*screenwidth), int(0.7*screenheight))
    window.title("ROOM SHAKER")
    icon = PhotoImage(file = os.path.join(os.path.dirname(__file__), "imgs\\icon.png"))
    window.iconphoto(False, icon)
    window.update()
    window.rowconfigure(0, weight=1)
    window.rowconfigure(1, weight=1)
    window.rowconfigure(2, weight=1)
    window.rowconfigure(3, weight=1)
    window.rowconfigure(4, weight=1)
    window.rowconfigure(5, weight=1)
    window.columnconfigure(0, weight=1)

    ## FIRST ROW
    first_row = create_widget(window, tk.Frame, height=2*window.winfo_height()/20, width=window.winfo_width(), bg="blue")
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
    second_row = create_widget(window, tk.Frame, height=2*window.winfo_height()/20, width=window.winfo_width(), bg="red")
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
    third_row = create_widget(window, tk.Frame, height=10*window.winfo_height()/20, width=window.winfo_width()) # bg="green"
    third_row.grid(row=2, column=0, sticky="nsew")
    third_row.columnconfigure(0, weight=5)
    third_row.columnconfigure(1, weight=1)
    third_row.columnconfigure(2, weight=1)
    third_row.columnconfigure(3, weight=1)
    third_row.columnconfigure(4, weight=1)
    third_row.columnconfigure(5, weight=1)
    third_row.columnconfigure(6, weight=1)
    third_row.columnconfigure(7, weight=1)
    third_row.columnconfigure(8, weight=1)
    third_row.columnconfigure(9, weight=5)
    third_row.columnconfigure(10, weight=5)
    # third_row.grid_propagate(False)
    # third_row.update()

    # Biquad expression
    bqd = Image.open(os.path.join(os.path.dirname(__file__), "imgs\\biquad_transparent.png"))
    bqd_resize_factor = 1.0 * min((second_row.winfo_width()*.25)/bqd.width, (second_row.winfo_height()*.75)/bqd.height)
    bqd_img = bqd.resize((int(bqd.width * bqd_resize_factor), int(bqd.height * bqd_resize_factor)), Image.Resampling.LANCZOS)
    bqd_bg = ImageTk.PhotoImage(bqd_img)
    bqd_label = create_widget(third_row, tk.Label, image=bqd_bg)
    bqd_label.grid(row=0, column=1, columnspan=7)

    # Labels
    b0_label = create_widget(third_row, tk.Label, text="b0", font=("Helvetica", 12, "bold"))
    b0_label.grid(row=1, column=2)
    b1_label = create_widget(third_row, tk.Label, text="b1", font=("Helvetica", 12, "bold"))
    b1_label.grid(row=1, column=3)
    b2_label = create_widget(third_row, tk.Label, text="b2", font=("Helvetica", 12, "bold"))
    b2_label.grid(row=1, column=4)
    a1_label = create_widget(third_row, tk.Label, text="a1", font=("Helvetica", 12, "bold"))
    a1_label.grid(row=1, column=5)
    a2_label = create_widget(third_row, tk.Label, text="a2", font=("Helvetica", 12, "bold"))
    a2_label.grid(row=1, column=6)

    # Store labels and entry fields
    labels = []     # List
    entries = []    # List of lists
    load_buttons = []   # List

    # Number of filters and parameters per filter
    num_filters=8
    num_parameters=5

    # Configure rows to support the correct number of filters
    third_row.rowconfigure(0, weight=1)
    for i in range(1, num_filters+3):
        third_row.rowconfigure(i, weight=1)
    third_row.rowconfigure(num_filters+2, weight=10)
    # third_row.update()

    # Generate all of the labels and input fields
    for i in range(num_filters):
        row=i+2
        e = create_widget(third_row, tk.Label, text=("Biquad " + str(i)), font=("Helvetica", 12, "bold"))
        e.grid(row=row, column=1)
        labels.append(e)
        entries.append([])
        for j in range(num_parameters):
            e = create_widget(third_row, tk.Entry, width=10)
            e.grid(row=row, column=j+2)
            entries[i].append(e)
        e = create_widget(third_row, tk.Button, text="Load from .txt...", command=lambda:_floader.browse_files(is_txt=True, is_single=True, filter_index=i), font=("Helvetica", 10, "bold"))
        e.grid(row=row, column=num_parameters+2)
        load_buttons.append(e)

    # Set default values for all filters
    for i in range(0, num_filters):
        for j in range(num_parameters):
            if (j == 0):
                entries[i][j].insert(0, "1.0000000")
            else:
                entries[i][j].insert(0, "0.0000000")

    # Create frequency response plot
    freq_plot_container = create_widget(third_row, tk.Frame, height=2*window.winfo_height()/5) # bg="grey"
    freq_plot_container.grid(row=0, column=9, rowspan=num_filters+4, sticky="nsew")
    _plot.create(parent=freq_plot_container, toolbar_true=False, fields=entries)

    # Quick options
    quick_options_container = create_widget(third_row, tk.Frame,  height=3*window.winfo_height()/40)
    quick_options_container.grid(row=num_filters+2, column=1, columnspan=7, sticky="nsew")
    quick_options_container.rowconfigure(0, weight=3)
    quick_options_container.rowconfigure(1, weight=1)
    quick_options_container.rowconfigure(2, weight=3)
    quick_options_container.columnconfigure(0, weight=3)
    quick_options_container.columnconfigure(1, weight=1)
    quick_options_container.columnconfigure(2, weight=1)
    quick_options_container.columnconfigure(3, weight=1)
    quick_options_container.columnconfigure(0, weight=3)

    # Upload TXT
    txt = create_widget(quick_options_container, tk.Button, text="Load all biquad filters from .txt file...", command=lambda:_floader.browse_files(is_txt=True, is_single=False), font=("Helvetica", 12, "bold"))
    txt.grid(row=1, column=1)
    
    # Upload BEQ
    beq = create_widget(quick_options_container, tk.Button, text="Load biquad filters from BEQDesigner file...", command=lambda:_floader.browse_files(is_txt=False, is_single=False), font=("Helvetica", 12, "bold"))
    beq.grid(row=1, column=2)
    beq["state"] = "disabled" # Disable this button until it is fully implemented

    # Superbass Mode
    beq = create_widget(quick_options_container, tk.Button, text="Super Bass Mode", command=_floader.enable_super_bass, font=("Helvetica", 12, "bold"))
    beq.grid(row=1, column=3)

    ## FOURTH ROW
    fourth_row = create_widget(window, tk.Frame, height=3*window.winfo_height()/40, width=window.winfo_width(), bg="purple")
    fourth_row.grid(row=3, column=0)
    fourth_row.grid_propagate(False)
    fourth_row.columnconfigure(0, weight=2)
    fourth_row.columnconfigure(1, weight=1)
    fourth_row.columnconfigure(2, weight=2)
    fourth_row.rowconfigure(0, weight=1)
    fourth_row.rowconfigure(1, weight=1)
    fourth_row.rowconfigure(2, weight=1)

    # Filter configurator
    configurator = create_widget(fourth_row, tk.Button, text="Generate new filter parameters...", font=("Helvetica", 12, "bold"))
    configurator.grid(row=1, column=1)
    configurator["state"] = "disabled" # Disable this button until it is fully implemented

    ## FIFTH ROW
    fifth_row = create_widget(window, tk.Frame, height=3*window.winfo_height()/40, width=window.winfo_width(), bg="orange")
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
    # fifth_row.update()

    # Upload Filters
    upload = create_widget(fifth_row, tk.Button, text="Upload Filters", command=lambda:_sport.upload_filters(get_values(entries)), font=("Helvetica", 12, "bold"))
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
    sixth_row = create_widget(window, tk.Frame, height=3*window.winfo_height()/20, width=window.winfo_width(), bg="black")
    sixth_row.grid(row=5, column=0)
    sixth_row.columnconfigure(0, weight=1)
    sixth_row.columnconfigure(1, weight=1)
    sixth_row.columnconfigure(2, weight=1)
    sixth_row.rowconfigure(0, weight=1)
    sixth_row.rowconfigure(1, weight=1)
    sixth_row.rowconfigure(2, weight=1)
    sixth_row.grid_propagate(False)
    # sixth_row.update()

    # Text box
    output = create_widget(sixth_row, tk.Text, height=6, width=100)
    output.grid(row=1, column=1)

    # Store entry fields for file loader
    _floader.store_fields(fields=entries)

    # Checking for received data
    _sport.receive_response(output)

    # Thread
    # t1 = threading.Thread(target=plot_loop)
    # t1.start()

    window.after(250, _plot.update, entries)

    ## BEGIN TKINTER EVENT LOOP
    window.mainloop()
    

main()


###############################################################################
# Author                Revision                Date
#
# N Blanchard           -                       6/15/2025
###############################################################################