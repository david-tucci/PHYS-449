import matplotlib.pyplot as plt
import numpy as np
import RPi.GPIO as GPIO
from bokeh.plotting import figure, show
import tweepy



class MAX31855(object):
    '''Python driver for [MAX38155 Cold-Junction Compensated Thermocouple-to-Digital Converter](http://www.maximintegrated.com/datasheet/index.mvp/id/7273)
     Requires:
     - The [GPIO Library](https://code.google.com/p/raspberry-gpio-python/) (Already on most Raspberry Pi OS builds)
     - A [Raspberry Pi](http://www.raspberrypi.org/)
    '''
    def __init__(self, cs_pin, clock_pin, data_pin, units = "c", board = GPIO.BCM):
        '''Initialize Soft (Bitbang) SPI bus
        Parameters:
        - cs_pin:    Chip Select (CS) / Slave Select (SS) pin (Any GPIO)  
        - clock_pin: Clock (SCLK / SCK) pin (Any GPIO)
        - data_pin:  Data input (SO / MOSI) pin (Any GPIO)
        - units:     (optional) unit of measurement to return. ("c" (default) | "k" | "f")
        - board:     (optional) pin numbering method as per RPi.GPIO library (GPIO.BCM (default) | GPIO.BOARD)
        '''
        self.cs_pin = cs_pin
        self.clock_pin = clock_pin
        self.data_pin = data_pin
        self.units = units
        self.data = None
        self.board = board

        # Initialize needed GPIO
        GPIO.setmode(self.board)
        GPIO.setup(self.cs_pin, GPIO.OUT)
        GPIO.setup(self.clock_pin, GPIO.OUT)
        GPIO.setup(self.data_pin, GPIO.IN)

        # Pull chip select high to make chip inactive
        GPIO.output(self.cs_pin, GPIO.HIGH)

    def get(self):
        '''Reads SPI bus and returns current value of thermocouple.'''
        self.read()
        self.checkErrors()
        return getattr(self, "to_" + self.units)(self.data_to_tc_temperature())

    def get_rj(self):
        '''Reads SPI bus and returns current value of reference junction.'''
        self.read()
        return getattr(self, "to_" + self.units)(self.data_to_rj_temperature())

    def read(self):
        '''Reads 32 bits of the SPI bus & stores as an integer in self.data.'''
        bytesin = 0
        # Select the chip
        GPIO.output(self.cs_pin, GPIO.LOW)
        # Read in 32 bits
        for i in range(32):
            GPIO.output(self.clock_pin, GPIO.LOW)
            bytesin = bytesin << 1
            if (GPIO.input(self.data_pin)):
                bytesin = bytesin | 1
            GPIO.output(self.clock_pin, GPIO.HIGH)
        # Unselect the chip
        GPIO.output(self.cs_pin, GPIO.HIGH)
        # Save data
        self.data = bytesin

    def checkErrors(self, data_32 = None):
        '''Checks error bits to see if there are any SCV, SCG, or OC faults'''
        if data_32 is None:
            data_32 = self.data
        anyErrors = (data_32 & 0x10000) != 0    # Fault bit, D16
        noConnection = (data_32 & 1) != 0       # OC bit, D0
        shortToGround = (data_32 & 2) != 0      # SCG bit, D1
        shortToVCC = (data_32 & 4) != 0         # SCV bit, D2
        if anyErrors:
            if noConnection:
                raise MAX31855Error("No Connection")
            elif shortToGround:
                raise MAX31855Error("Thermocouple short to ground")
            elif shortToVCC:
                raise MAX31855Error("Thermocouple short to VCC")
            else:
                # Perhaps another SPI device is trying to send data?
                # Did you remember to initialize all other SPI devices?
                raise MAX31855Error("Unknown Error")

    def data_to_tc_temperature(self, data_32 = None):
        '''Takes an integer and returns a thermocouple temperature in celsius.'''
        if data_32 is None:
            data_32 = self.data
        tc_data = ((data_32 >> 18) & 0x3FFF)
        return self.convert_tc_data(tc_data)

    def data_to_rj_temperature(self, data_32 = None):
        '''Takes an integer and returns a reference junction temperature in celsius.'''
        if data_32 is None:
            data_32 = self.data
        rj_data = ((data_32 >> 4) & 0xFFF)
        return self.convert_rj_data(rj_data)

    def convert_tc_data(self, tc_data):
        '''Convert thermocouple data to a useful number (celsius).'''
        if tc_data & 0x2000:
            # two's compliment
            without_resolution = ~tc_data & 0x1FFF
            without_resolution += 1
            without_resolution *= -1
        else:
            without_resolution = tc_data & 0x1FFF
        return without_resolution * 0.25

    def convert_rj_data(self, rj_data):
        '''Convert reference junction data to a useful number (celsius).'''
        if rj_data & 0x800:
           without_resolution = ~rj_data & 0x7FF
           without_resolution += 1
           without_resolution *= -1
        else:
             without_resolution = rj_data & 0x7FF
        return without_resolution * 0.0625

    def to_c(self, celsius):
        '''Celsius passthrough for generic to_* method.'''
        return celsius

    def to_k(self, celsius):
        '''Convert celsius to kelvin.'''
        return celsius + 273.15

    def to_f(self, celsius):
        '''Convert celsius to fahrenheit.'''
        return celsius * 9.0/5.0 + 32

    def cleanup(self):
        '''Selective GPIO cleanup'''
        GPIO.setup(self.cs_pin, GPIO.IN)
        GPIO.setup(self.clock_pin, GPIO.IN)

class MAX31855Error(Exception):
     def __init__(self, value):
         self.value = value
     def __str__(self):
         return repr(self.value)

if __name__ == "__main__":

    # Multi-chip example
    import time
    cs_pins = [4,17,18,24]
    clock_pin = 23
    data_pin = 22
    units = "c"
    thermocouples = []
    
    
    for cs_pin in cs_pins:
        thermocouples.append(MAX31855(cs_pin, clock_pin, data_pin, units))
    running = True
    
#    Note if one would like to add a thermocouple. Change the code by adding a row to matrix, add an elif statement
#    and change the last elif to 5, as well add a list before hand and add which cs_pin it is in.
    
    
#   columns is the temperature every second
#   rows is the amount of thermocouples
    matrix = [[0 for columns in range(1)] for rows in range(4)]
    
#   i is the amount of thermocouples
    i = 0 #steps
    
#   seconds updates the time    
    seconds =0
    list_seconds=[0]
    
    while(running):
        # This stops the loop so we can loop for 86400 seconds which is one day
        if seconds == 101:
            print('A new day')
            
            break
            
        try:
            for thermocouple in thermocouples:
                rj = thermocouple.get_rj()
                try:
                    tc = thermocouple.get()
                except MAX31855Error as e:
                    tc = "Error: "+ e.value
                    running = False 
                
#                 print(tc)
                print("tc: {} and rj: {}".format(tc, rj))
                
                # adding temperature to the most recently added column of the matrix. Meaning this puts the
                # right temperature for each of the 4 thermocouples.
                if i == 0 : # thermocouple 1
                    matrix[0][seconds]=tc
                    
                elif i == 1 : # thermocouple 2
                    matrix[1][seconds]=tc
                    
                elif i == 2 : # thermocouple 3
                    matrix[2][seconds]=tc
                
                elif i == 3 : # thermocouple 4
                    matrix[3][seconds]=tc
                
                elif i == 4: # resets steps
                    i=0
                    
                
                i+=1 #moves on to next thermocouple (steps)
            
#                 print(matrix)
            print(seconds)
            time.sleep(1)
            
            
#          bokeh part for plot... works well but needs wifi so very slow... 1 second equal 3 just for code
#          then need to wait for it to load on wifi usually crashes after first 3 
            
            if seconds == 100:  
                p = figure(title="Temperature of thermocouples", x_axis_label="time(s)",y_axis_label="Temperature(C)")
                p.line(list_seconds, matrix[1], legend_label="Temperature of thermocouple 2", line_color="blue", line_width=2)
                p.line(list_seconds, matrix[2], legend_label="Temperature of thermocouple 3", line_color="green", line_width=2)
                p.line(list_seconds, matrix[3], legend_label="Temperature of thermocouple 4", line_color="red", line_width=2)
                show(p)          
                
#             plt.plot(list_seconds,matrix[1])
#             plt.plot(list_seconds,matrix[2])
#             plt.plot(list_seconds,matrix[3])
#             plt.xlabel("Time(s)")
#             plt.ylabel("Temperature(C)")
#             plt.show()
            # The next 4 lines is to add seconds to update the graph.
            # This loop adds a column in the matrix this column is the Temp for the next second.
            for col in matrix:
                col.append(0)
            seconds+=1
            list_seconds.append(seconds)
            
            
        except KeyboardInterrupt:
            running = False
    
    for thermocouple in thermocouples:
        thermocouple.cleanup()

    
#problem is delay time maybe up the sleep or say 1 second = 3
# and how toexport plot onto twitter. p.show() creates html websites.