#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Name:        RC-Pi Gamepad 
# Purpose:     Remote controlling of models with Pi-Receiver 
#              
#             
# Author:      Bernd Hinze
#
# Created:     30.01.2020
# Copyright:   (c) Bernd Hinze 2020
# Licence:     MIT see https://opensource.org/licenses/MIT
# ---------------------------------------------------------------------------- 
import netifaces as ni
import socket
from time import time, sleep
from os import system
from threading import Thread
from evdev import InputDevice
import queue
import GPcfg

'''
Installation of evdev:
    sudo pip install evdev
First check the gamepad configuration with 
   ls /dev/input

   E(Rpi) --->    6000 S (GP) IP ADRESS
   E(Rpi) 6100 <----   S (GP)Cyclic Telegramms
   
   Telegram to the RSCreen (Remote SCREEN) strings, seperated by "," 
   --------------- Status Data by Gamepad ----------------------
    V[0] = HDR (255)  
    V[1] = Dual Rate Channel 0  (DR)
    V[2] = Trimm Channel 0
    V[3] = Mode Channel 0
    V[4] = Dual Rate Channel 4  (DR)
    V[5] = Trimm Channel 4
    V[6] = Com Status (0 = default, 1 connect, 2 = lost)
    ----------------Data of the receiver, forwarded to the Remote SCREEN-----
    V[7] = Voltage of RC accu nn.nn
    V[8] = IP of the receiver
     
'''
q_aloop = queue.LifoQueue(100)
q_eloop = queue.Queue(20)
q_observer = queue.LifoQueue(20)

# -----------  Utilities ----------------------
def get_bc_address(ifname):
    ip = get_ip_address(ifname).split('.')
    bcip = ip[0] + '.' + ip[1] + '.' + ip[2] + '.' + '255'
    return bcip
    
def get_ip_address(ifname):
    try:
        return ni.ifaddresses(ifname)[ni.AF_INET][0]['addr']
    except:
        return "127.0.0.0"
                 
# -----------  Global data definition ----------------------
RED, GREEN, YELLOW = range(3)
# indizes of analog event list in GPcfg.py
CH, IV, DR, MIN, MAX = range(5)
# shut down message
V_Sensor = "0,00"
# some states
shutdown = False
Trtel_update = False
# default screendata
screen_dat = [255, 100, 25, 0, 100, 25, 0]
lenTel = len(screen_dat)
# screen_tel indexes
# COS Status (0 = default, 1 connect, 2 = lost)
HDR, DR0, TR0, V0, DR4, TR4, COS = range(lenTel)
# default contro vaues for 16 channes
contr_dat = [127, 127, 127, 127, 127, 127, 127, 127, \
                 127, 127, 127, 127, 127, 127, 127, 127]
# default trimm values for 16 channes
trim_dat = [25 , 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25]
# mapping dictionary, for each anaog event code to map the GP output from 
# -128 .. 0  ...127 to the range of 0..254 with center value = 127
dict_ValCorr = {}
# -----------  End Global data definition ----------------------


def create_ValCorr(): 
    ''' Creates tables for each event that results from the GP range output
    to a range of 0..254
    ''' 
    global dict_ValCorr
    for event in GPcfg.analogEvent:
        irange = abs(GPcfg.analogEvent[event][MIN]) \
                     + GPcfg.analogEvent[event][MAX]
        if GPcfg.analogEvent[event][IV]:
            tab = []  
            tab.append(254)
            for i in range (irange): 
                tab.append(irange - (i+1))            
            dict_ValCorr[event] = tab
        else:
            tab = []
            tab.append(0) 
            for i in range (irange): 
                tab.append(i) 
            dict_ValCorr[event] = tab

gamepad = InputDevice(GPcfg.USB_event)

def GP_loop(): 
    print('GP_loop running')
    sleep(3)
    for event in gamepad.read_loop():
        if (event.code in GPcfg.analogEvent):            
            if (not q_aloop.full()):               
                q_aloop.put((event.code, event.value), block=False)
                #print ('put_q', event.code, event.value) 
            else: 
                print('q_aloop full')
        elif (event.code in GPcfg.eventlist):
            if (not q_eloop.full()):
                #print (event.code, event.value)
                q_eloop.put((event.code, event.value), block=False)
            else: 
               print('q_eloop full')
                
def update_data():
    ''' updates the contr_dat[] and trim_dat[] by receiving data via queues
        from the GP_loop()
    '''
    global shutdown, Trtel_update, screen_dat, trim_dat
    if (not q_aloop.empty()):
        code, value = q_aloop.get()
        #print ('get_q', code, value)
        if code in GPcfg.analogEvent:
            chan = GPcfg.analogEvent[code][CH]
            gval = value - GPcfg.analogEvent[code][MIN]
            contr_dat[chan] = dict_ValCorr[code][gval]                                
    while(not q_aloop.empty()):                             
        tmp = q_aloop.get()        
    if (not q_eloop.empty()):
        code, value = q_eloop.get()
        if (code in GPcfg.trimEvent) and (value == 1):
            chan = GPcfg.trimEvent[code][0]
            trim_dat[chan] += GPcfg.trimEvent[code][1]
            if trim_dat[chan] > 50:
                trim_dat[chan] = 50
            elif trim_dat[chan] < 0:
                trim_dat[chan] = 0
            Trtel_update = True
        elif (code == GPcfg.shutdEvent):
            shutdown = True  
        elif (code in GPcfg.duraEvent) and (value == 1):   
            drev = GPcfg.duraEvent[code]
            GPcfg.analogEvent[drev][DR] = not GPcfg.analogEvent[drev][DR]
            #print (GPcfg.analogEvent[drev])
            ch = GPcfg.analogEvent[drev][0]
            if ch == 0:
                if GPcfg.analogEvent[drev][DR]: 
                    screen_dat[DR0] = 50                           
                else:
                    screen_dat[DR0] = 100
            if ch == 4:
                if GPcfg.analogEvent[drev][DR]: 
                    screen_dat[DR4] = 50 
                else:
                    screen_dat[DR4] = 100

# Creation of the comma separated strings for the telegram    
def Trimm_update():   
    global screen_dat
    tel = "" 
    for event in GPcfg.analogEvent:
        ch = GPcfg.analogEvent[event][0]
        val = trim_dat[ch] 
        tel = tel + "127," + str(ch) + "," + str(val) + ","
        if ch == 4:
            screen_dat[TR4] = val     
    return tel    

def Control_update():
    tel = ""  
    for event in GPcfg.analogEvent:
        ch = GPcfg.analogEvent[event][CH]
        val = contr_dat[ch] 
        if GPcfg.analogEvent[event][DR] == True:
                val = ((val - 127) // 2) + 127 
        tel = tel + "255," + str(ch) + "," + str(val) + ","                 
    return tel

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
def UDP_run():
    global V_Sensor, Trtel_update, screen_dat
    receiver_port = GPcfg.receiver_port
    receiver_ip = ""
    receiver_ip_received = False
    screen_port = GPcfg.screen_port
    screen_ip = ""
    screen_ip_received = False 
    str_Broadcast = ("GP@" + get_ip_address(GPcfg.ifname)).encode('utf-8')
    
    def UDP_init():
        broadcast_ip = get_bc_address(GPcfg.ifname)
        #---------- Sockket
        sock.bind((GPcfg.gamepad_addr)) 
        for i in range(5):
            # broadcast the own ip
            sent = sock.sendto(str_Broadcast, \
                (broadcast_ip, screen_port))        
            sleep(0.2)             
        print("Start to listen")
              
    def mess_to_receiver(ip, port):
        global Trtel_update
        tel = Control_update()       
        if Trtel_update:
            tel = tel + Trimm_update()
            Trtel_update = False
        # letztes comma delete
        try: 
            sent = sock.sendto(tel.encode('utf-8'), (ip, port))
        except: 
            print("Failed telegram RC  " + str(ip))
        #print (tel)

    def mess_to_screen():
        global screen_dat, V_Sensor
        tel = ""
        if not q_observer.empty():
            a = q_observer.get()
            screen_dat[COS] = a[0] 
            V_Sensor = a[1]                
        while not q_observer.empty():
            tmp = q_observer.get()
        for i in range(lenTel):
            tel =  tel + str(screen_dat[i]) + "," 
        tel = tel + V_Sensor + "," + str(receiver_ip)
        try:
            sent = sock.sendto(tel.encode('utf-8'), (screen_ip, screen_port)) 
        except:
            print("Failed Screen telegram")  
        return time()      
        
    def sent_shutdown():
        rcsd_tel = "100,15,0,"
        for i in range(3):
            try: 
                sent = sock.sendto(rcsd_tel.encode('utf-8'), \
                    (receiver_ip, receiver_port))
            except: 
                print("Failed telegram Shutdown")        
            sleep(0.5)          
        if (GPcfg.PC == False):
            system("sudo shutdown now")
        print("Shutdown") 
    
    t_screen_sent = time()
    UDP_init()
    
    # ----------- running loop ---------------------------      
    while (not shutdown):                  
        while (not receiver_ip_received):                   
            data, address = sock.recvfrom(1024)
            data = data.decode('utf-8')          
            if data:  
                try:  
                    splitdata = data.split('@')
                    if (splitdata[0] == "RSC"):
                        screen_ip = address[0]
                        screen_ip_received = True
                        sent = sock.sendto(str_Broadcast, \
                            (screen_ip, screen_port))
                    elif(splitdata[0][0:2] == "RC"):                     
                        receiver_ip = address[0]
                        receiver_ip_received = True  
                        screen_dat[COS] = GREEN                                     
                except:
                    print("listen exception " + str(data) + (splitdata[0]))       
        update_data()            
        if receiver_ip_received:  
            mess_to_receiver(receiver_ip, receiver_port)
        
        if screen_ip_received: 
            if ((time() - t_screen_sent) > 0.2): 
                t_screen_sent = mess_to_screen()
            
        sleep(0.05) 
        
    # shutdown cmd by pressing shutdown button    
    if receiver_ip_received:
        sent_shutdown()
                 
def Observer_loop():
    # communication data via queue -  V_Sensor and State of communication
    observer_dat = [RED, "0.00"]
    t_rec_tel_rc = time()   
    while True: 
        data, address = sock.recvfrom(1024)
        data = data.decode('utf-8')
        #print (data)
        rectel = data.split('@')
        if (data and (rectel[0][0:2] == "RC")):
            observer_dat[0] = GREEN
            t_rec_tel_rc = time()  
            # sensor data update 
            if (len(rectel) == 3):
                observer_dat[1] = rectel[2]
                #print (observer_dat)
        tout = (time() - t_rec_tel_rc)
        if (tout > 3.0):
            observer_dat[0] = RED
        if not q_observer.full(): 
                q_observer.put(observer_dat, block=False)                      
        sleep(0.4)      

     
def main():       
    while (get_ip_address(GPcfg.ifname) == "127.0.0.0"):
         print ("waiting for networking")
         sleep(1)  
    sleep(1)
    print(gamepad.capabilities())   
    create_ValCorr()  
    Thread(target = GP_loop).start()
    Thread(target = Observer_loop).start()
    UDP_run()
    
            
    
if __name__ == '__main__':
    main()
   
