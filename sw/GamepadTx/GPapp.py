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

# Installation of evdev:
#    sudo pip install evdev
# First check the gamepad configuration with 
#   ls /dev/input

q_aloop = queue.LifoQueue(100)
q_eloop = queue.Queue(20)
q_observer = queue.LifoQueue(20)
q_obs_to_Udp_loop = queue.Queue(20)

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
    
def bytostr(inp):
    '''Converts an integer < 256 into a coded string'''
    if (inp < 256):
        h = inp // 16     
        l = inp % 16  
        return (lockup[h]) + (lockup[l])
    else:
        return "00"  
    
def strtobyte (codstr): 
    if (len(codstr) == 2):
        return (ord(codstr[0])-48)*16 + (ord(codstr[1])-48)
    else: return -1
                 
# -----------  Global data definition ----------------------
RED, GREEN, YELLOW = range(3)
# indizes of analog event list in GPcfg.py
CH, IV, DR, MIN, MAX = range(5)
# some states
shutdown = False
Trtel_update = False
# default screendata
screen_dat = [4, 127, 0, 0, 0,        \
                 0,                   \
                 "00",                \
                 "00",                \
                 0, 100, 25, 127,     \
                 3, 100, 25, 127]
lenTel = len(screen_dat)
# screen_tel indexes
# COS Status (0 = default, 1 connect, 2 = lost)
ID, IP1, IP2, IP3, IP4, COS , SVAL1, SVAL2, START = range(9)

sCH, sDR, sTR, sVAL = range(4)
# default contro vaues for 16 channes
contr_dat = [127, 127, 127, 127, 127, 127, 127, 127, \
                 127, 127, 127, 127, 127, 127, 127, 127]
# default trimm values for 16 channes
trim_dat = [25 , 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25]
# mapping dictionary, for each anaog event code to map the GP output from 
# -128 .. 0  ...127 to the range of 0..254 with center value = 127
dict_ValCorr = {}
lockup = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
                       ":", ";", "<", "=", ">", "?"]
CENTER = 127
# -----------  End Global data definition ----------------------
                
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
                    screen_dat[START+1] = GPcfg.DualRate                           
                else:
                    screen_dat[START+1] = 100
            if ch == 3:
                if GPcfg.analogEvent[drev][DR]: 
                    screen_dat[START+5] = GPcfg.DualRate 
                else:
                    screen_dat[START+5] = 100   

def Trimm_update():   
    global screen_dat
    tel = "" 
    for event in GPcfg.analogEvent:
        ch = GPcfg.analogEvent[event][0]
        val = trim_dat[ch] 
        tel = tel + "7?" + bytostr(ch) + bytostr(val)
        if ch == 3:
            screen_dat[START + sTR + 4] = val 
    return tel    


def Control_update():
    tel = chr(2) + "02" 
    for event in GPcfg.analogEvent:
        ch = GPcfg.analogEvent[event][CH]
        val = contr_dat[ch] 
        if GPcfg.analogEvent[event][DR] == True:
            val = CENTER + round((val - CENTER) * GPcfg.DualRate / 100)
        tel = tel + "??" + bytostr(ch) + bytostr(val)               
    return tel
   

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.bind((GPcfg.gamepad_addr)) 
   
def UDP_run():
    print('Udp running')
    global  Trtel_update, screen_dat  
    rx_port = GPcfg.receiver_port
    screen_port = GPcfg.screen_port     
    bc_ip = get_bc_address(GPcfg.ifname)
    screen_ip = bc_ip
    rx_ip = bc_ip 
    t_screen_sent = time()
    t_BC_sent = time()
        
    def Tx_BC():
        """Creates the string coded telegram including the owne IP - Tx_BC
        """
        tel = ""
        ip = get_ip_address(GPcfg.ifname).split('.')    
        tel = chr(2) + "03"
        for i in range (len(ip)):
            tel = tel + bytostr(int(ip[i]))
        tel = tel + chr(13)
        return tel  

    Tx_BC = Tx_BC().encode('utf-8')        
        
    def mess_to_receiver(ip, port):
        global Trtel_update
        tel = Control_update()       
        if Trtel_update:
            tel = tel + Trimm_update() 
            Trtel_update = False
        tel = tel + chr(13)
        try: 
            sent = sock.sendto(tel.encode('utf-8'), (ip, port))
        except: 
            print("Failed telegram RC  " + str(ip))
        #print (tel)

    def iptotel(ip):
        tel = ""
        ipl = ip.split('.') 
        if (len(ipl) == 4):
            for i in range (len(ipl)):
                tel = tel + bytostr(int(ipl[i]))
        return tel

    def mess_to_screen(ip, port, rx_ip):
        global screen_dat
        tel = chr(2) + "04" + iptotel(rx_ip)
        if not q_observer.empty():
            a = q_observer.get()
            screen_dat[COS] = a[0] 
            screen_dat[SVAL1] = a[1][0:2]
            screen_dat[SVAL2] = a[1][2:4]  
        
        while not q_observer.empty():
            tmp = q_observer.get()     
        tel = tel + bytostr(screen_dat[COS]) + screen_dat[SVAL1] + \
              screen_dat[SVAL2]
        #print ("Voltage" , screen_dat[SVAL1], screen_dat[SVAL2] )
        for i in range(START, lenTel):
            tel =  tel + bytostr(screen_dat[i])
        tel = tel + chr(13)
        try:
            sent = sock.sendto(tel.encode('utf-8'), (ip, port)) 
        except:
            print("Failed Screen telegram")  
        return time()      
        
    def sent_shutdown(ip, port):
        rcsd_tel = chr(2) + "04" + bytostr(15) + bytostr(0) + chr(13)
        for i in range(3):
            try: 
                sent = sock.sendto(rcsd_tel.encode('utf-8'), (ip, port))
            except: 
                print("Failed telegram Shutdown")        
            sleep(0.5)          
        if (GPcfg.PC == False):
            system("sudo shutdown now")
        print("Shutdown")            
  
    # ----------- running loop ---------------------------      
    while (not shutdown):  
        if (not q_obs_to_Udp_loop.empty()):
            ID, ip = q_obs_to_Udp_loop.get()
            if (ID == 5) :
                screen_ip = ip
                #print ("Screen IP", screen_ip)
            if (ID == 1):  
                rx_ip = ip
                #print ("Rx IP", rx_ip)
                
                     
        if ((time() - t_BC_sent) > 2.0):
            try: 
                sent = sock.sendto(Tx_BC, (screen_ip, screen_port))
                t_BC_sent = time()
            except: 
                print("Failed telegram to sreen") 
                
        if ((time() - t_screen_sent) > 0.2): 
            try:
                t_screen_sent = mess_to_screen(screen_ip, screen_port, rx_ip)
            except:
                print("Failed data telegram to sreen") 
       
        update_data()              
        mess_to_receiver(bc_ip, rx_port)  
        t_rx_sent = time()
        sleep(0.03)    
        
    # shutdown cmd by pressing shutdown button    
    sent_shutdown(bc_ip, rx_port)

                 
def Observer_loop():
    # communication data via queue -  V_Sensor and State of communication
    print('Observer Loop running')
    observer_dat = [RED, "0000"]
    t_rec_tel_rc = time()  
    Tel_ID, ip = range(2)
    QuetoUDP = [0, ""]           
    while True: 
        data, address = sock.recvfrom(1024)
        data = data.decode('utf-8')
        #print (data)
        if (data):
            # Rx_BC received ?
            if (strtobyte(data[1:3]) == 1):
                observer_dat[0] = GREEN 
                observer_dat[1] = data[11:15]
                QuetoUDP[Tel_ID] = 1
                QuetoUDP[ip] = address[0] 
                t_rec_tel_rc = time()
                    
            # Screen broadcast ?
            if (strtobyte(data[1:3]) == 5): 
                QuetoUDP[Tel_ID] = 5
                QuetoUDP[ip] = address[0]
                
            if not q_obs_to_Udp_loop.full():
                #print("QuetoUDP", QuetoUDP)
                q_obs_to_Udp_loop.put(QuetoUDP, block=False)   
        
        tout = (time() - t_rec_tel_rc)
        if (tout > 3.0):
            observer_dat[0] = RED
        if not q_observer.full(): 
                q_observer.put(observer_dat, block=False)                      
        sleep(0.5)      

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
    #sleep(3)
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

     
def main():  
    sleep(5) 
    while (get_ip_address(GPcfg.ifname) == "127.0.0.0"):
         print ("waiting for networking")
         sleep(1)      
    #print(gamepad.capabilities())   
    create_ValCorr()  
    Thread(target = GP_loop).start()
    Thread(target = Observer_loop).start()
    UDP_run()
    
            
    
if __name__ == '__main__':
    main()
   
