import matplotlib.pyplot as plt
import numpy as np
from func import *

fn = "fiveAxisOverhang.gcode"

brimsize = 5.0

lengthB = 55.33
towerheight = 20
nozzlesize = 0.4
overhanglenght = 50.0
trackwidth = 0.5
layerheight = 0.2
angle = 0

extrusionfactor = (trackwidth * layerheight)/ (0.25*np.pi*1.75**2)*1.05
overlap = 0.15
blocksize = 20.0
xoffset = 3*brimsize
yoffset = 90.0-0.5*blocksize
bedoffset = 0.1
#brimgeneration
brimarr = np.linspace(brimsize, 0, int(brimsize/trackwidth))

fiveAxispreGcode = """"
\nM18 S0; disables steppers timeout
G0 A0 B0; moves a and b steppers to the right position

"""

preamble = """
; Start sequence
M220 S100 ;Reset Feedrate
M221 S100 ;Reset Flowrate
 
M104 S210 ;Set final nozzle temp
M190 S60 ;Set and wait for bed temp to stabilize
 
G28 X ;Home X to prevent cable blocking Z homing
G28 ;Home all axes
G91 ;Relative positioning
G0 Z-20 F3000 ;Move Z down 20mm from top for bowden tube alignment
G90 ;Absolute positioning
G0 A0.000 B0 F3000 ;Move rotation axes to 0
 
; Purge line (at original coordinates before centering)
G92 E0 ;Reset Extruder
; A-axis optimized for shortest rotation path (slipring mode)
G1 Z2.0 F3000 ;Move Z Axis up
G1 X-2 Y20 Z0.28 F600 ;Move to start position slowly
M109 S210 ;Wait for nozzle temp to stabilize
G1 X-2 Y145.0 Z0.28 F1500.0 E15 ;Draw the first line
G1 X-1.7 Y145.0 Z0.28 F5000.0 ;Move to side a little
G1 X-1.7 Y20 Z0.28 F1500.0 E30 ;Draw the second line
G92 E0 ;Reset Extruder
G1 E-1.0000 F1800 ;Retract a bit
G1 Z2.0 F3000 ;Move Z Axis up
G1 E0.0000 F1800
 
; Post-homing positioning
G0 X100 Y100 F1800 ;Move to center
G92 X100 Y100 A0 B0 ;Set bed center as origin (0,0) and reset rotation axes
M211 S0 ;Disable software endstops (required for A-axis optimization with negative values)
 
M83 ; Use relative extrusion
 
"""
with open(fn,"w") as f:
    f.write(preamble)
    f.write(fiveAxispreGcode)
# Brim
for brimpos in brimarr:
    move(x=xoffset-brimpos,y=yoffset-brimpos,z=bedoffset,a=0,b=0,fileName=fn)
    extrude(x=xoffset+blocksize+brimpos,E=extrusionfactor*(blocksize+2*brimpos),a=0,b=0,fileName=fn)
    extrude(y=yoffset+blocksize+brimpos,E=extrusionfactor*(blocksize+2*brimpos),a=0,b=0,fileName=fn)
    extrude(x=xoffset-brimpos,E=extrusionfactor*(blocksize+2*brimpos),a=0,b=0,fileName=fn)
    extrude(y=yoffset-brimpos,E=extrusionfactor*(blocksize+2*brimpos),a=0,b=0,fileName=fn)

towerarr = np.linspace(bedoffset,towerheight,int((towerheight-bedoffset)/layerheight))
#Tower
for towerpos in towerarr:
    move(x=xoffset,y=yoffset,z=towerpos,a=0,b=0,fileName=fn)
    extrude(x=xoffset+blocksize,E=blocksize*extrusionfactor,F=500,a=0,b=0,fileName=fn)
    extrude(y=yoffset+blocksize, E=extrusionfactor*blocksize,F=500,a=0,b=0,fileName=fn)
    extrude(x=xoffset,E=extrusionfactor*blocksize,a=0,b=0,F=500,fileName=fn)
    extrude(y=yoffset, E=extrusionfactor*blocksize,a=0,b=0,F=500,fileName=fn)


#move A and B axis to the right position
with open(fn,"a") as f:
    f.write(f"\nG0 X{xoffset+blocksize+lengthB*np.sin(angle/360*2*np.pi)+10};move the nozzle out of the way")
    f.write(f"\nG0 A0 B{angle};rotate b arm to vertical")
    f.write(f"\nG0 Z{towerheight-(1-np.cos(angle/360*2*np.pi))*lengthB+0.1}")
    f.write(f"\nG0 X{xoffset+blocksize+lengthB*np.sin(angle/360*2*np.pi)}")

# overhang


comment("LAYER_CHANGE",fn)
comment("---------start overhang------------",fn)

E_factor=(0.15)/(0.25*np.pi*1.75**2)*1.05
posOverhang=0
a=0
Ex=E_factor*blocksize
xstart = xoffset+lengthB*np.sin(angle/360*2*np.pi)
move(x=xstart,y=yoffset,fileName=fn)
while posOverhang<overhanglenght:
    posOverhang+=(1-overlap)*nozzlesize
    move(x=xstart+posOverhang,fileName=fn)
    
    extrude(y= yoffset+blocksize,E= Ex,F=180,fileName=fn)
    posOverhang+=(1-overlap)*nozzlesize
    move(x=xstart+posOverhang,fileName=fn)
    extrude(y=yoffset,E=Ex,F=200,fileName=fn)


