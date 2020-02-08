#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:        ADC for Remote Control Receiver 
# Purpose:     Controlling the battery  
#              with a ADC1115 board 
# Author:      Bernd Hinze
#
# Created:     30.01.2020
# Copyright:   (c) Bernd Hinze 2020
# Licence:     MIT see https://opensource.org/licenses/MIT
# -------------------------------------------------------------------------------
import time
from pca9685 import bus

ADS_ADDRESS = 0x48  # address pin is connected with GND
REG_CONV = 0x00
REG_CFG = 0x01

# Data sample rates

ADS1115_SAMPLE = {
    8:    0x0000,
    16:   0x0020,
    32:   0x0040,
    64:   0x0060,
    128:  0x0080,
    250:  0x00A0,
    475:  0x00C0,
    860:  0x00E0
}

# AIN N = GND 
CHANNEL = {0: 0x4000, 1: 0x5000, 2: 0x6000, 3: 0x7000}

ADS1X15_GAIN =  {6.144: 0x0000,
                 4.096: 0x0200, 
                 2.048: 0x0400,
                 1.024: 0x0600,
                 0.512: 0x0800,
                 0.256: 0x0A00}
        
# Modes
ADS_CONF_OS_SINGLE = 0x8000
CONTINUOUS = 0x0000
SINGLE = 0x0100
OFFSET = -0x01
GAIN = 2.048
EXGAIN = 5.69 # external divider at ads1115 input
def set_cfg(channel=0, programmable_gain=GAIN, samples_per_second=32):
    # sane defaults  0000 0001 0000 0011  Disable Comperator & Single Shot
    # leaf power down mode
    config = 0x0000
    config |= ADS_CONF_OS_SINGLE  # power up 
    config |= CHANNEL[channel]
    config |= ADS1X15_GAIN[programmable_gain]
    config |= CONTINUOUS
    config |= ADS1115_SAMPLE[samples_per_second]
    config |= 0x0003  # disable comparator
                                      
    bus.write_i2c_block_data(ADS_ADDRESS, REG_CFG, [(config >> 8) & 0xFF, config & 0xFF])
    time.sleep(1.0/samples_per_second + 0.0001) 
    print (hex(config))
     
def read_cfg():
    data = bus.read_i2c_block_data(ADS_ADDRESS, REG_CFG, 2)
    return ((data[0] << 8) | data[1])

def read_adc():
    data = bus.read_i2c_block_data(ADS_ADDRESS, REG_CONV, 2)
    val = ((data[0] << 8) | data[1] ) 
    # val = (((data[0] << 8) | data[1] ) >> 4)  1015
    return val

def convert_to_V(ana, divider=1.0): 
    """ converts conversion input into float volt value with two digits """
    ana -= OFFSET
    voltage = (ana * GAIN / 32767) * divider  
    return round(voltage, 2) 

def reset_adc():
    bus.write_byte_data(ADS_ADDRESS, 0x00, 0x06)

def init():
    reset_adc()
    time.sleep(0.02)
    set_cfg(0)
    print (hex(read_adc()))

def main():    
    init()
    while True: 
        print (convert_to_V(read_adc(), 5.69), "V")
        time.sleep(1)

if __name__ == '__main__':
    main()