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


###############################################################################
## AUXILIARY CLASSES AND FUNCTIONS
###############################################################################


# Function to create widgets with all options
def create_widget(parent, widget_type, **options):
    return widget_type(parent, **options)

# Function for opening the file explorer window to select BEQ file
def browse_files():

    # Open file explorer
    filename = filedialog.askopenfilename(initialdir = "/", title = "Select a File", filetypes = (("Text files", "*.txt*"), ("all files", "*.*")))
    
    # Load biquad filter parameters from file
    print(filename)

# Function to select and open COM port
def open_com_port(cbox):
    ports = serial.tools.list_ports.comports()
    vals = []
    for port, desc, hwid in sorted(ports):
        # print(f"{port}: {desc} [{hwid}]")
        vals.append(port)
    cbox['values'] = vals

# Function to upload filters to DSP
class sport:

    ser = NONE

    def bind(self, event, portname, buttons):
        if portname != "Select COM Port..." and portname != '':
            try:
                self.ser = serial.Serial(portname, 9600)
            except Exception as e:
                print(f"An error occurred: {e}")
            
            for button in buttons:
                button["state"] = "active"

    def upload_filters(self, values):
        
        # Convert data to bytes
        raw = bytearray()
        for val in values:
            raw.extend(struct.pack('f', val))
        self.ser.write(raw)

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
    

###############################################################################
## GLOBAL VARIABLES
###############################################################################


# MAIN WINDOW
window = tk.Tk()

# Serial port
_sport = sport()


###############################################################################
## MAIN FUNCTION
###############################################################################


def main():

    ## MAIN WINDOW
    window.minsize(1000, 750)
    window.maxsize(1000, 750)
    window.title("ROOM SHAKER")
    icon = PhotoImage(file = os.path.join(os.path.dirname(__file__), "imgs\icon.png"))
    window.iconphoto(False, icon)
    window.update()

    ## FIRST ROW
    first_row = create_widget(window, tk.Frame, height=window.winfo_height()/5, width=window.winfo_width())
    first_row.grid(row=0, column=0)
    first_row.columnconfigure(0, weight=1)
    first_row.columnconfigure(1, weight=1)
    first_row.columnconfigure(2, weight=1)
    first_row.grid_propagate(False)
    first_row.update()

    # Logo
    bg = Image.open(os.path.join(os.path.dirname(__file__), "imgs\\room_shaker_transparent.png"))
    resize_factor = 0.9 * min(first_row.winfo_width()/bg.width, first_row.winfo_height()/bg.height)
    img = bg.resize((int(bg.width * resize_factor), int(bg.height * resize_factor)), Image.Resampling.LANCZOS)
    tk_bg = ImageTk.PhotoImage(img)
    image_label = create_widget(first_row, tk.Label, image=tk_bg)
    image_label.grid(row=0, column=1)

    ## SECOND ROW
    second_row = create_widget(window, tk.Frame, height=window.winfo_height()/10, width=window.winfo_width())
    second_row.grid(row=1, column=0)
    second_row.columnconfigure(0, weight=1)
    second_row.columnconfigure(1, weight=1)
    second_row.columnconfigure(2, weight=1)
    second_row.grid_propagate(False)
    second_row.update()
    chart = Image.open(os.path.join(os.path.dirname(__file__), "imgs\\flow.png"))
    chart_resize_factor = 0.9 * min(second_row.winfo_width()/chart.width, second_row.winfo_height()/chart.height)
    chart_img = chart.resize((int(chart.width * chart_resize_factor), int(chart.height * chart_resize_factor)), Image.Resampling.LANCZOS)
    chart_bg = ImageTk.PhotoImage(chart_img)
    chart_label = create_widget(second_row, tk.Label, image=chart_bg)
    chart_label.grid(row=0, column=1)

    ## THIRD ROW
    third_row = create_widget(window, tk.Frame, height=1.5*window.winfo_height()/5, width=window.winfo_width())
    third_row.grid(row=2, column=0)
    third_row.columnconfigure(0, weight=4)
    third_row.columnconfigure(1, weight=1)
    third_row.columnconfigure(2, weight=1)
    third_row.columnconfigure(3, weight=1)
    third_row.columnconfigure(4, weight=1)
    third_row.columnconfigure(5, weight=1)
    third_row.columnconfigure(6, weight=4)
    third_row.rowconfigure(0, weight=1)
    # third_row.rowconfigure(1, weight=1)
    # third_row.rowconfigure(3, weight=1)
    # third_row.rowconfigure(4, weight=1)
    # third_row.rowconfigure(5, weight=1)
    third_row.rowconfigure(6, weight=1)
    third_row.grid_propagate(False)
    third_row.update()

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
    f1_label = create_widget(third_row, tk.Label, text="Biquad Filter 1", font=("Helvetica", 12, "bold"))
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
    f2_label = create_widget(third_row, tk.Label, text="Biquad Filter 2", font=("Helvetica", 12, "bold"))
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
    f3_label = create_widget(third_row, tk.Label, text="Biquad Filter 3", font=("Helvetica", 12, "bold"))
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
    f4_label = create_widget(third_row, tk.Label, text="Biquad Filter 4", font=("Helvetica", 12, "bold"))
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

    ## FOURTH ROW
    fourth_row = create_widget(window, tk.Frame, height=window.winfo_height()/10, width=window.winfo_width())
    fourth_row.grid(row=3, column=0)
    fourth_row.grid_propagate(False)
    fourth_row.columnconfigure(0, weight=1)
    fourth_row.columnconfigure(1, weight=1)
    fourth_row.columnconfigure(2, weight=1)
    fourth_row.rowconfigure(0, weight=1)
    fourth_row.rowconfigure(1, weight=1)
    fourth_row.rowconfigure(2, weight=1)
    
    # Upload BEQ
    beq = create_widget(fourth_row, tk.Button, text="Load biquad filters from BEQDesigner file...", command=browse_files, font=("Helvetica", 12, "bold"))
    beq.grid(row=1, column=1)


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
    com = create_widget(fifth_row, ttk.Combobox, textvariable=port, postcommand=lambda:open_com_port(com), font=("Helvetica", 12, "bold"))
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

    # Checking for received data
    # window.after(250, _sport.receive_response(output))
    _sport.receive_response(output)

    ## BEGIN TKINTER EVENT LOOP
    window.mainloop()

main()


###############################################################################
# Author                Revision                Date
#
# N Blanchard           -                       6/15/2025
###############################################################################