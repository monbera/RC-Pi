# RC-Pi Funkfernsteuerung für Modellbau
Die Software 'TelDaControl' <https://github.com/monbera/TelDaControl>, wurde grundlegend überarbeitet und um einen optionalen Gamepad Controller erweitert. Die wesentlichen Änderungen sind:

  *  vereinfachte Kodierung des Telegramms (Performance - Faktor 10).
 Nicht kompatible zu 'TelDaControl'!
  *  Vermeidung objektorientierter Programmierung (Performance)
  *  vereinfachte Konfiguration
  *  Steuerung via Gamepad
  *  Rückkanal zur Übertragung der Batteriespannung oder anderer
analoger Daten des Empfängers

Das System besteht aus folgenden Komponenten:

  * **GamepadTx** (GPapp.py, GPcfg.py) [./sw/GamepadTx](./sw/GamepadTx)
    * Raspberry Pi wandelt die Ausgaben eines Gamepads (USB) in kompatible UDP Telegramme um. Die internen Zustände des Gamepads lassen sich mit einer Smartphone App visualisieren. 
  * **GPSCreen** (GPScreen.pde) [./sw/GPScreen](./sw/GPScreen)
    * Diese Smartphone App empfängt UDP-Telegramme vom GampadTx und visualisiert 
interne Zustände.
  * **PhoneTx** (PhoneTx.pde, Config.pde) [./sw/PhoneTx](./sw/PhoneTx)
    * vergleichbar mit 'TelDaControl', zusätzliche Statusanzeigen
  * **PiRx** (ads1115.py, pca9685.py, rcapp.py, rccfg.py) [./sw/PiRx](./sw/PiRx)
    * Fernsteuerempfänger bestehend aus einem Raspberry Pi, einem PWM-Board und optional einem ADC (ADS1115).

Eine etwas detailliertere Anleitung ist im Verzeichnis [./doc](./doc) zu finden. 

Direkte Fragen zur Software werden unter monbera[at]posteo.de beantwortet.
Allgemeine Fragen zum Raspberry Pi und zur Installation nicht, da ausreichend Tutorials 
im Netz verfügbar sind.

Konfigurationsmöglichkeiten:

| Empfänger | Sender | Remote Screen | Hotspot | Entfernung|
|:--:|:-----:|:----:|:----:|:----:|
| PiRx|PhoneTx| --|  PhoneTx | ca. 25 m |
| PiRx|PhoneTx| --|  Router mit ext. Ant. | ca. 100 m |
| PiRx|GamepadTx| GPScreen| GPScreen | ca. 25 m |
| PiRx|GamepadTX| [GPScreen]|  Router mit ext. Ant. | ca. 100 m |

Bei Verwendung eines Raspberry Pi mit externem Wifi-Modul, das eine externe Antenne nutzt, kann mit dem Router eine Reichweite von bis zu 400 m erreicht werden. 


# RC-Pi Radio Remote Control for Model Making
The software 'TelDaControl' <https://github.com/monbera/TelDaControl>, has been fundamentally revised and extended by an optional gamepad controller. The main changes are:
 

  * Simplified coding of the telegram (performance - factor 10). Not compatible to 'TelDaControl'!
  * Avoidance of object-oriented programming (performance)
  * Simplified configuration
  * Control via gamepad
  * Return channel for transmitting the battery voltage or other analogue data of the receiver

The system consists of the following components:

  *  **GamepadTx** (GPapp.py, GPcfg.py) [./sw/GamepadTx](./sw/GamepadTx)
    * Raspberry Pi converts the output of a gamepad (USB) into compatible UDP telegrams. The internal states of the gamepad can be visualized with a smartphone app. 
  * **GPSCreen** (GPScreen.pde) [./sw/GPScreen](./sw/GPScreen)
    * This smartphone app receives UDP telegrams from the GampadTx and visualizes 
internal states.
  * **PhoneTx** (PhoneTx.pde, Config.pde) [./sw/PhoneTx](./sw/PhoneTx)
    * comparable with 'TelDaControl', additional status displays
  * **PiRx** (ads1115.py, pca9685.py, rcapp.py, rccfg.py) [./sw/PiRx](./sw/PiRx)
    * Remote control receiver consisting of a Raspberry Pi, a PWM board and optionally an ADC (ADS1115).
A slightly more detailed guide can be found in the [./doc](./doc) directory.

Direct questions about the software are answered at monbera[at]posteo.de.
General questions about Raspberry Pi and the installation are not answered, because there are enough tutorialsare available on the network.

Configuration options:

| Receiver | Sender | Remote Screen | Hotspot | Distance|
|:--:|:-----:|:----:|:----:|:----:|
| PiRx|PhoneTx| --| PhoneTx || about 25 meters ||
| PiRx|PhoneTx| --| Router with ext. ant. | about 100 m |
| PiRx|GamepadTx| GPScreen| GPScreen | about 25 m |
| PiRx|GamepadTX| [GPScreen]| Router with ext. ant. | about 100 m |

When using a Raspberry Pi with an external Wifi module using an external antenna, a router can achieve a range of up to 400m. 

Translated with www.DeepL.com/Translator (free version)

