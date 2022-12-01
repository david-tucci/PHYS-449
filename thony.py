import matplotlib.pyplot as plt
import numpy as np
import RPi.GPIO as GPIO
from bokeh.plotting import figure, show
import tweepy
from matplotlib.ticker import MultipleLocator




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

    # Multi-chip 
    import time
    from time import strftime,localtime
    cs_pins = [4,17,18,24]
    clock_pin = 23
    data_pin = 22
    units = "c"
    thermocouples = []
    
    
    for cs_pin in cs_pins:
        thermocouples.append(MAX31855(cs_pin, clock_pin, data_pin, units))
    running = True
    
#    Note if one would like to add a thermocouple. Add a row to matrix, add an elif statement
#    and change the last elif to 5. Don't forget to add which cs_pin it is in.
    
    
#   columns is the temperature every minute
#   rows is the amount of thermocouples
    matrix = [[0 for columns in range(1)] for rows in range(4)]
    
#   i is the amount of thermocouples
    i = 0 #start
    
#   minutes updates the time (its an estimate)    
    minutes = 0
    list_mins = [0]
    
    while(running):
        # Next line stops the loop.
        if minutes == 49: # 1 minute is 30 minutes add 1 for the amount of minutes you want.# 49 mins in a day
            print('Run Complete')
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
                
                # Adding temperature to the most recently added column(time) of the matrix. Meaning this puts the
                # right temperature for each of the 4 thermocouples.
                if i == 0 : # thermocouple 1
                    matrix[0][minutes]=tc
                    
                elif i == 1 : # thermocouple 2
                    matrix[1][minutes]=tc
                    
                elif i == 2 : # thermocouple 3
                    matrix[2][minutes]=tc
                
                elif i == 3 : # thermocouple 4
                    matrix[3][minutes]=tc
                
                elif i == 4: # resets steps
                    i=0
                    
                
                i+=1 #moves on to next thermocouple (steps)
            

            print(minutes)
            
            # Using twitter API from tweepy
            CONSUMER_KEY = 'KwcLi3vRvV8vTdUvCYtr7v9Mr'
            CONSUMER_SECRET = 'kzvsMqYfcVt9QEvQmSlVndOV6XQf8Urc3qye7hEvfbHpfwNju9'

            ACCESS_KEY = '1578097015178907653-fgIqG3XkaHHGF96C21dlTOwL0MOgRJ'
            ACCESS_SECRET = 'bnuH2EjmlEFEkph483rdxqSyUMp96dXSTNsOct5XriwwY'

            auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
            auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
                
            api = tweepy.API(auth)
                
                
#           Everything under this if statement is to create and send graphs to twitter  
            if minutes%1 ==0: # 1
                
                if minutes == 0:
                    current_time = time.strftime("%H:%M:%S", localtime())
                    times = [current_time]
                if minutes != 0:
                    current_time = time.strftime("%H:%M:%S", localtime())
                    times.append(current_time)
                
                # Changing the amount of ticks shown on x (time) axis.
                if minutes <= 10:
                    ticks = 1
                    ticksminor = 1
                else:
                    ticks = 6 # 30mins for 6 steps = 180 mins(3hr) for total  8 ticks in a day might need to increa delay cluttered
                    ticksminor = 1
                    
                
                ml = MultipleLocator(ticks)
                mlminor = MultipleLocator(ticksminor)
                
                plt.axes().xaxis.set_major_locator(ml)
                plt.axes().xaxis.set_minor_locator(mlminor)

                plt.plot(times, matrix[1], color = "red", label = "Thermocouple 1")
                plt.plot(times, matrix[2], color = "blue", label = "Thermocouple 2")
                plt.plot(times, matrix[3], color = "green", label = "Thermocouple 3")
                plt.xlabel("Time(minutes)")
                plt.ylabel("Temperature(C)")
                plt.xticks(rotation=20)
                plot=plt.savefig('plot.png')
                
                
                # Sends to twitter
                ret = api.media_upload(filename="plot.png", file=plot)
                api.update_status(media_ids=[ret.media_id_string], status="Thermocouple 1 is red,\nThermocouple 2 is blue,\nThermocouple 3 is green,\n Started:" " " +str(times[0])+ " " "EST,\nCurrent Time: " " "+str(current_time)+ " ""EST")
                
                
#               The next 5 lines is to add minutes and to update the graph.
#               This loop adds a column in the matrix this column allows us to add a temperature for the next minute.
                for col in matrix:
                    col.append(0)
                minutes+=1
                list_mins.append(minutes)
                time.sleep(1794)# 1794 because there is a delay of 6 seconds to send to twitter (I think
                          # that it takes 6 seconds to save to the raspberry pi) 1794 seconds = 30 mins
                
            
        except KeyboardInterrupt:
            running = False
    
    for thermocouple in thermocouples:
        thermocouple.cleanup()
