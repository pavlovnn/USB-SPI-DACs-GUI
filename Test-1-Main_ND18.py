# Controller for ND18,  2016, Copyright by Ndevices LLC
# 26 SEPT 2016 

# CONSTANTS:
TABOUT='''
         18 channel SiPm bias controller ND18  based on  libFTDI driver  \n\n
                                 Ndevices Ltd.  Ireland,2016  \n\n
                                   http:\\\www.ndevices.ie                  '''

dt = "ND18: Enter Voltages in Volts"
st ="ND18: Saving to EEPROM..."

NOFTDI = ''' No FTDI chip found!! '''

# Channels
NCH=1 

#Default Volts
DEFV=70

#vmax max voltage ta 0x3FF potmeter
VMAX=72.13

#VMIN min voltage at 0X000 potmeter
VMIN=66.72


# LIMITS for  GUI

#VMAXCLIP
VMAXCLIP = 71.1

#VMINCLIP
VMINCLIP = 66.9


# POT resolution =10 bits
DISC = 1023.4

#COMMANDS, some not used

COM_WRITE_DAC = 0b1011<<20
COM_DAC_TO_EE = 0b0010<<20

COM_RESTORE_EE_DAC = 0xb0001<<20
COM_NOP = 0xb0000<<20

COM_WRITE_EE = 0b0010<<20
COM_READ_EE = 0b1001<<20
COM_READ_DAC = 0b1010<<20

TESTWORD = 0x00f123 # TEST 24 bit word for SPI loopback

#PORT pins on UM245R
# 0..7
# CLK DB4 on UM245R was DB0, 0x01 
CLK = 0x10

#Dwrite DB1 DATA 
DWRITE = 0x02

#CS DB2
CS = 0x04

#DREAD DB7
DREAD=0x80

from Tkinter import *
import tkFileDialog
import tkMessageBox
import time
import ast
import sys
from pylibftdi import BitBangDevice


# FTDI USB port routines

def initport():
    with BitBangDevice() as bb:
        bb.direction = (~ DREAD)&0xFF 
        bb.port = 0xFF  

# Routines to handle a chain of ad5231

# Word level function

def voltword(vs,command): # Volts to 24-bit words
        w =  int (round ((DISC*(vs-VMIN)/(VMAX-VMIN))))
        w =  0x0003FF & w     # 10 bit mask for the value
        wt =  w | command
        return wt

# Bit stream routines

def bitar(word24):# word of 24 bits to bit array
        data=[]
        for n in range (23,-1,-1):
                data.append( 0x01 & (word24>>n))
        #print(data)
        return data

def re_bitar(rbar ): #bitraay to 24-bit word for reaadback
        rb =0x000000
        for n in xrange (len(rbar)):
                rb = (rb << 1) & 0xFFFFFF  
                if (rbar [n] >0):
                    rb = rb | 0x000001                   
        #print("ret array, ret word TESTWORD ",rbar,rb,TESTWORD)
        return rb

def dusb(vt,command): # prepares data for USB SPI daisy chain
        datal=[]
        datal.extend( bitar(TESTWORD)) # SPI loopback extra woard
        
        for k in reversed(xrange(len(vt))):
                word24 = voltword(vt[k],command)
                datal.extend(bitar(word24))
        return datal

def clkd (vt,command): # Clock the whole chain
        rback = []
        datal = dusb(vt,command)
        print("bb")        
        with BitBangDevice() as bb:
                bb.direction = (~ DREAD)&0xFF 
                bb.port = 0xFF  

                #chip_s("active")
                bb.port = (~CS) & 0xFF

                for k in xrange(len(datal)):
                    if (datal[k] ==0)   :
                        bb.port = 0xFF & (~CS ) & (~CLK) & (~DWRITE) # send 0 bit
                        bb.port = 0xFF & (~CS )  & (~DWRITE) # send CLK
                    else :
                        bb.port = 0xFF & (~CS ) & (~CLK)  # send 1 bit
                        bb.port = 0xFF & (~CS )  # send CLK

                    rr = bb.port
                    if (rr & DREAD > 0) :
                        rback.append(0x01)
                    else :
                        rback.append(0x00)

                bb.port = 0xFF    #chip_s("inactive")
                
                if (re_bitar(rback) == TESTWORD):
                    return "LOOPBACK OK"
                else:               
                    return "USB OK"
        
#Functions

def ok_box(status="OK"): # Loopback status indicator box
        #print("ok box ", status)
        if (status == "USB OK") :
                color = "yellow"
        elif (status == "LOOPBACK OK"):
                color = "green"
        else:
                color = "red"
        Label(root, text ="  STATUS:").grid(column=3,row=16)
        sta = Entry(root, width=20,bg=color)
        sta.grid(column=4,row=16)
        sta.insert(END,status)       
    
def clip_form(vt): # clip values to max/min voltage 
        for k in xrange(len(vt)):
                if vt[k]>VMAXCLIP:
                        vt[k]=VMAXCLIP
                if vt[k]<VMINCLIP:
                        vt[k]=VMINCLIP
        return vt

def read_form(vt): #Read from numeric control boxes
        for k in xrange(len(vt)):
                vt[k] = float(e[k].get())
        update_form(vt)
        return vt

def update_form(vt): # Update numeric control boxes 
        vt = clip_form(vt)
        for k in xrange(len(vt)): 
            e[k].delete(0, END) 
            e[k].insert(END,"%6.3f" %vt[k])
        print("update_form")
        
def reset_form(vt,defb): # Reset to the leading box
        defv = float(defb.get())
        for k in xrange(len(vt)):
            vt[k] = defv
        update_form(vt)
        print("reset_form")
        
def save_ee(vt): # Save to eeprom !!- ad5231
        print("\n save_ee ")
        root.title(st)
        root.update()
        read_form(vt)
        try:
                clkd(vt,COM_WRITE_DAC)#clock data DAC first
                status = clkd(vt,COM_WRITE_EE)#transfer datat= to EEPROM
        except:
                status = "USB problem"
        ok_box(status)
        time.sleep(1.0)
        root.title(dt)
        root.update()

def readf(vt): # Read from file
        print("\n read file")
        file_path_string = tkFileDialog.askopenfilename(parent=root)
        mfile =open(file_path_string,"r+")
        v = mfile.read()
        v = ast.literal_eval(v)
        print "v= ",v
        update_form(v)       
        mfile.close()
        vt = read_form(vt)
        return v
        
def savef(vt):# Save to file
        print("\n save file")
        read_form(vt)
        file_path_string = tkFileDialog.asksaveasfilename(parent=root)
        mfile =open(file_path_string,"w+")
        print >> mfile, vt
        mfile.close()
       
def send_ram(vt): # Send to RAM !!- ad5231
        print("\n send_ram ")
        read_form(vt)
        try:
            status = clkd(vt,COM_WRITE_DAC)#clock data
        except:
            status = "USB problem"
        ok_box(status)

def about_menu():# About software
        tkMessageBox.showinfo(title = "About",message = TABOUT)
        
# MAIN:

# Initiliaze voltage form boxes to 0
v= []
for k in range (0,NCH):
    v.append(0)
    v[k] =0


# initilaze leading box to default 70V    
defv = DEFV

# Start main form
root = Tk()
root.title(dt)

try:
        initport()
except:
        tkMessageBox.showinfo(title = "No USB connection found",message = NOFTDI)
         


# 18 channel boxes drawn
e =[]
for k in range (0,NCH):
    Label(root, text="%2d" %(k+1)).grid(column=0,row=k)
    e.append( Entry(root, width=7))
    e[k].grid(column=1,row=k)
    e[k].insert(END,"%6.3f" %v[k])
    
#default common value box
Label(root, text ="  SET ALL TO:").grid(column=2,row=0)
defb = Entry(root, width=7)
defb.grid(column=3,row=0)
defb.insert(END,"%6.3f" %defv)
# List max, min
maxmintext ="MIN=%6.3f MAX=%6.3f" %( VMINCLIP, VMAXCLIP)
Label(root, fg="blue",text = maxmintext).grid(column=3,row=1)
 

#buttons   

Button(root, text='SET TO ALL BOXEX', width=25, command=lambda : reset_form(v,defb)).grid(column=4,row=0)
Button(root, text='SEND TO RAM', width=25, command=lambda : send_ram(v)).grid(column=4,row=4)
Button(root, text='SAVE TO EEPROM', bg= "orange",width=25, command=lambda : save_ee(v)).grid(column=4,row=6)
Button(root, text='READ FROM FILE',width=25, command=lambda: readf(v)).grid(column=4,row=8)
Button(root, text='SAVE TO FILE',width=25,command=lambda: savef(v)).grid(column=4,row=10)
Button(root, text='EXIT', fg= "blue",width=25, command=root.destroy).grid(column=4,row=14)
Button(root, text='ABOUT', fg= "brown",width=25,command=lambda: about_menu()).grid(column=4,row=12)

root.mainloop()


