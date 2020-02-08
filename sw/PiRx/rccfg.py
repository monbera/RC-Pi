#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Name:        RC-Pi Remote Control
# Purpose:     Configurationg of models with Pi-Receiver 
#              
#             
# Author:      Bernd Hinze
#
# Created:     30.01.2020
# Copyright:   (c) Bernd Hinze 2020 
# Licence:     MIT see https://opensource.org/licenses/MIT
# ---------------------------------------------------------------------------- 
ADS = True      # configure either the ADS1115 Board is available or not
AVAL = "0.00"    # default value for analog input
SIM = False      # running for test and integration on a PC
# PCA9685 Parameter
FREQ = 50.0 
port_tx = 6000
port_rx = 6100

if not SIM:
    ifname = "wlan0"
else:
    ifname = "wlp2s0"

SERVO, DIO, L298 = range(3)  

'''
Parameter for channel configuration 
(MODE, CENTER, RATE, REVERSE, ACCFILT, FAILSAFE, STEPW)
MODE = SERVO, DIO or L298
CENTER = center position of servo in ms
RATE = max. diviation from center in ms 
REVERSE = boolean reverse orientation 
ACCFILT = boolean, using a filter or not to degrease the rising rate of values
FAILSAFE = 0..254 
STEPW = max. steps af rate within of cycle rate of 20 ms used by the filter
'''

models = {
    'TESTBED' : [(SERVO, 0, 1.4, 0.4, False, True, 127, 10), 
                 (SERVO, 4, 1.5, 0.3, False, False, 127, 127),
                 (DIO, 5, 1.5, 0.5, False, False, 0, 127)],

     'MyCar'  : [(SERVO, 0, 1.5, 0.5, True, True, 127, 10), 
                 (SERVO, 4, 1.5, 0.2, False, False, 127, 127)],
                
     'CASPARCAR': [(L298, 0, 1.5, 0.5, False, False, 127, 127), 
                  (SERVO,4, 1.5, 0.25, True, False, 127, 127),
                  (DIO, 3, 1.5, 0.5, True, False, 0, 127),
                  (DIO, 6, 1.5, 0.5, True, False, 254, 127)] }
  
MODEL = 'TESTBED'
ID = "RC#001"

   
def main():
    pass       
       
if __name__ == '__main__':
    main()
                         
                         
                         
                         
        
        
        
        
   
