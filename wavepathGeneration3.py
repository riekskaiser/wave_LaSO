import matplotlib.pyplot as plt
from shapely.geometry import Point,LineString, Polygon
from shapely.affinity import rotate
from shapely import geometry
import numpy as np
from func import *
alternate = True
printer = "Bambu"
# --- Example input data ---
polyRes = 8

def densify_curve(seed_curve, spacing=0.1):
    
    #Add intermediate points along a line so that no segment is longer than spacing (in mm).
    line = LineString(seed_curve)
    length = line.length
    num_points = int(length / spacing)
    dense_points = [line.interpolate(dist).coords[0] for dist in np.linspace(0, length, num_points + 1)]
    return dense_points

# --- Helper functions ---
def coordinate_trans(boundary_curve): #transforms a matrix with the x and y coordinates to a list of points
    return [(boundary_curve[0][i], boundary_curve[1][i]) for i in range(len(boundary_curve[0]))]
import numpy as np

def lineinterpolation(xprev, yprev, xcurr, ycurr, length):
    dx = xcurr - xprev
    dy = ycurr - yprev
    
    seg_len = np.hypot(dx, dy)
    if seg_len == 0:
        raise ValueError("Previous and current points are identical.")

    t = length / seg_len

    xnew = xprev + t * dx
    ynew = yprev + t * dy
    return xnew, ynew

def offsets(seed_curve, r=0.1):
    line = LineString(seed_curve)
    offset_shape = line.buffer(r, resolution=polyRes)
    offset_boundary = offset_shape.exterior
    x_offset, y_offset = offset_boundary.xy
    return x_offset, y_offset, offset_shape

def translate_seed(seed_curve, dx, dy):
    return [(p[0] + dx, p[1] + dy) for p in seed_curve]

def rotate_coord(coord_set, center, angle):
    """
    Rotate:
      • list of (x,y) tuples
      • list-style boundary_curve [[x],[y]]
      • shapely LineString or Polygon
    around a given center point by a certain angle (degrees).
    """
    cx, cy = center

    # Case 1 --- Shapely geometry
    if hasattr(coord_set, "geom_type"):
        return rotate(coord_set, angle, origin=center, use_radians=False)

    # Case 2 --- [[x],[y]] boundary_curve format
    if isinstance(coord_set, list) and len(coord_set) == 2 \
       and isinstance(coord_set[0], list) and isinstance(coord_set[1], list):

        xs, ys = coord_set
        theta = np.deg2rad(angle)
        cos_t = np.cos(theta)
        sin_t = np.sin(theta)

        xr = []
        yr = []

        for x, y in zip(xs, ys):
            dx = x - cx
            dy = y - cy
            xr.append(dx * cos_t - dy * sin_t + cx)
            yr.append(dx * sin_t + dy * cos_t + cy)

        return [xr, yr]

    # Case 3 --- list of (x,y) tuples
    if isinstance(coord_set, list) and isinstance(coord_set[0], tuple):
        theta = np.deg2rad(angle)
        cos_t = np.cos(theta)
        sin_t = np.sin(theta)

        rotated = []
        for x, y in coord_set:
            dx = x - cx
            dy = y - cy
            rotated.append((
                dx * cos_t - dy * sin_t + cx,
                dx * sin_t + dy * cos_t + cy
            ))
        return rotated

    raise TypeError("rotate_coord(): unsupported input type.")

def last_False_index(arr):
    for i in range(len(arr) - 1, -1, -1):
        if not arr[i]:
            return i
    return -1  # or None, depending on what you prefer

# --- Iterative offset generation ---
def offset2gcode(linewidth = 0.4,overlap = 0.125,boundary_curve = [(0, 0), (12, 0), (18, 6), (32, 12), (12, 12), (12, 20), (8, 16), (4, 16), (0, 20), (0, 12), (-20, 12), (-6, 6), (0, 0)]
                 ,seed_curve = [(40, 20),(55, 22.5), (70, 25)],Efactor = 0.05,F = 180,xoffset = 25.0,yoffset = 20.0,supportpitch = 10.0,extruderTemp = 200,center = (80,80),supportpitch_across = 20,angle = 45,filename = "default.gcode"):
    #innitialises the lists that will recieve the coordinates for the locations of the supports
    x_coord_support = []
    y_coord_support = []
    #determines in which curve the supports are placed. Every curve with an index divisible by this number generates support locations
    supportpitch_indexes = max(1,int(supportpitch_across/(linewidth*(1-overlap))))
    #turns fan to full and heats up the extruder
    change_fanspeed(255,filename)
    previous_command = "move"
    set_extrusionTemp(extruderTemp,True,filename)
    #moves and rotates the seed curve geometry, so that the geometry is located and rotated correctly
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
    # this becomes the distance between each curve
    r = linewidth*(1-overlap)
    # --- define a minimum extruded length to prevent the printer from printing a line with a E value that rounds to 0
    E_min = 0.02
    min_length = max([0.05,E_min/Efactor])
    # determine the boundary polygon and densify the seed curve
    boundary_polygon = Polygon(boundary_curve) #generate a polygon of the boundary coordinates
    seed_curve = densify_curve(seed_curve,0.05) #makes sure that the curve that generates the offset curves has sufficient point density
    # --- Initial offset ---
    bin1, bin2, shape = offsets(seed_curve, r/2) #offset of the seedcurve
    current_shape = shape.intersection(boundary_polygon) #offset of the seedcurve where it intersects with the boundary polygon. Note this also includes the boundary
    coords = list(current_shape.exterior.coords)

    # --- innitialise index ----
    i = 1
   
    curr_extruded_length = 0
    xseam = []
    yseam = []
    while not current_shape.is_empty and i < 1000: #runs while the current wave is not empty
        
        
        if current_shape.is_empty|len(coords[0])<2:              #exits the loop if there is no more offsets to generate
            break
        
        if current_shape.geom_type == 'Polygon':
            x, y = current_shape.exterior.xy
            plt.plot(x, y)
            curr_supported_length = 0 #add a support every 10 mm
            
            # Write coordinates to G-code
            comment(f"offset {i}",filename)
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
            if i%supportpitch_indexes==0:

                x_coord_support.append(x[0])
                y_coord_support.append(y[0])
            if alternate and i%2==0:

                x = list(reversed(x))
                y = list(reversed(y))
                isOnBoundary = list(reversed(isOnBoundary))
            if previous_command!="move":
                retract(filename)
            move(x=x[0],y=y[0],fileName=filename)
            previous_command="move"
            
            lastOffboundary = last_False_index(isOnBoundary)
            
            
            
            for j in range(1,len(x[:])):
                
                xcurr =x[:][j]
                xprev =x[:][j-1]
                ycurr =y[:][j]
                yprev =y[:][j-1]

               

                if isOnBoundary[j]and isOnBoundary[j-1] and (j!=(len(isOnBoundary)-1)):
                    if not (isOnBoundary[j+1]): #if the point and the previous point is on the boundary, but the next point is not, move to this position to start printing
                        if previous_command != "move":
                            retract(filename)
                        move(x=xcurr,y=ycurr,fileName=filename)
                        previous_command = "move"
                        curr_extruded_length = 0
                    else: #if the previous, current and next point are on the boundary curve, it can be ignored.
                        curr_extruded_length = 0
                #elif isOnBoundary[j]and not(isOnBoundary[j+1]):
                #    extrude(x=xcurr,y=ycurr,E=Efactor*curr_extruded_length,F=F,fileName=filename)
                #    curr_extruded_length = 0
                else:# if the previous and or current points are not on the boundary, it can be extruded
                    extrusionlength = np.sqrt((xcurr-xprev)**2+(ycurr-yprev)**2) #distance between the current and previous point
                    curr_extruded_length+=extrusionlength #the accumulated length between the points
                    
                    # determining the positions of the support pilars
                    if i%supportpitch_indexes==0: # if the index is divisible by the supportpitch_indexes, indexes are placed on this curve
                        prev_supported_length = curr_supported_length
                        x_last_support = xprev
                        y_last_support = yprev
                        curr_supported_length+=extrusionlength
                        if curr_supported_length>supportpitch and not extrusionlength<=0:
                            dist_points = np.sqrt((xprev-xcurr)**2+(yprev-ycurr)**2)
                            len_segment=0
                            while (curr_supported_length>supportpitch) and (len_segment<dist_points):
                                x_last_support,y_last_support = lineinterpolation(xprev=x_last_support,yprev=y_last_support,xcurr=xcurr,ycurr=ycurr, length=supportpitch-prev_supported_length)
                                len_segment = np.sqrt((xprev-x_last_support)**2+(yprev-y_last_support)**2)
                                x_coord_support.append(x_last_support)
                                y_coord_support.append(y_last_support)
                                curr_supported_length-=(supportpitch-prev_supported_length)
                                
                                prev_supported_length=0
                                
                    if (curr_extruded_length>=min_length)|(j==len(x[:])-1)|(j==lastOffboundary-1):
                        if previous_command == "move":
                            detract(filename)
                        previous_command = "extrude"
                        extrude(x=xcurr,y=ycurr,E=Efactor*curr_extruded_length,F=F,fileName=filename)
                        
                        
                        
                        curr_extruded_length = 0
                 
                    
            #saving information for the next iteration, and updating indices
            xprevious = xcurr
            yprevious = ycurr 
            curr_supported_length = 0
            print(f"completed offset {i}")           
            i += 1
            first_bound_not_found = True
        coords = list(current_shape.exterior.coords) 
        a,b,next_shape = offsets(coords, r=r)
        current_shape = next_shape.buffer(0.001).intersection(boundary_polygon)       
    """ #  -- draw the boundary --
    if previous_command != "move":
        retract(filename)
    previous_command == "move"
    move(x=boundary_curve[0][0],y=boundary_curve[1][0],fileName=filename)
    
    for a in range(1,len(boundary_curve[0])):
        extrusionlength = np.sqrt((boundary_curve[0][a]-boundary_curve[0][a-1])**2+(boundary_curve[1][a]-boundary_curve[1][a-1])**2)
        if previous_command =="move":
            detract(filename)
        previous_command = "extrude"
        extrude(x=boundary_curve[0][a],y=boundary_curve[1][a],E=0.016*extrusionlength,fileName=filename)   """     
    plt.plot(xseam,yseam,".k")   
    plt.axis('equal')
  
   
    return r, min_length,x_coord_support,y_coord_support

# --- making the support pilar at the point of the seed curve
def supportPilar(seed_curve = [(40, 20),(55, 22.5), (70, 25)],layertickness = 0.2,brimsize=5.0,towerheight=10.0,
                 feedrate_brim = 300,feedrate_tower = 1000,nozzlesize = 0.4,xoffset = 25,yoffset = 20,extruderTemp = 200,
                 center = (0,0), angle = 0,supportx= [],supporty = [],supportpitch = 10,fileName = "default.gcode"):
    set_extrusionTemp(extruderTemp,True,fileName)
    comment(f"Start Brim, {brimsize} mm  thick",fileName)
    move(z=layertickness,fileName=fileName)
    brimarr = np.linspace(brimsize,nozzlesize,int(brimsize/nozzlesize))
    seed_curve = translate_seed(seed_curve,xoffset,yoffset)
    seed_curve = rotate_coord(seed_curve,center,angle)
    
    polygon = geometry.Polygon(seed_curve)
    polygon = polygon.buffer(0.5)
    seed_curve = densify_curve(seed_curve,0.1)
    for i in reversed(range(len(supportx))):
        point = geometry.Point(supportx[i],supporty[i])
        if polygon.contains(point):
            del(supportx[i])
            del(supporty[i])
    for brimpos in brimarr:
        xoffset,yoffset,polygon =offsets(seed_curve,brimpos)
        move(x=xoffset[0],y=yoffset[0],z=0.2,fileName=fileName)
        E_min = 0.02
        Efactor= nozzlesize*layertickness/(0.25*np.pi*1.75**2)
        min_length = E_min/Efactor
        curr_extruded_length = 0
        # brim seedcurve
        for i in range(1,len(xoffset)):
            curr_extruded_length+=np.sqrt((xoffset[i-1]-xoffset[i])**2+(yoffset[i-1]-yoffset[i])**2)
            if curr_extruded_length>=min_length:
                
                extrude(x=xoffset[i],y=yoffset[i],E=Efactor*curr_extruded_length*1.1,F=feedrate_brim,fileName=fileName)
                curr_extruded_length=0
        #brim supportpins
    for i in range(len(supportx)):
        for brimpos in brimarr:
            retract(fileName)
            move(x=supportx[i]-brimpos,y=supporty[i]-brimpos, fileName=fileName)
            detract(fileName)
            extrude(x=supportx[i]+brimpos,E=Efactor*2*brimpos,F=feedrate_brim,fileName=fileName)
            extrude(y=supporty[i]+brimpos,E=Efactor*2*brimpos,F=feedrate_brim,fileName=fileName)
            extrude(x=supportx[i]-brimpos,E=Efactor*2*brimpos,F=feedrate_brim,fileName=fileName)
            extrude(y=supporty[i]-brimpos,E=Efactor*2*brimpos,F=feedrate_brim,fileName=fileName)
    #printing the towers
    change_fanspeed(128,fn=fileName)
    towerarr = np.linspace(0.3+layertickness,towerheight,int(towerheight/layertickness))
    xoffset,yoffset,polygon = offsets(seed_curve,0.5*nozzlesize)

    for towerpos in towerarr:
        retract(fileName)
        move(x=xoffset[0],y=yoffset[0],z=towerpos,fileName=fileName)
        detract(fileName)
        for i in range(1,len(xoffset)):
            curr_extruded_length+=np.sqrt((xoffset[i-1]-xoffset[i])**2+(yoffset[i-1]-yoffset[i])**2)
            if (curr_extruded_length>=min_length)|(i==len(xoffset)):
                extrude(x=xoffset[i],y=yoffset[i],E=Efactor*curr_extruded_length*1.1,F=feedrate_tower,fileName=fileName)
                curr_extruded_length=0
        triangle = (supportpitch*0.75-nozzlesize)/towerheight
        for j in range(len(supportx)):
            retract(fileName=fileName)
            move(x=supportx[j]-triangle*(towerheight-towerpos)+nozzlesize,y=supporty[j],fileName=fileName)
            detract(fileName)
            extrude(x=supportx[j]+nozzlesize + triangle*(towerheight-towerpos) + nozzlesize ,E=(2*triangle*(towerheight-towerpos) )*Efactor,fileName=fileName)
            
def wavePathGeneration(bead_area = 0.15,nozzle_size = 0.4,layerheight_support=0.2,filament_diam = 1.75,flow_multiplier = 1.05, 
                       ExType = "polygonOverhang",printer = "Ender",
                       overlap = 0.15,
                       boundary = [(0, 0), (12, 0), (18, 6), (32, 12), (12, 12), (12, 20), (8, 16), (4, 16), (0, 20), (0, 12), (-20, 12), (-6, 6), (0, 0)]
                        ,seed = [(12,20),(8,16),(4,16),(0,20)],
                        x_offset = 25, y_offset = 25, support_pitch = 10, support_pitch_across=20,exTemp = 200.0,
                        feedRate_Overhang = 180.0,feedRate_brim = 400,feedRate_supports = 600.0,
                        brimSize = 5.0,height = 10.0,center = (80,80), angle = 0,supported=False, tower = []):
    # bead_area             crossectional area of track                                 mm^2
    # nozzle_size           diameter of the nozzle                                      mm
    # layerheight_support   layerthickness of the support structure                     mm
    # filament_diam         diameter of filament stock                                  mm
    # flow_multiplier       flow multiplier                                             -
    # ExType                type of experiment, used for file name                      string
    # printer               type of printer, used for file name                         "Ender" or "Bambu"
    # boundary              set of points representing the edge of the overhang         points in mm
    # seed                  set of points representing the seed curve                   points in mm
    # x_offset              location of origin of boundary and seed wrt bed origin      mm
    # y_offset              location of origin of boundary and seed wrt bed origin      mm
    # support_pitch         distance between support pilars                             mm
    # exTemp                extrusion Temperature                                       celcius
    # feedRate_Overhang     feedrate of the overhang                                    mm/min
    # feedRate_brim         feedrate of the brim                                        mm/min
    # feedRate_supports     feedrate of the support pilars and the tower                mm/min
    # brimSize              width of the brim of support pilars and the tower           mm
    # height                height where the overhang is printed                        mm
    # center                center where the shape is rotated around                    (mm,mm)
    # angle                 angle with which the shape is rotated counterclockwise      degree



    E_fac = bead_area/(0.25*np.pi*filament_diam**2)*flow_multiplier
    fn = f"gcodes/{ExType}{printer}.gcode"
    with open(fn,"w") as file:
        file.write("M83") # make sure the extruder is in relative coordinates
    # write the starting gcode from the correct printer to the gcode file
    if printer == "Ender":
        with open("gcodes/Ender3StartGcode.gcode") as f:
            preamble = f.read()
            f.close()
    elif printer == "Bambu":
        with open("gcodes/BambuLabsA1MiniStart.gcode") as f:
            preamble = f.read()
            f.close()
    with open(fn, 'a') as f:
        f.write(preamble) #write the starting gcode
    move(z=0.3,fileName=fn)

    
    if tower==[]:
        towercoords= seed
    else:
        towercoords=tower
    with open("placeholder.gcode",'w') as a:
        a.write("")
    r, m, x,y= offset2gcode(linewidth=nozzle_size,overlap=overlap,boundary_curve=boundary,seed_curve=seed,
                            xoffset=x_offset,yoffset=y_offset,supportpitch=support_pitch,supportpitch_across=support_pitch_across,extruderTemp=exTemp,
                            F=feedRate_Overhang,Efactor=E_fac,center=center,angle=angle,filename="placeholder.gcode")
    if supported:
        supportPilar(seed_curve=towercoords,layertickness=layerheight_support,brimsize=brimSize,towerheight=height,feedrate_brim=feedRate_brim,
                 feedrate_tower=feedRate_supports,nozzlesize=nozzle_size,xoffset=x_offset,yoffset=y_offset,extruderTemp=exTemp,supportx=x,supporty=y,
                 center=center,supportpitch=support_pitch*0.5, angle=angle,fileName=fn)
    else:
        
        supportPilar(seed_curve=towercoords,layertickness=layerheight_support,brimsize=brimSize,towerheight=height,feedrate_brim=feedRate_brim,
                feedrate_tower=feedRate_supports,nozzlesize=nozzle_size,xoffset=x_offset,yoffset=y_offset,extruderTemp=exTemp,supportx=[],supporty=[],
                center=center, angle=angle,fileName=fn)
    comment("LAYER_CHANGE",fn)
    move(z=height+bead_area/nozzle_size,fileName=fn)
    bridge = open("placeholder.gcode",'r')
    with open(fn, 'a') as a:
        a.write(bridge.read())
    move(z=min(height*10,150),fileName=fn) #move extruder out of the way
    if printer == "Ender":
        fileEndGcode = open("gcodes/Ender3EndGcode.gcode",'r')
    elif printer == "Bambu":
        fileEndGcode = open("gcodes/BambuLabsA1MiniEnd.gcode",'r')
    with open(fn, 'a') as a:
        a.write(fileEndGcode.read())#write the appropiate end gcode to the file 
    plt.plot(x,y,".b") #plot the location of the supports
    plt.show()



"""
seed_curve = [(10,0),(8, 4), (14, 5)]
boundary_curve = coordinate_trans([
    [0, 10, 8, 14, 16, 14, 8, 8, 4, -2, 0],
    [0, 0, 4, 5, 8, 14, 14, 8, 12, 4, 0],
    ])

wavePathGeneration(bead_area=0.15,nozzle_size=0.4,layerheight_support=0.2,filament_diam=1.75,flow_multiplier=1.1,ExType="PolyOverhang", 
                   printer = "Ender",overlap=0.15,boundary=boundary_curve,seed=seed_curve,supported=False)"""

