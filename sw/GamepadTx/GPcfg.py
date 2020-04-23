#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Name:        RC-Pi Gamepad
# Purpose:     Configuration
#              
#             
# Author:      Bernd Hinze
#
# Created:     30.01.2020
# Copyright:   (c) Bernd Hinze 2020
# Licence:     MIT see https://opensource.org/licenses/MIT
# ----------------------------------------------------------------------------
from time import sleep
from os import listdir

'''
Configuration output of my Gamepad
GP_Conf = { 0L: [0L, 1L, 3L, 4L], 
   1L: [304L, 305L, 306L, 307L, 308L, 309L, 310L, 311L, 312L, 313L, 314L, 315L], 
   3L: [(0L, AbsInfo(value=0, min=-128, max=127, fuzz=0, flat=15, resolution=0)), 
      (1L, AbsInfo(value=0, min=-128, max=127, fuzz=0, flat=15, resolution=0)), 
      (5L, AbsInfo(value=0, min=-128, max=127, fuzz=0, flat=15, resolution=0)), 
      (6L, AbsInfo(value=128, min=0, max=255, fuzz=0, flat=15, resolution=0)), 
      (16L, AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0, resolution=0)), 
      (17L, AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0, resolution=0))], 
   4L: [4L]}
'''
gamepad_addr = "", 6000
receiver_port = 6100
screen_port = 5000   
PC = False  # running for test and integration on a PC

if not PC:
    ifname = "wlan0"
    USB_event = '/dev/input/event0'
else:
    ifname = "wlp2s0"
    # event number has to be configured
    USB_event = '/dev/input/event10'
  
# {eventcode : [channel, invert, dual rate ],....}
analogEvent = {1 : [0, True, False, -128, 127], 
               5 : [3, False, False, -128, 127]}
# {eventcode : (channel, increment),....}
trimEvent = {304 : [0, -1], 
             305 : [3, -1],  
             306 : [3, 1], 
             307 : [0, 1]}
# {eventcode : reference to event code of analog events }  (Dualrate buttons)
duraEvent = {308 : 1, 
             310 : 5}
# eventcode of shutdown button
shutdEvent = 312  
# eventlist for button events
eventlist = (304, 305, 306, 307, 308, 310, 312)    
minAnaVal = -128 
    

def searchGP():
    ''' helper function to check the USB-dev event
    unplug gamepad
    call the script manually > python3 GPcfg.py
    plug in gamepad when the message has been emitted
    the event will be emitted     
    '''
    lsWoutGP = set((listdir('/dev/input/')))
    print ("Stecke Gamepad an")
    sleep(10)
    lsWithGP = set ((listdir('/dev/input/')))
    delta = lsWithGP - lsWoutGP
    return delta 

def main():       
    print (searchGP())
    
            
    
if __name__ == '__main__':
    main()
