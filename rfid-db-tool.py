#!/usr/bin/env python3
#
# rfid-db-tool
#
# This little Python/Tk GUI tool was created for locally storing and
# managing RFID numbers list and uploading it to a doorlock embedded
# device using a binary protocol though a serial UART interface.
#
# The embedded device was created by a friend of mine, a master's
# student, whom I helped with developing the PC part of his project.
#
# This project might be useful for people developing a similar project,
# or for people who are learning Python GUI development using Tk
# or for the people who are learning binary protocols using serial
# communication.
#
# Use `python3 rfid-db-tool.py` to run the application
#
# Requirements
# -------------
# Tk
# PySerial
#
# Tk documentation
# -----------------
# https://python-textbok.readthedocs.io/en/1.0/Introduction_to_GUI_Programming.html
# https://docs.python.org/3/library/tk.html
# https://docs.python.org/3/library/tkinter.html
# https://docs.python.org/3/library/tkinter.ttk.html
# https://www.nmt.edu/tcc/help/pubs/tkinter/tkinter.pdf
#
# PySerial documentation
# -----------------------
# https://pyserial.readthedocs.io/en/latest/shortintro.html
#
# Struct documentation
# ---------------------
# https://docs.python.org/3/library/struct.html
#
# Project Homepage
# -----------------
# https://github.com/0xebef/rfid-db-tool
#
# License
# --------
# GPLv3 or later
#
# Copyright (c) 2020, 0xebef
#

import tkinter
from tkinter import ttk
from tkinter import messagebox

import serial
import serial.tools.list_ports

import struct

class App(object):

    def __init__(self):
        # configuration options
        self.SERIAL_BAUDRATE    = 9600       # serial port baud rate
        self.SERIAL_TIMEOUT_S   = 2          # timeout for serial read function
        self.PACKET_MAX_COUNT   = 32         # max. data count in one packet

        # commands and answers (2 bytes for command/answer, 2 bytes for parameter)
        self.COMMAND_PINGPONG   = 0xCD000000
        self.ANSWER_PINGPONG    = 0xDC000000
        self.COMMAND_WRITECOUNT = 0xCD010000
        self.ANSWER_WRITECOUNT  = 0xDC010000
        self.COMMAND_WRITEDATA  = 0xCD020000
        self.ANSWER_WRITEDATA   = 0xDC020000
        self.COMMAND_READLAST   = 0xCD030000
        self.ANSWER_READLAST    = 0xDC030000

        # as mentioned, the parameter space is 2 bytes,
        # so this limits the largest parameter to be 0xFFFF
        self.DEVICES_COUNT_MAX  = 0xFFFF

        # serial object and status
        self.serial = None
        self.serial_connected = False

        # create main GUI window
        self.root = tkinter.Tk()
        self.root.resizable(width=0, height=0)
        self.root.title('Device Configuration')

        # create main GUI frmae
        self.frm = ttk.Frame(self.root)
        self.frm.pack(expand=True, fill='both')

        # create serial port label
        self.serial_port_label = ttk.Label(self.frm, text='Serial Port:')
        self.serial_port_label.grid(row=0, column=0, padx=8, pady=8, sticky='w')

        # get serial port interfaces list
        available_serial_ports = [port.device for port in serial.tools.list_ports.comports()]

        # create serial port combo box
        self.serial_port_combo = ttk.Combobox(self.frm, values=available_serial_ports)
        self.serial_port_combo.bind('<Return>', self.serial_connect_disconnect_handler)
        self.serial_port_combo.grid(row=1, column=0, padx=8, pady=0, sticky='w')

        # create serial connection/disconnet button
        self.serial_connect_disconnect_button = ttk.Button(self.frm, text='Connect')
        self.serial_connect_disconnect_button['command'] = self.serial_connect_disconnect_handler
        self.serial_connect_disconnect_button.grid(row=1, column=1, columnspan=2, padx=8, pady=0, sticky='e')

        # create a frame for the treeview and its scrollbar
        self.tree_frame = ttk.Frame(self.frm)
        self.tree_frame.grid(row=2, column=0, columnspan=2, padx=8, pady=8, sticky='we')

        # create the treeview
        self.tree = ttk.Treeview(self.tree_frame, selectmode='browse')
        self.tree['columns'] = ('id', 'data')
        self.tree.column('#0', width=16, minwidth=16, stretch=tkinter.NO)
        self.tree.column('id', width=150, minwidth=150, stretch=tkinter.NO)
        self.tree.column('data', width=400, minwidth=200)
        self.tree.heading('#0', text='', anchor=tkinter.W)
        self.tree.heading('id', text='ID', anchor=tkinter.W)
        self.tree.heading('data', text='Data', anchor=tkinter.W)
        self.tree.bind('<Double-Button-1>', self.tree_dblclick_handler) # mouse left-button double-click event
        self.tree.bind('<Button-3>', self.tree_popup_handler)           # mouse right-button single-click event
        self.tree.pack(side='left')

        # create the treeview's vertical scrollbar
        self.tree_vsb = ttk.Scrollbar(self.tree_frame, orient='vertical', command=self.tree.yview)
        self.tree_vsb.pack(side='right', fill='y')

        # bind the treeview and the scrollbar
        self.tree.configure(yscrollcommand=self.tree_vsb.set)

        # create popup menu for treeview
        self.tree_popup_menu = tkinter.Menu(self.frm, tearoff=0)
        self.tree_popup_menu.add_command(label='Add', command=self.tree_popup_menu_add_handler)
        self.tree_popup_menu.add_command(label='Edit', command=self.tree_popup_menu_edit_handler)
        self.tree_popup_menu.add_command(label='Delete', command=self.tree_popup_menu_delete_handler)
        self.tree_popup_menu.add_command(label='Save', command=self.tree_popup_menu_save_handler)
        self.tree_popup_menu.add_command(label='Write to Device', command=self.tree_popup_menu_write_handler)

        # create the close button
        self.close_button = ttk.Button(self.frm, text='Exit', command=self.frm.quit)
        self.close_button.grid(row=3, column=1, padx=8, pady=8, sticky='e')

        # load data into the treeview from a file
        self.load_data_from_file()

    def load_data_from_file(self):
        # try to open the data.txt file
        try:
            f = open('data.txt', 'r')
        except:
            return

        # read the contents line-by-line and insert the data into the treeview
        for line in f:
            self.insert_data_item(line)

        f.close()

    def insert_data_item(self, line):
        parts = line.split(',', maxsplit=1)
        if len(parts) != 2:
            return

        try:
            data_id_hex = parts[0].rstrip()
            data_text = parts[1].rstrip()

            # unpack 4-byte unsigned integer "I"
            # see https://docs.python.org/3/library/struct.html#format-characters
            data_id = struct.unpack('>I', bytes.fromhex(data_id_hex))

            self.tree.insert(parent='', index='end', iid=data_id, values=(data_id_hex, data_text))
        except:
            pass

    def serial_connect_disconnect_handler(self, event=None):
        serial_port = self.serial_port_combo.get()

        if serial_port == '':
            messagebox.showerror(title='Error', message='Please choose a Serial Port')
            return

        if self.serial != None and self.serial.is_open:
            self.serial.close()

        if self.serial_connected:
            self.serial_set_disconnected()
        else:
            try:
                self.serial = serial.Serial(port=serial_port, baudrate=self.SERIAL_BAUDRATE, timeout=self.SERIAL_TIMEOUT_S)
                if not self.serial.is_open:
                    self.serial.open()

                if self.serial.is_open and self.serial_protocol_check():
                    self.serial_set_connected()
                else:
                    self.serial_set_disconnected()
            except:
                self.serial_set_disconnected()

    def serial_set_connected(self):
        self.serial_connected = True
        self.serial_port_combo.configure(state=tkinter.DISABLED)
        self.serial_connect_disconnect_button.configure(text='Disonnect')

    def serial_set_disconnected(self):
        self.serial_connected = False
        self.serial_port_combo.configure(state=tkinter.NORMAL)
        self.serial_connect_disconnect_button.configure(text='Connect')

        if self.serial is not None and self.serial.is_open:
            self.serial.close()

        self.serial = None

    def tree_dblclick_handler(self, event):
        # on double click find the item under the mouse x/y position
        item = self.tree.identify('item', event.x, event.y)
        if item is None or item == '':
            return

        # open the "add/edit" dialog for editing the found item
        self.data_add_edit(item)

    def tree_popup_handler(self, event):
        # open the popup menu
        self.tree_popup_menu.tk_popup(event.x_root, event.y_root)

    def tree_popup_menu_add_handler(self):
        # open the "add/edit" dialog for adding a new item
        self.data_add_edit(None)

    def tree_popup_menu_edit_handler(self):
        # open the "add/edit" dialog for editing the selected item or show error
        item = self.tree.focus()
        if item:
            self.data_add_edit(item)
        else:
            messagebox.showerror(title='Error', message='Nothing selected')

    def tree_popup_menu_delete_handler(self):
        # delete the selected item
        item = self.tree.focus()
        if item:
            self.data_delete(item)
        else:
            messagebox.showerror(title='Error', message='Nothing selected')

    def tree_popup_menu_save_handler(self):
        # get the treeview children and the count
        children = self.tree.get_children()
        count = len(self.tree.get_children())

        # count validation
        if count > self.DEVICES_COUNT_MAX:
            messagebox.showerror(title='Error', message='Too much data')
            return

        result = True

        # save data into the data.txt file using a loop
        try:
            f = open('data.txt', 'w')

            for i in range(count):
                values = self.tree.item(children[i])['values']
                f.write(str(values[0]).zfill(8))
                f.write(',')
                f.write(str(values[1]))
                f.write('\r\n')

            f.close()
        except:
            pass

        if not result:
            messagebox.showerror(title='Error', message='Save error')
        else:
            messagebox.showinfo(title='Success', message='Saved {} lines'.format(count))

    def tree_popup_menu_write_handler(self):
        # we need open serial connection for writing the data
        if self.serial == None or not self.serial.is_open:
            messagebox.showerror(title='Error', message='No connection')
            return

        # get the treeview children and the count
        children = self.tree.get_children()
        count = len(self.tree.get_children())

        # count validation
        if count > self.DEVICES_COUNT_MAX:
            messagebox.showerror(title='Error', message='Too much data')
            return

        result = True
        result_txt = ''

        # write data to the device in chunks using loops
        try:
            request = struct.pack('>I', self.COMMAND_WRITECOUNT + count)
            expected_answer = struct.pack('>I', self.ANSWER_WRITECOUNT + count)
            self.serial.write(request)
            answer = self.serial.read(4)
            if answer != expected_answer:
                result = False
            else:
                i = 0
                while i < count:
                    if count - i > self.PACKET_MAX_COUNT:
                        current_count = self.PACKET_MAX_COUNT
                    else:
                        current_count = count - i

                    request = struct.pack('>I', self.COMMAND_WRITEDATA + current_count)
                    self.serial.write(request)

                    for j in range(current_count):
                        values = self.tree.item(children[i + j])['values']
                        request  = bytearray.fromhex(str(values[0]))
                        self.serial.write(request)

                    expected_answer = struct.pack('>I', self.ANSWER_WRITEDATA + current_count)
                    answer = self.serial.read(4)
                    if answer != expected_answer:
                        result = False
                        result_txt = 'Unexpected answer'
                        break

                    i += current_count
        except Exception as e:
            result = False
            result_txt = str(e)

        if not result:
            messagebox.showerror(title='Error', message='Communication error: ' + result_txt)
        else:
            messagebox.showinfo(title='Success', message='Written {} lines'.format(count))

    def read_last_id_handler(self, event=None, default=''):
        if self.serial == None or not self.serial.is_open:
            return default

        try:
            request = struct.pack('>I', self.COMMAND_READLAST)
            expected_answer = struct.pack('>I', self.ANSWER_READLAST)
            self.serial.write(request)

            answer = self.serial.read(4)
            if answer != expected_answer:
                return default

            data_id = self.serial.read(4)
            if data_id is None:
                return default

            return data_id.hex().zfill(8)
        except:
            pass

        return default

    def data_add_edit(self, item):
        if item is None:
            values = ['00000000', '']
        else:
            values = self.tree.item(item)['values']

        # Set up window
        win = tkinter.Toplevel()
        win.title("Add/Edit")
        win.resizable(width=0, height=0)

        col_id_label = ttk.Label(win, text = 'ID: ')
        col_id_label.grid(row=0, column=0, padx=8, pady=8)

        col_id_entry = ttk.Entry(win)
        col_id_entry.insert(0, values[0])
        col_id_entry.grid(row=0, column=1, padx=8, pady=8)

        col_id_read = ttk.Button(win, text='<', width=1)
        col_id_read['command'] = lambda: [col_id_entry.delete(0, 'end'), col_id_entry.insert(0, self.read_last_id_handler(default=values[0]))]
        col_id_read.grid(row=0, column=2, padx=8, pady=8)

        col_data_label = ttk.Label(win, text = 'Data: ')
        col_data_label.grid(row=1, column=0, padx=8, pady=8)

        col_data_entry = ttk.Entry(win)
        col_data_entry.insert(0, values[1])
        col_data_entry.grid(row=1, column=1, padx=8, pady=8)

        def data_edit_update_then_destroy():
            if self.tree_confirm_entry(item, col_id_entry.get(), col_data_entry.get()):
                win.destroy()
            else:
                messagebox.showerror(title='Error', message='Invalid Data', parent=win)

        buttons_frame = ttk.Frame(win)
        buttons_frame.grid(row=2, columnspan=3, column=0, padx=8, pady=8, sticky='e')

        ok_button = ttk.Button(buttons_frame, text = 'OK')
        ok_button.bind('<Button-1>', lambda e: data_edit_update_then_destroy())
        ok_button.pack(side='left')

        cancel_button = ttk.Button(buttons_frame, text = 'Cancel')
        cancel_button.bind('<Button-1>', lambda e: win.destroy())
        cancel_button.pack(side='right')

    def data_delete(self, item):
        if item is not None:
            self.tree.delete(item)

    def serial_protocol_check(self):
        if self.serial == None or not self.serial.is_open:
            return False

        try:
            request = struct.pack('>I', self.COMMAND_PINGPONG)
            expected_answer = struct.pack('>I', self.ANSWER_PINGPONG)
            self.serial.write(request)
            answer = self.serial.read(4)
            if answer != expected_answer:
                return False
        except:
            return False

        return True

    def tree_confirm_entry(self, item, data_id_hex, data_text):
        try:
            if data_id_hex is None or data_id_hex == '' or len(data_id_hex) != 8 or data_text is None or data_text == '':
                return False

            data_id = struct.unpack('>I', bytes.fromhex(data_id_hex))

            if data_id is None or data_id == 0:
                return False

            if item is not None:
                current_index = self.tree.index(item)
                self.tree.delete(item)
            else:
                current_index = 'end'

            self.tree.insert(parent='', index=current_index, iid=data_id, values=(data_id_hex, data_text))

        except:
            return False

        return True

app = App()
app.root.mainloop()
