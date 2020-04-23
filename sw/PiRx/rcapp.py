#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# Name:        Remote Control Receiver for robots or models
# Purpose:     Receiving remote control commands, controlling 
#              servos, H-bridges and digital outputs using a PCA9685 board     
# Author:      Bernd Hinze
#
# Created:     30.01.2020
# Copyright:   (c) Bernd Hinze 2020
# Licence:     MIT see https://opensource.org/licenses/MIT
# -----------------------------------------------------------------------------
import netifaces as ni
import socket
from time import time, sleep
from os import system
import queue
from threading import Thread
import pca9685 as PWM         # PWM Board Package
import ads1115 as ads         # pca9685 has to be allready loaded
import rccfg 

# queue that is used for communication between the observer thread -reading 
# sensor data and the UDP-Client class that transmits the data 
# to the transmitter 
q_time = queue.LifoQueue(20)
q_Udp_to_OBS = queue.Queue(20)
 
def get_ip_address(ifname):
    try:
        return ni.ifaddresses(ifname)[ni.AF_INET][0]['addr']
    except:
        return "127.0.0.0"
         
def get_bc_address(ifname):
    ip = get_ip_address(ifname).split('.')
    bcip = ip[0] + '.' + ip[1] + '.' + ip[2] + '.' + '255'
    return bcip

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
               
# Elements of of configuration
MODE, CENTER, RATE, REVERSE, ACCFILT, FAILSAFE, STEPW, CENTER_TR = range(8) 
LASTVAL = 0  # index for Globdata[chan][LASTVAL]
# Configuration for each channel with following cells
#  MODE, CENTER, RATE, REVERSE, ACCFILT, FAILSAFE, STEPW, CENTER_TR
Conf = [] 
#Globdata with the default center position 
GlobData = []
# table for inputs to be reversed 
revVal = []
imp_tab = []   
lockup = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
                       ":", ";", "<", "=", ">", "?"]
    
def CtrData_init():
    '''Init the Globdata with the default center position 
    Filling the channel impulse tab   
    '''
    global Conf, GlobData, revVal, imp_tab
    for  i in range (16):
        Conf.append([rccfg.SERVO, 1.5, 0.5, False, False, 127, 127, 1.5]) 
        GlobData.append([127]) 
    for i in range (255):
        revVal.append(254 - i) 
    for c in range (16):
            tab = [] 
            for i in range(255):                 
                tab.append(PcaVal(c, i))
            imp_tab.append(tab)
                
def PcaVal (chan, telval):
    """Calculates the puls value (0..4065) for the pca9685 module
    
    tval = message input 0..254
    [RATE] = maximal diviation (0..0.5) from the servo center puls duration 
    [CENTER_TR] = servo center puls duration with timm adjustment 
    [REVERSE] boolean for reverse operation
    """
    rate = Conf[chan][RATE]
    center = Conf[chan][CENTER_TR] 
    servoVal = telval
    if Conf[chan][REVERSE]:
        servoVal = revVal[telval]
    ival = 2 *  rate * servoVal / 254.0  + center - rate
    pval =  ival * rccfg.FREQ / 1000 * PWM.MAX_I_P9685
    return int(round(pval, 0))
   
def PcaHVal(chan, telval):
    IN1 = chan + 1
    IN2 = chan + 2
    """Calculates the puls value (0..4065) for the pca9685 module    
    tval = message input 0..254
    """
    cntimpuls = round(abs(telval-127)*32.008)
    PWM.set_pwm(chan, 0, cntimpuls)
    #print ("H " , cntimpuls)    
    if (telval < 127):          
        PWM.set_dio(IN1, 0)
        PWM.set_dio(IN2, 1)  
    elif (telval > 127):
        PWM.set_dio(IN1, 1)
        PWM.set_dio(IN2, 0)  
    else: 
        PWM.set_dio(IN1, 0)
        PWM.set_dio(IN2, 0)
                       
def configure_channel(mod, chan,  center, rate, reverse=False, \
                    accfilt=False, failsafe=127, stepw = 127): 
    global Conf, GlobData, imp_tab
    trimmctr = center
    Conf[chan] = [mod, center, rate, reverse, accfilt, failsafe, stepw, trimmctr]
    GlobData[chan] = [failsafe] 
    if (mod == rccfg.L298):
        for i in range (255):
            imp_tab[chan][i] = round(abs(i-127)*PWM.MAX_I_P9685/127)
    else:
        for i in range(255):                 
            imp_tab[chan][i] = PcaVal(chan, i)        

first = False

def acc_filter(chan, inp): 
    """ Decrease the input rise rate for an channel"""
    global GlobData, first
    da = Conf[chan][STEPW]
    centerpos = Conf[chan][FAILSAFE]
    def clamp(n, minn, maxn):
        if n < minn:
            return minn
        elif n > maxn:
            return maxn
        else:
            return n
    an = GlobData[chan][LASTVAL]
    if first: 
        an = inp
        first = False
    if ((inp > centerpos) and (inp > (an + da))): 
        cout = an + da   
    elif ((inp < centerpos) and (inp < (an - da))): 
        cout = an - da  
    else:
        cout = inp     
    GlobData[chan][LASTVAL] = clamp(cout, 0, 254)
    return GlobData[chan][LASTVAL]    
        
def update_PWM(chan, telval):
    """Calls the pwm driver and sets the impuls rate for a channel """
    mode = Conf[chan][MODE]
    if Conf[chan][ACCFILT]:
        telval = acc_filter(chan, telval)            
    if (mode == rccfg.SERVO):
        PWM.set_pwm(chan, 0, imp_tab[chan][telval])       
    elif (mode == rccfg.DIO):
        PWM.set_dio(chan, telval)
    elif (mode == rccfg.L298):    
        PcaHVal (chan, telval)                
        
def fail_safe():
    '''Set all actuators to the fail safe position '''
    for i in range(16):
        update_PWM(i, Conf[i][FAILSAFE])           
        
def trimm_Chan(chan, trimm):  
    """Change the trimm value of a channel in the Cfg table
    trim = 0..50
    """ 
    global Conf, imp_tab
    center = Conf[chan][CENTER]
    if Conf[chan][REVERSE]:
        trimm = 50 - trimm
    Conf[chan][CENTER_TR] = round(((center * (trimm - 25)/254) + center),3)
    for i in range(255):                 
        imp_tab[chan][i] = PcaVal(chan, i)

def shutdown_rx(chan, telval):
    """Shutdown the system """
    if (telval == 0):
        fail_safe()
        sleep(1)
        print ("Shutdown")
        if (not rccfg.SIM):
            system("sudo shutdown now") 

def update(msg):  
    """ Interface for the UDP-client 

    hdr = 100 : update_app | hdr = 127 : trimming |hdr = 255 : servo values            
    """
    # forward the current time to the observer queue
    if not q_time.full(): 
        q_time.put(time(), block=False)
    cntloop = len(msg)//3
    i = 0
    for i in range(cntloop):
        y = i*3
        hdr = msg[y]
        if (hdr == 255):
            update_PWM(msg[y+1], msg[y+2])
        else:
            if (hdr == 127):
                trimm_Chan(msg[y+1], msg[y+2])
            elif (hdr == 100):
                shutdown_rx(msg[y+1], msg[y+2])                
                
def Observer_loop():  
    print("Observer running")
    sensetime = time()
    sleep(5.0)
    aval = str(rccfg.AVAL)
    bc_data = tel_tx()
    port_tx = rccfg.port_tx   
    tx_address = (get_bc_address(rccfg.ifname), port_tx)
    observed_time= time()
    temp = time()
    
    while True:                    
        if (not q_time.empty()):
            observed_time = q_time.get()  # last time entry
        while (not q_time.empty()):
            temp = q_time.get()  
        if (not q_Udp_to_OBS.empty()):
            ID, ip = q_Udp_to_OBS.get()
            if (ID == 2) :
                tx_address = (ip, port_tx)
                #print ("TX IP", ip) 
                
        if ((time() - observed_time) > 1.5):
            fail_safe()
            #print('Timeout -> Fail Save')
 
        # sensor telegram            
        if (((time() - sensetime) > 2.0)): 
            aval = str(rccfg.AVAL)
            if rccfg.ADS:
                aval = ads.read_adc()
                aval = str(ads.convert_to_V(aval, ads.EXGAIN))
            databc = (bc_data + strfltotel(aval) + chr(13)).encode('utf-8')
            try:
                if sock.sendto(databc, tx_address) == 0: 
                    print('No data sent')
            except:
                print ("Network not available")
            sensetime = time()                        
        sleep(0.2)      
            
def decode_Tel(strtel):
    '''Decodes the incommimg control telegram and fills an array '''
    l = len(strtel)
    maxi = int(l / 2) - 2
    tel = [0] * maxi
    if (((ord(strtel[1])-48)*16 + (ord(strtel[2])-48)) == 2):
        for i in range (maxi):
            ti = i*2 + 3
            tel[i] = (ord(strtel[ti])-48)*16 + (ord(strtel[ti + 1])-48)
    return tel 

def tel_tx():
    """Creates the string coded telegram including the owne IP
    for transmitting back to the transmitter
    """
    tel = ""
    ip = get_ip_address(rccfg.ifname).split('.')    
    tel = chr(2) + "01"
    for i in range (len(ip)):
        tel = tel + bytostr(int(ip[i]))
    return tel  

def strfltotel(sense):
    '''Converts a string float value into coded string
    '''
    senli = (sense).split('.')
    tel = bytostr(int(senli[0])) + bytostr(int(senli[1]))
    return tel

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1) 

def UDP_run():  
    print ("Start UDP ")
    sock.bind(('', rccfg.port_rx))  
    Tel_ID, ip = range(2)
    UDOtoOBS = [0, ""]
    quetime = time()
    while True:
        data, address = sock.recvfrom(1024)       
        data = data.decode('utf-8')
        if data:
            if (strtobyte(data[1:3]) == 2): 
                UDOtoOBS[Tel_ID] = 2
                UDOtoOBS[ip] = address[0]
            # deliver the Tx ip to the Observer Loop
            if (((time() - quetime) > 2.0)): 
                if not q_Udp_to_OBS.full():
                    q_Udp_to_OBS.put(UDOtoOBS, block=False)   
                else:
                    print("UDP2OBS que full")
                quetime = time()
            try:
                msg = decode_Tel(data) 
                #print (msg)
                update(msg)
            except:
                msg = []                                      
                    
def main():   
    while (get_ip_address(rccfg.ifname) == "127.0.0.0"):
        print ("waiting for networking")
        sleep(1)                   
    CtrData_init()
    # init hardware boards
    PWM.init()
    PWM.set_pwm_freq(rccfg.FREQ)
    if rccfg.ADS:
        ads.init()
    # setting the configuration data for the selected model
    for data in rccfg.models[rccfg.MODEL]:
        configure_channel(data[0],data[1],data[2],data[3],\
                       data[4],data[5],data[6],data[7])
        
    fail_safe()   
    Thread(target = Observer_loop).start()
    UDP_run()
  
if __name__ == '__main__':
    main()
