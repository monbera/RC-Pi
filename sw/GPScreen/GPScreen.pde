/*-------------------------------------------------------------------------------
 Name:        GPSreen (remote controlled screen by the rpi of the gamepad controller 
 Purpose:     Visualisation of internal states of the Gamepad   
              The code is the same for PC and Android    
 Author:      Bernd Hinze
 
 Created:     30.01.2020
 Copyright:   (c) Bernd Hinze 2020
 Licence:     MIT see https://opensource.org/licenses/MIT
 ------------------------------------------------------------------------------
 */
import hypermedia.net.*;
UDP udp;

Indicator IRC;
Indicator IGP; 
SensVal Voltage;
ChannelIndicator CHT;
ChannelIndicator CHS;
TrimmL TST;

PFont F;

boolean ip_received = false;
int ms_received_tout = 10 * 1000; // 10s
int ms_received = millis();
int ms_sent = millis();
int com_stat_gp = 0;
String ip       = "_._._._";  // the remote IP address

int port        = 6000;    // the destination port
int GPdataLen = 7 ;        // splitted lengt comma separatet 
String V_Sensor = "0.00";   
String rcip     = "_._._._";

/* Telegram to the RSCreen (Remote SCREEN) strings, seperated by "," 

  V[0] = HDR (255)  
  V[1] = Dual Rate Channel Speed
  V[2] = Trimm Channel 0
  V[3] = Value Channel 0
  V[4] = Dual Rate Channel Steering
  V[5] = Trimm Channel Steering
  V[6] = Com Status RC (0 = default, 1 connect, 2 = lost) 
  ----------------Data of the receiver, forwarded to the Remote SCREEN-----
  V[7] = Voltage of RC accu nn.nn
  V[8] = IP of the receiver
*/
int [] GPdata = new int [GPdataLen];

void setup()
{
  //size(800,400);
  fullScreen();
  orientation(LANDSCAPE); 
  background (#353250);
  F = createFont("Arial", 14, true); 
  rectMode(CENTER);
  textAlign(LEFT);
  textSize(int(height * 0.08));
  stroke(#FFFFFF);
  GPdata [1] = 100;
  GPdata [2] = 25;
  GPdata [4] = 100;
  GPdata [5] = 25;  // setting the default position of trimming to center

  IRC  = new Indicator(0.085, "RC");
  IGP  = new Indicator(0.18, "GP");
  Voltage = new SensVal(0.9, 0.13);
  CHT = new ChannelIndicator(0.32, 25, "TH", "0");
  CHS = new ChannelIndicator(0.52, 25, "ST", "3");
  TST = new TrimmL(0.7, 0.5);
  /* 
  RCR: RC Receiver Rpi
  GP: Gamepad Rpi 
  RSC: Remote Screen (this one)
  Communication diagram
  1. RCR (IP) --->   6000 (GP_rpi)
  2. RCR 6100 <----  GP_Rpi Cyclic Command Telegrams (0.02s)
  3.                 GP_Rpi Cyclic Status Telegrams (0.2s) ---> 5100 RSC 
  4.                 GP_Rpi 6000                            <--- RSC Cyclic Telegrams (1s)
  */
  udp = new UDP (this, 5000);
  udp.listen( true ); 
}

void draw() 
{ 
  background (#353250);
  raster();
  IRC.display(GPdata[6], rcip);  
  IGP.display(com_stat_gp, ip);
  CHT.display(GPdata[1]);
  CHS.display(GPdata[4]);
  TST.display(GPdata[5]);
  //Voltage.display(str(GPdata[7]) + str(GPdata[8]));
  Voltage.display(V_Sensor);
  if (ip_received)   // ip valid Gamepad
  { 
    try {
      if ((millis() - ms_sent) > 1000) {
        udp.send("RSC@0.0.0.0", ip, port);
        //println("RSC@0.0.0.0", ip, port);
        ms_sent = millis();
      }
    }
    catch (Exception e) {
    }
  }
  if ((millis() - ms_received) > (ms_received_tout)) { 
       com_stat_gp = 0;
       GPdata[6] = 0;  
  }
}

/* ----------------------------------------------------------------------------------
 Default method of the UDP library for listening. 
 ------------------------------------------------------------------------------------  
 */
void receive(byte[] data)
{  
  String message = new String(data); 
  String[] parts = split(message, "@");
  //println (message + "   " + (message.length()));
  // checking if BC IP or Data Telegramm
  //println(parts.length);
  if (parts.length == 2) {
    String[] ip_parts = split(parts[1], ".");
    // checking wether it is probably a IP adress
    if ((int(ip_parts[0])==192) && (int(ip_parts[1])==168))
    {      
      println (parts[0]);
      if ((parts[0].equals("GP") == true))
      { println ("IP received");
        ip = parts[1];
        ip_received = true;
        com_stat_gp = 1;
        ms_received = millis();
      }
    }
  } else {
       String[] screendata = split(message, ",");
       for (int i = 0; i < GPdataLen; i = i+1){
          GPdata[i] = int(screendata[i]);
       }
       V_Sensor = screendata[GPdataLen];
       rcip =  screendata[GPdataLen + 1];
       println (V_Sensor,  rcip);
       ms_received = millis();
       com_stat_gp = 1;
 }   
}

void seperatorLine(float x){
   line(width * x ,  height/5, width * x , height);
}

void raster(){
  int i;
  for (i = 1 ; i <= 4; i += 1){
    line (0.0, i * height / 5, width , i * height / 5);
  }
  line(0.0 , height / 10, width *2 /3 , height / 10);
  line(width *2 /3 , 0.0, width *2 /3 , height / 5);
  seperatorLine (0.15);
  seperatorLine (0.3);
  seperatorLine (0.53);
}

class SensVal
{
  int tx, ty, tSz;
  String val; 
  float volt;
  SensVal(float x, float y)
  { 
    // geometry
    tx = int (x * width);
    ty = int(y * height); 
    // text output
     
  }
  void display(String v){
    volt = float(v);
    //println (volt);
    if (volt == 0.0){
     val = "__.__ V";  
    }
    else{
     val = v + " V";
    }         
    fill(255);
    text(val, tx, ty);   
  }
}


class Indicator 
{
  int tx, ty, ex, ey, ed, state;
  String tID, tor, trd;
  boolean RecApp;   
  Indicator(float y, String t)
  { 
    state = 0;
    RecApp = true;
    // geometry
    ex = int(width * 0.6 );
    ey = int(height * (y - 0.0350));
    ed = int(height * 0.07);
    tx = int(width * 0.03);
    ty = int(height * (y + 0.0)); 
    // text output
    tID = t;    
  }

  void display(int cl, String ip) {
    textAlign(LEFT);
    noStroke();
    fill(#353250);    
    rect(ex - height* 0.25, ey, height* 0.5, ed, 0);
    stroke(#FFFFFF);   
    switch(cl)
    {
    case 0: 
      fill(#FF0000);   
      break;   
    case 1: 
      fill(#04C602);   //green
      break;  
    case 2: 
      fill(#FFF703);   //yellow
      break; 
    default: 
      fill(#FF0000);
      break; 
    }
    ellipse(ex, ey, ed, ed);
    fill(255);
    text(tID, tx, ty);   
    fill(255);
    text(ip, tx + width * 0.15, ty );   
  }
}


class ChannelIndicator 
{
  int tx1, tx2, tx3 ,txt ,ty, ex, ey, tval;
  String GPfunc, tnb, cha;
  //boolean RecApp;   
  ChannelIndicator(float y, int trimval, String kfunc, String kcha)
  { 
    
    GPfunc = kfunc;
    tval = trimval;
    cha = kcha;
    
    //ex = int(width * 0.0);
    //ey = int(height * y);
    tx1 = int(width * 0.03);
    tx2 = int(width * 0.17);
    tx3 = int(width * 0.32);
    txt = int(width * 0.6);
    ty = int(height * (y + 0.0));
  }
  
  void display(int dr) {
     text(GPfunc, tx1, ty ); 
     text("CH " + cha, tx2, ty ); 
     text("DR " + str(dr) + "%", tx3, ty ); 
  }
}


class TrimmL
{ 
  int x, y, wB, hB, val, hTr, pmin, pmax;
  int [] ValMap;
  TrimmL(float cx, float cy)
  {
  x = int (width * cx);
  y = int (height * cy); 
  wB = int(height * 0.5);
  hB = int(height * 0.1);
  pmin = x - wB/2;    
  pmax = x + wB/2;    
  // trimm indication
  hTr = int(height * 0.05);
  val = 25;
  //println("start", val);
  ValMap = new int [51];
  //println (pmin, pmax);
  adjustValMap(pmin, pmax);
  }
  
  void display(int val){
    textAlign(RIGHT);
    fill(0);
    rect(x, y, wB, hB, 0);
    //rect(x , y - hB * 1.5 , hB * 1.5, hB, 0);
    placeIndication(val);
    //println (val);
  }
  
  void placeIndication(int ival){
    fill(200);
    rect(ValMap[ival], y, hTr , hB, 0); 
    //textSize(int(height * 0.08));
    fill(255);
    text (str(ival - 25), x + (width *0.22), y + (height*0.02));
  }
  
  void adjustValMap(int tpmin, int tpmax) {   
    for (int i = 0; i <= 50; i++) { 
      ValMap [i] = round(map(i, 0, 50, tpmin + hTr/2, tpmax -hTr/2));
      //println( i, ValMap [i]);
    }
  }  
}
