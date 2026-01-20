import matplotlib.pyplot as plt
from shapely.geometry import Point,LineString, Polygon
from shapely.affinity import rotate
import numpy as np
from func import *
from wavepathGeneration3 import *
import os

import datetime



def offset2gcode2(linewidth = 0.4,overlap = 0.125,boundary_curve = [(0, 0), (12, 0), (18, 6), (32, 12), (12, 12), (12, 20), (8, 16), (4, 16), (0, 20), (0, 12), (-20, 12), (-6, 6), (0, 0)]
                 ,seed_curve = [(40, 20),(55, 22.5), (70, 25)],Efactor = 0.05,F = 180,xoffset = 25.0,yoffset = 20.0,supportpitch = 10.0,extruderTemp = 200,center = (80,80)
                 ,angle = 45,layers= 2,baseHeight = 20.1+0.2,layerheight = 0.2,filename = "default.gcode"):
    stairlength = 3
    x_coord_support = []
    y_coord_support = []
    supportpitch_indexes = int(supportpitch/(linewidth*(1-overlap)))
    change_fanspeed(128,filename)
    previous_command = "move"
    set_extrusionTemp(extruderTemp,True,filename)
    boundary_curve = translate_seed(boundary_curve,xoffset,yoffset)
    boundary_curve = rotate_coord(coord_set=boundary_curve,center = center,angle=angle)
    seed_curve = translate_seed(seed_curve,xoffset,yoffset)
    seed_curve = rotate_coord(coord_set=seed_curve,center=center,angle=angle)
    # inputs 
    # - linewidth       width of the line               mm
    # - overlap         overlap of printed lines        %
    # - boundary_curve  boundary of the printed area    [x-coordinate array],[y-coorinate array] mm
    # - seed_curve      curve that generates overhangs  list of shapely points mm
    # - fileName        filepath of the .gcode file     string
    # - F               feedrate of the overhang        mm/min
    # --- define the r (radius of the offset circles) as the track offset --- 
    r = linewidth*(1-overlap)
    # --- define a minimum extruded length to prevent the printer from printing a line with a E value that rounds to 0
    E_min = 0.002
    min_length = max([0.05,E_min/Efactor])
    # --- First offset ---
    boundary_polygon = Polygon(boundary_curve) #generate a polygon of the boundary coordinates
    seed_curve = densify_curve(seed_curve,0.05)
    # --- Initial offset odd layers---
    bin1, bin2, shape = offsets(seed_curve, r/2) #offset of the seedcurve
    current_shape = shape.intersection(boundary_polygon) #offset of the seedcurve where it intersects with the boundary polygon
    # -- Bottom layer ---
    i = 0
    E_first = Efactor
    curr_extruded_length = 0
    xseam = []
    yseam = []
    while not current_shape.is_empty and i < 1000: #runs while the current wave is not empty
        
        name = f"lines/BottomLine{i}.gcode"
            
        with open(name,'w') as a:
            a.write("")
        
        coords = list(current_shape.exterior.coords)
        next_x, next_y, next_shape = offsets(coords, r=r)
        current_shape = next_shape.buffer(0.0001).intersection(boundary_polygon)

        

        
        if current_shape.is_empty|len(coords[0])<2:              #exits the loop if there is no more offsets to generate
            break
        
        if current_shape.geom_type == 'Polygon':
            x, y = current_shape.exterior.xy
            
            curr_supported_length = 0 #add a support every 10 mm
            
            # Write coordinates to G-code
            
            #determine if each point is on the boundary or not
            isOnBoundary = np.zeros(len(x[:]),dtype=bool)
            first_bound_index = 0
            first_bound_not_found = True
            for j in range(len(x[:])):
                xcurr =x[:][j]
                ycurr =y[:][j]
                
                if boundary_polygon.boundary.distance(Point(xcurr,ycurr))<1e-8:
                    isOnBoundary[j] = True
                    if first_bound_not_found:
                        first_bound_index = j
                        first_bound_not_found=False
            # make sure that the start of each line is on the boundary.
            if (np.sum(isOnBoundary==False))<1:
                break
            x = list(x[first_bound_index:])+list(x[:first_bound_index])
            y = list(y[first_bound_index:])+list(y[:first_bound_index])
            isOnBoundary = list(isOnBoundary[first_bound_index:])+list(isOnBoundary[:first_bound_index])
            xseam.append(x[0])
            yseam.append(y[0])
            retract(name)
            move(x=x[0],y=y[0],fileName=name)
            move(z=baseHeight,fileName=name)
            detract(name)
            if i%supportpitch_indexes==0:

                x_coord_support.append(x[0])
                y_coord_support.append(y[0])
            
            previous_command="move"
            
           
            plt.plot(x,y,"-r")
            # generating the gcode commands
            for j in range(1,len(x[:])-1):
                
                xcurr =x[:][j]
                xprev =x[:][j-1]
                yprev =y[:][j-1]
                ycurr =y[:][j]

               

                if isOnBoundary[j]and isOnBoundary[j-1]:
                    if not (isOnBoundary[j+1]): #if the point and the previous point is on the boundary, but the next point is not, move to this position to start printing
                        if previous_command != "move":
                            pass#retract(name)
                        retract(name)
                        move(x=xcurr,y=ycurr,fileName=name)
                        detract(name)
                        previous_command = "move"
                        curr_extruded_length = 0
                    else: #if the previous, current and next point are on the boundary curve, it can be ignored.
                        curr_extruded_length = 0
                #elif isOnBoundary[j]and not(isOnBoundary[j+1]):
                #    extrude(x=xcurr,y=ycurr,E=Efactor*curr_extruded_length,F=F,fileName=filename)
                #    curr_extruded_length = 0
                else:# if the previous and or current points are not on the boundary, it can be extruded
                    extrusionlength = np.sqrt((xcurr-xprev)**2+(ycurr-yprev)**2)
                    curr_extruded_length+=extrusionlength
                    if (curr_extruded_length>=min_length)|(j==len(x[:])-1):
                        if previous_command == "move":
                            pass#detract(name)
                        previous_command = "extrude"
                        extrude(x=xcurr,y=ycurr,E=Efactor*curr_extruded_length,F=F,fileName=name)
                        
                        
                        if i%supportpitch_indexes==0:
                            curr_supported_length+=curr_extruded_length
                            if curr_supported_length>supportpitch:
                                x_coord_support.append(xcurr)
                                y_coord_support.append(ycurr)
                                curr_supported_length=0
                        curr_extruded_length = 0
                        
                    
           
           
                  
            i += 1
            first_bound_not_found = True
    # --- innitialise index ----
    i = 0
    # --- Initial offset odd layers---
    bin1, bin2, shape = offsets(seed_curve, r/2) #offset of the seedcurve
    current_shape = shape.intersection(boundary_polygon) #offset of the seedcurve where it intersects with the boundary polygon
    curr_extruded_length = 0
    xseam = []
    yseam = []
    while not current_shape.is_empty and i < 2000: #runs while the current wave is not empty
        
        #Efactor = (layerheight*r)/(0.25*np.pi*1.75**2)*0.9
        Efactor = ((0.25*np.pi*layerheight**2+layerheight*(r-layerheight)))/(0.25*np.pi*1.75**2)
        if i%2==1:
            name = f"lines/EvenLine{int(i/2)}.gcode"
            
        else:
            name = f"lines/OddLine{int((i-1)/2)}.gcode"
            
        with open(name,'w') as a:
            a.write(f";{name}\n")

        coords = list(current_shape.exterior.coords)
        next_x, next_y, next_shape = offsets(coords, r=r/2)
        current_shape = next_shape.buffer(0.0001).intersection(boundary_polygon)

        

        
        
        
        if current_shape.geom_type == 'Polygon':
            x, y = current_shape.exterior.xy
            
            curr_supported_length = 0 #add a support every 10 mm
            
            # Write coordinates to G-code
            
            #determine if each point is on the boundary or not
            isOnBoundary = np.zeros(len(x[:]),dtype=bool)
            first_bound_index = 0
            first_bound_not_found = True
            for j in range(len(x[:])):
                xcurr =x[:][j]
                ycurr =y[:][j]
                
                if boundary_polygon.boundary.distance(Point(xcurr,ycurr))<1e-8:
                    isOnBoundary[j] = True
                    if first_bound_not_found:
                        first_bound_index = j
                        first_bound_not_found=False
            # make sure that the start of each line is on the boundary.
            if (np.sum(isOnBoundary==False))<1:
                break
            x = list(x[first_bound_index:])+list(x[:first_bound_index])
            y = list(y[first_bound_index:])+list(y[:first_bound_index])
            isOnBoundary = list(isOnBoundary[first_bound_index:])+list(isOnBoundary[:first_bound_index])
            xseam.append(x[0])
            yseam.append(y[0])
            comment(f"X{x[0]} Y{y[0]}",name)
            if i%supportpitch_indexes==0:

                x_coord_support.append(x[0])
                y_coord_support.append(y[0])
            if i%2==0:

                x = list(reversed(x))
                y = list(reversed(y))
                isOnBoundary = list(reversed(isOnBoundary))
                if previous_command!="move":
                    pass#retract(name)
                retract(name)
                move(x=x[0],y=y[0],fileName=name)
                detract(name)
                previous_command="move"
            if i%2==1:
                plt.plot(x,y,":b")
            
            # generating the gcode commands
            for j in range(1,len(x[:])-1):
                
                xcurr =x[:][j]
                xprev =x[:][j-1]
                yprev =y[:][j-1]
                ycurr =y[:][j]

               

                if isOnBoundary[j]and isOnBoundary[j-1]:
                    if not (isOnBoundary[j+1]): #if the point and the previous point is on the boundary, but the next point is not, move to this position to start printing
                        if previous_command != "move":
                            pass#retract(name)
                        retract(name)
                        move(x=xcurr,y=ycurr,fileName=name)
                        detract(name)
                        previous_command = "move"
                        curr_extruded_length = 0
                    else: #if the previous, current and next point are on the boundary curve, it can be ignored.
                        curr_extruded_length = 0
                #elif isOnBoundary[j]and not(isOnBoundary[j+1]):
                #    extrude(x=xcurr,y=ycurr,E=Efactor*curr_extruded_length,F=F,fileName=filename)
                #    curr_extruded_length = 0
                else:# if the previous and or current points are not on the boundary, it can be extruded
                    extrusionlength = np.sqrt((xcurr-xprev)**2+(ycurr-yprev)**2)
                    curr_extruded_length+=extrusionlength
                    if (curr_extruded_length>=min_length)|(j==len(x[:])-1):
                        if previous_command == "move":
                            pass#detract(name)
                        previous_command = "extrude"
                        extrude(x=xcurr,y=ycurr,E=Efactor*curr_extruded_length,F=F,fileName=name)
                        
                        
                        if i%supportpitch_indexes==0:
                            curr_supported_length+=curr_extruded_length
                            if curr_supported_length>supportpitch:
                                x_coord_support.append(xcurr)
                                y_coord_support.append(ycurr)
                                curr_supported_length=0
                        curr_extruded_length = 0
                        
                         
        i+=1
        first_bound_not_found = True
        
    lines = int(i/2)
    print(lines)
    for line in range(lines+stairlength*layers):
        for layer in range(layers):
            comment(f"layer {layer} line {line}",filename)
            if layer%2==0:
                #check if the line exsists
                if line-stairlength*layer>=0 and (os.path.isfile(f"lines/BottomLine{int(line-stairlength*layer)}.gcode") or os.path.isfile(f"lines/EvenLine{int(line-stairlength*layer)}.gcode")):
                    if layer==0 and os.path.isfile(f"lines/BottomLine{int(line-stairlength*layer)}.gcode"):
                        gcode_of_line = open(f"lines/BottomLine{int(line-stairlength*layer)}.gcode")
                        #the bottom line gets the bottom line file
                    elif os.path.isfile(f"lines/EvenLine{int(line-stairlength*layer)}.gcode"):
                        retract(filename)
                        move(z=baseHeight+layer*layerheight,fileName=filename)
                        detract(filename)
                        gcode_of_line = open(f"lines/EvenLine{int(line-stairlength*layer)}.gcode")
                    with open(filename,"a") as a:
                        a.write(gcode_of_line.read())
                    gcode_of_line.close()
                    
            else:
                if line-stairlength*layer>=0 and os.path.isfile(f"lines/OddLine{int(line-stairlength*layer)}.gcode"):
                    retract(filename)
                    move(z=baseHeight+layer*layerheight,fileName=filename)
                    detract(filename)
                    gcode_of_line = open(f"lines/OddLine{int(line-stairlength*layer)}.gcode")
                    with open(filename,"a") as a:
                        a.write(gcode_of_line.read())
                    gcode_of_line.close()
    
                    
                    
    


     #  -- draw the boundary --
    if previous_command != "move":
        pass#retract(filename)
    previous_command == "move"
    move(x=boundary_curve[0][0],y=boundary_curve[1][0],fileName=filename)
    
    for a in range(1,len(boundary_curve[0])):
        extrusionlength = np.sqrt((boundary_curve[0][a]-boundary_curve[0][a-1])**2+(boundary_curve[1][a]-boundary_curve[1][a-1])**2)
        if previous_command =="move":
            pass#detract(filename)
        previous_command = "extrude"
        extrude(x=boundary_curve[0][a],y=boundary_curve[1][a],E=0.016*extrusionlength,fileName=filename)        
    plt.plot(xseam,yseam,".k")   
    plt.axis('equal')
    plt.show()
   
    return r, min_length,x_coord_support,y_coord_support

with open("nonplanar.gcode",'w') as n:
    n.write("")
tower_block = [(0,0),(20,0),(20,20),(0,20),(0,0)]# the block that makes the tower
seed_part = densify_curve([(0.01,0.01),(0.01,19.99)],1)
overhang_bounds = [(-0.1,-0.1),(70.1,0-0.1),(70.1,20.1),(-0.1,20.1),(-0.1,-0.1)]

preamble = open("gcodes/Ender3StartGcode.gcode")
with open("nonplanar.gcode", 'a') as a:
        a.write(preamble.read())
        a.write("\nG0 Z-0.3")
        a.write("\nG92 Z0\n")
        a.close()
supportPilar(seed_curve=tower_block,layertickness=0.3,brimsize=10,towerheight=20,fileName="nonplanar.gcode")
offset2gcode2(linewidth=0.4,overlap=0.15,baseHeight=20+0.2,boundary_curve=overhang_bounds,Efactor=0.15/(0.25*np.pi*1.75**2),seed_curve=seed_part,filename="nonplanar.gcode",layers=6,angle=0)

fileBlock = open("gcodes/Block70x20x10Ender.gcode",'r')
fileEndGcode = open("gcodes/Ender3EndGcode.gcode",'r')
with open("nonplanar.gcode", 'a') as a:
    a.write("\nG0 X0 Y0 Z21.5")
    a.write("\nG92 X-25 Y80 Z0\n")
    a.write(fileBlock.read())
    fileBlock.close()
    a.write(fileEndGcode.read())
    fileEndGcode.close()
    a.close()
print(f"done at {str(datetime.datetime.now())}")
