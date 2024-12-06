# PA3ANG, October - 2024
# version 1.11 
# added FT8 w/ DATA mode and TX on/off
# added DUP mode again
# removed SPLIT mode 
#
# Layout adjusted for Windows
#
# COM port use in parameter to enable different usage of the program
# 
# This program connects to a Icom IC-705 transceiver and reads the RX frequency to display.
# The program does swith to DUPlex mopde with a caculated offset based on the default parameters and the QO-100 bandplan.
# Because the LNB is drifting slightly because of temperature the program has a calibration function to calibrate on the lower CW beacon. This
# beacon does key up to 1089050045 and with the AUTOTUNE function on the IC-705 you can zero beat in. When accepting the calibration the 
# DUPlex offset is calculated with the Dailed frequency - Beacon frequency as LNB_CALIBRATE
# The DUPlex offset then becomes: 500 - LNB_CALIBRATE/100 - TCXO_OFFSET, where TCXO_OFFSET is the aging of the SG Lab up transverter.
#
# Start the program and click 525/CW or 700/USB to send all needed settings to the IC-705
#  - store current frequentie and mode
#  - frequentie RX displayed
#  - power on 430 MHz to 5% (CW) or 44% (USB)
# Presing Exit will disable dup and will terminate the program.

import serial, time, socket, pickle, sys, bluetooth
from tkinter import *
from tkinter import ttk

# Serial port  and settings
SERIAL_SPEED        	= 19200
SERIAL_STOPBITS     	= serial.STOPBITS_TWO
SERIAL_TIMEOUT      	= 1     # in seconds
SERIAL_POLLING      	= 500   # in milliseconds


# ip address of IC-705 connected to WiFi
tcp_ip = '192.168.178.51'
# standard tcp port for this transsmision
tcp_port = 50001

# bluetooth 
target_device = '30:31:7D:34:0F:AD'

# Transceiver commands
CMD_PREAMBLE        	= [0xFE, 0xFE, 0xA4, 0xE0,]
CMD_STOPBYTE        	= [0xFD]
	
CMD_READ_FREQ       	= [0x03,]
CMD_READ_MODE       	= [0x04,]
CMD_READ_PTT        	= [0x1C, 0X00,]

CMD_SET_USB         	= [0x06, 0x01,]
CMD_SET_CW          	= [0x06, 0x03,]
CMD_SET_USB_UNSEL   	= [0x26, 0x01, 0x01,]
CMD_SET_CW_UNSEL    	= [0x26, 0x01, 0x03,]

CMD_SET_DUP_ON      	= [0x0F, 0x11,]
CMD_SET_DUP_OFF     	= [0x0F, 0x10,]
CMD_SET_DATAMODE_ON 	= [0x1A, 0x06, 0x01, 0x02,]
CMD_SET_DATAMODE_OFF	= [0x1A, 0x06, 0x00, 0x02,]
CMD_CHANGE_VFO      	= [0x07, 0xB0,]
CMD_SET_FIX_SCOPE   	= [0x27, 0x14, 0x00, 0x01,]
CMD_SET_CENTER_SCOPE	= [0x27, 0x14, 0x00, 0x00,]
CMD_SET_TX_ON       	= [0x1C, 0x00, 0x01,]
CMD_SET_TX_OFF      	= [0x1C, 0x00, 0x00,]

CMD_SET_POWER_SSB   	= [0x14, 0x0A, 0x01, 0x03,]   #40%
CMD_SET_POWER_CW    	= [0x14, 0x0A, 0x00, 0x13,]   #5%
CMD_SET_POWER_MAX   	= [0x14, 0x0A, 0x02, 0x55,]   #100%

CMD_SET_SQUELCH_OFF 	= [0x14, 0x03, 0x00, 0x00,]   #0%
CMD_SET_SQUELCH_ON  	= [0x14, 0x03, 0x01, 0x60,]   #65%

# This offset is needed during READ operations if CI-V Address A4h, CI-V Transceive ON and CI-V USB Echo Back ON
OFFSET_READ_FREQ    	= 5
OFFSET_READ_FREQ_DIGIT	= 6
OFFSET_READ_PTT    	= 6
OFFSET_READ_PTT_STATUS	= 7
OFFSET_READ_MODE    	= 7
OFFSET_READ_MODE_DIGIT	= 6

# Beacon used for calibration  (Frequency *10Hz)
Beacon_frequency    = 1048950045  

# Up and Down link offsets (Frequency *10Hz)
LNB_OFFSET		= 1005700000
# LNB TCXO offset on 10GHz
LNB_CALIBRATE		= -4800
# SG Labs transverter IF is 196800000 to reacvh 432 Mhz. reference only
# TCXO in SG Labs is aging and now 900 Hz off in cold situation drifting a bit up
TCXO_OFFSET		= .9

# Default vaiables
QO_frequency        	= 0
RX_frequency        	= 0
TX_status	    	= 0

# boolean for program flow
setcal              	= False

# serial write and read functions
def serial_write(cmd):
    # open serial port
    ser = serial.Serial(port=SERIAL_PORT, baudrate=SERIAL_SPEED, stopbits=SERIAL_STOPBITS, timeout=SERIAL_TIMEOUT)
    ser.write(CMD_PREAMBLE+cmd+CMD_STOPBYTE)
    ser.close()

def serial_read(cmd, char):
    # open serial port
    ser = serial.Serial(port=SERIAL_PORT, baudrate=SERIAL_SPEED, stopbits=SERIAL_STOPBITS, timeout=SERIAL_TIMEOUT)
    ser.write(CMD_PREAMBLE+cmd+CMD_STOPBYTE)
    resp = ser.read(char)
    ser.close()
    # delete preamble 0xFE, 0xFE, 0xE0, 0xA4  and last byte 0xFD
    # char was capturing all bytes 
    return resp[5:char:]

# navigation functions
def set_CW ():
    serial_write(CMD_SET_CW)
    set_squelch_off()
    serial_write(CMD_SET_CW_UNSEL)
    serial_write(CMD_SET_POWER_CW)
    set_frequency(1048952500)
    
def set_USB ():
    serial_write(CMD_SET_USB)
    serial_write(CMD_SET_DATAMODE_OFF)
    serial_write(CMD_SET_USB_UNSEL)
    serial_write(CMD_CHANGE_VFO)
    serial_write(CMD_SET_DATAMODE_OFF)
    serial_write(CMD_CHANGE_VFO) 
    serial_write(CMD_SET_POWER_SSB)
    set_frequency(1048970000)

def set_USBD ():
    serial_write(CMD_SET_USB)
    serial_write(CMD_SET_DATAMODE_ON)
    serial_write(CMD_SET_USB_UNSEL)
    serial_write(CMD_CHANGE_VFO)
    serial_write(CMD_SET_DATAMODE_ON)
    serial_write(CMD_CHANGE_VFO) 
    serial_write(CMD_SET_POWER_CW)
    set_frequency(1048954000)

def set_680 ():
    set_frequency(1048968000)
def set_800 ():
    set_frequency(1048980000)
def set_900 ():
    set_frequency(1048990000)

def set_squelch_on ():
    serial_write(CMD_SET_SQUELCH_ON)
    button_squelch.configure(command = set_squelch_off, text="SQ Off", fg="red")

def set_squelch_off ():
    serial_write(CMD_SET_SQUELCH_OFF)
    button_squelch.configure(command = set_squelch_on, text="SQ On", fg="black")
    
def set_tx_on ():
    serial_write(CMD_SET_TX_ON)
    button_tx.configure(command = set_tx_off, text="TX Off", fg="red")

def set_tx_off ():
    serial_write(CMD_SET_TX_OFF)
    button_tx.configure(command = set_tx_on, text="TX On", fg="black")
              
def set_bcn ():
    global RX_return_frequency, setcal, BCN_return_mode
    resp = serial_read(CMD_READ_MODE, 7+OFFSET_READ_MODE)
    BCN_return_mode = (resp[0+OFFSET_READ_MODE_DIGIT])
    setcal = True
    RX_return_frequency = RX_frequency
    serial_write(CMD_SET_CW)
    set_squelch_off()
    set_frequency(Beacon_frequency)
    serial_write(CMD_SET_CENTER_SCOPE)
    button_calibrate.configure(command= calibrate, fg="red")
    
def calibrate ():
    global LNB_CALIBRATE, setcal, BCN_return_mode
    LNB_CALIBRATE = LNB_CALIBRATE - (QO_frequency - Beacon_frequency)
    button_calibrate.configure(command= set_bcn, fg="black")
    # return to mode and frequency b4 starting calibration
    serial_write([0x06, BCN_return_mode,])
    Return_frequency= (RX_return_frequency*100000) + LNB_OFFSET + LNB_CALIBRATE
    setcal = False
    set_frequency(int(Return_frequency))
    serial_write(CMD_SET_FIX_SCOPE)
    set_dup_offset()

   
# this is the mainloop function the program will stau in
def read_frequency ():
    # this is the mainloop and controls the serial port
    global QO_frequency, RX_frequency

    # read frequency, calculate QO frequency based on LNB_OFFSET + LNB_CALIBRATE
    resp = serial_read(CMD_READ_FREQ, 11+OFFSET_READ_FREQ)
    try:
    	resp_bytes = (resp[4+OFFSET_READ_FREQ_DIGIT], resp[3+OFFSET_READ_FREQ_DIGIT], resp[2+OFFSET_READ_FREQ_DIGIT], resp[1+OFFSET_READ_FREQ_DIGIT], resp[0+OFFSET_READ_FREQ_DIGIT])
    	frequency = "%01x%02x%02x%02x%02x" % resp_bytes
    	RX_frequency = int(frequency)/10
    except:
    	print("Exeption: wrong frequency read.")
    QO_frequency = RX_frequency + LNB_OFFSET + LNB_CALIBRATE
         
    # read transceiver transmit status 
    try:
    	resp = serial_read(CMD_READ_PTT, 8+OFFSET_READ_PTT)
    	TX_status =  resp[1+OFFSET_READ_PTT_STATUS]
    except:
    	TX_status = 0
    
    # transmitting     
    if TX_status==1:
         label_frequency.config(fg="orange")
        
    # receiving
    if TX_status==0:
        # display calibrate offset
        COF = ('{0:.2f}'.format(LNB_CALIBRATE/100))
        button_calibrate.config(text=COF)
        
        # check if in QO-100 narrow band 
        if (QO_frequency < 1048950000 or QO_frequency > 1049000000):
            label_frequency.config(text="-out of band-")
            label_frequency.config(fg='red')
        
        # all ok to update readout and perform update functions
        else:
            # display operating QO-100 frequency
            QOF = ('{0:.2f}'.format(QO_frequency))
            QOF = QOF[0:5] + "." + QOF[5:8] + "." + QOF[8:10]
            label_frequency.config(text=QOF)
            label_frequency.config(fg="blue")
            
    # keep reading  / looping  in 500mS
    window.after(SERIAL_POLLING, read_frequency)

# update functions
def freq_to_cmd(frequency):
    frequencyStr = str(frequency*10)
    byte5 = "%02d" % int(frequencyStr[0:1], 16)
    byte4 = "%02d" % int(frequencyStr[1:3], 16)
    byte3 = "%02d" % int(frequencyStr[3:5], 16)
    byte2 = "%02d" % int(frequencyStr[5:7], 16)
    byte1 = "%02d" % int(frequencyStr[7:9], 16)
    return [int(byte1), int(byte2), int(byte3), int(byte4), int(byte5),]

def set_frequency (frequency):
    # calculate RX frequency based on QO_frequency  LNB_OFFSET - LNB_CALIBRATE
    RX_frequency = (frequency - LNB_OFFSET - LNB_CALIBRATE)
    # write RX frequency in selected vfo command 05
    serial_write([0x05,]+freq_to_cmd(RX_frequency))

def set_dup_offset ():
    # switch in DUP- mode if not already
    serial_write(CMD_SET_DUP_ON)
    
    # the duplex frequency is visible on the screen.
    DUP_offset = (500 - LNB_CALIBRATE/100 - TCXO_OFFSET)
    DUP_offsetStr = str(DUP_offset*100)
    DUP_P2 = "%02d" % int(DUP_offsetStr[0:2], 16)
    DUP_P1 = "%02d" % int(DUP_offsetStr[2:4], 16)
    DUP_P0 = "%02d" % int(DUP_offsetStr[4:5]+'0', 16)
         
    # write DUP_offset max 999.9 kHz
    cmd = [0x0D, int(DUP_P1), int(DUP_P2), 0x00,]
    serial_write(cmd)

def exit_program ():
    # cancel DUP mode, open Squelch and max power
    serial_write(CMD_SET_DUP_OFF)
    set_squelch_off()
    serial_write(CMD_SET_POWER_MAX)
    # and stop program
    exit() 
    
# start of program

# get parsed comm port if any
if len(sys.argv) <= 1:
    # COM6 is my IC-705 Serial Port A (CI-V) 
    SERIAL_PORT="COM6"
else:
    SERIAL_PORT = sys.argv[1]
  
# create a TkInter Window
window = Tk()
window.geometry("750x50")

# top line
window.wm_title("IC-705 -- QO-100 Controller V1.11 -- Windows 10 -- @"+SERIAL_PORT+", "+str(SERIAL_SPEED)+"Bd. DUP- Mode.")

# frequency label
label_frequency = Label(window, font=('Arial', 30, 'bold'),  fg='blue', width=11)
label_frequency.grid(column=1, row=1, padx=(2,2))

# function keys
button_calibrate = Button(window, command = set_bcn, width=6)
button_calibrate.grid(column=0, row=1, ipady=6, padx=(6, 2))

Button(window, text = "CW" , command = set_CW, width=4).grid(column=6, row=1, ipady=6, padx=(2, 2))
Button(window, text = "USB", command = set_USB, width=4).grid(column=7, row=1, ipady=6, padx=(2, 2))
Button(window, text = "FT8", command = set_USBD, width=4).grid(column=8, row=1, ipady=6, padx=(2, 2))
Button(window, text = "680", command = set_680, width=4).grid(column=9, row=1, ipady=6, padx=(2, 2))
Button(window, text = "800", command = set_800, width=4).grid(column=10, row=1, ipady=6, padx=(2, 2))
Button(window, text = "900", command = set_900, width=4).grid(column=11, row=1, ipady=6, padx=(2, 2))
button_squelch  = Button(window, text = "SQ On", command = set_squelch_on, width=6)
button_squelch.grid(column=12, row=1, ipady=6, padx=(2, 2))
button_tx  = Button(window, text = "TX On", command = set_tx_on, width=6)
button_tx.grid(column=13, row=1, ipady=6, padx=(2, 2))
Button(window, text = "Exit",    command = exit_program, width=5).grid(column=14, row=1, ipady=6, padx=(2, 6))

# start satellite mode by
set_dup_offset()
print ("Status: program started and DUP- offset set.")

# and go into an invinite loop
read_frequency()
window.mainloop()