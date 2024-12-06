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