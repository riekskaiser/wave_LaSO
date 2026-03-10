import matplotlib.pyplot as plt
from shapely.geometry import Point,LineString, Polygon
from shapely.affinity import rotate
import numpy as np
from func import *
from wavepathGeneration3 import *
tower_block = [(0,0),(20,0),(20,20),(0,20),(0,0)]# the block that makes the tower

seed_part = densify_curve([(0.01,0.01),(0.01,19.95)],0.1)# back edge of the tower

max_overhang_length = 50
number_of_prints = 1
print_difference = max_overhang_length/number_of_prints

for i in range(number_of_prints):
    overhang_bounds = [(0,0),(20+print_difference*(i+1),0),(20+print_difference*(i+1),20),(0,20),(0,0)]
    print(overhang_bounds)
    wavePathGeneration(bead_area=0.15,nozzle_size=0.4,layerheight_support=0.2,filament_diam=1.75,
                       flow_multiplier=1.05,ExType=f"Overhang_wave_{int(print_difference*(i+1))}_unsupported",
                       printer="Ender",angle=0,overlap=0.15,boundary=overhang_bounds,seed=seed_part,
                       x_offset=20,y_offset=80,support_pitch=50,support_pitch_across=50,exTemp=200,brimSize=20,height=10,supported=False,tower=tower_block,feedRate_brim=600,feedRate_supports=900)
    block = open(f"gcodes/Block{int(print_difference*(i+1))}X20X10Ender.gcode",'r')
    with open(f"gcodes/Overhang_wave_{int(print_difference*(i+1))}_unsupportedEnder.gcode",'a') as f:
        
        f.write(block.read())
    block.close()



