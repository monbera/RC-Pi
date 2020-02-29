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
q = queue.LifoQueue(100)
q_sense = queue.LifoQueue(20)
 
def get_ip_address(ifname):
    try:
        return ni.ifaddresses(ifname)[ni.AF_INET][0]['addr']
    except:
        return "127.0.0.0"
         
def get_bc_address(ifname):
    ip = get_ip_address(ifname).split('.')
    bcip = ip[0] + '.' + ip[1] + '.' + ip[2] + '.' + '255'
    return bcip
               
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
    
def CtrData_init():
    global Conf, GlobData, revVal, imp_tab
    for  i in range (16):
        Conf.append([rccfg.SERVO, 1.5, 0.5, False, False, 127, 127, 1.5]) 
        # init the Globdata with the default center position 
        GlobData.append([127]) 
    for i in range (255):
        revVal.append(254 - i)
    #filling the channel impulse tab   
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
    if not q.full(): 
        q.put(time(), block=False)
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
    sensetime = time()
    sleep(5.0)
    print("Observer running")
    observed_time= time()
    temp = time()
    while True:                    
        if (not q.empty()):
            observed_time = q.get()  # last time entry
        while (not q.empty()):
            temp = q.get()                   
        if ((time() - observed_time) > 1.5):
            fail_safe()
            print('Timeout -> Fail Save')

        # sensor telegram         
        if (((time() - sensetime) > 2.0) and rccfg.ADS):
            aval = ads.read_adc()
            aval = str(ads.convert_to_V(aval, ads.EXGAIN))
            # write the coded values to the queue
            if (not q_sense.full()): 
                q_sense.put([aval], block=False)
            sensetime = time()                        
        sleep(0.2)      
            
def decode_Tel(strtel):
    tel = strtel.split(',')
    tel.pop()
    for i in range(len(tel)):
        tel[i] = int(tel[i])
    return tel      

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1) 

def UDP_run():  
    port_tx = rccfg.port_tx
    aval = rccfg.AVAL
    bcTime = time()
    sent = 0
    tmp =''     
    tx_address = (get_bc_address(rccfg.ifname), rccfg.port_tx)
    print ("Start UDP")
    bc_data = (rccfg.ID + '@' + get_ip_address(rccfg.ifname)).encode('utf-8')   
    sock.bind(('', rccfg.port_rx))    
    for i in range(10):
         sent = sock.sendto(bc_data + \
             ("@" + aval).encode('utf-8'), tx_address)  
         sleep(0.1)
    
    while True:
        if ((time() - bcTime) > 1.0):
            bcTime = time()
            if (not q_sense.empty()):
                a = q_sense.get()
                aval = a[0]  # last analog value                      
            while (not q_sense.empty()):
                tmp = q_sense.get()
            try: 
                pass
                databc = (bc_data + ("@" + aval).encode('utf-8')) 
                if sock.sendto(databc, tx_address) == 0: 
                    print('No data sent')                        
            except:
                print ("Network not available")
                
        data, address = sock.recvfrom(1024)
        data = data.decode('utf-8')
        if data:
            try:
                msg = decode_Tel(data)
                # use the real address of transmitter 
                tx_address = (address[0], port_tx)
                print (msg , 'to', tx_address)
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
