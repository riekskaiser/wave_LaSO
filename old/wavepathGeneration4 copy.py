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
import numpy as np

def closest_point(xlast, ylast, points):
    # inputs : 
    # xlast      x coordinate of reference point
    # ylast      y coordinate of reference point
    # points     list of points (each point is [x, y])

    def dist(xlast, ylast, point):
        return (xlast - point[0])**2 + (ylast - point[1])**2 #square root is not needed for the comparison, it just takes up time

    min_dist = float('inf')
    index_last_point = None

    for i in range(len(points)):
        d = dist(xlast, ylast, points[i])
        if d < min_dist:
            min_dist = d
            index_last_point = i

    return index_last_point




# --- Iterative offset generation ---
def offset2gcode(linewidth = 0.4,overlap = 0.125,boundary_curve = [(0, 0), (12, 0), (18, 6), (32, 12), (12, 12), (12, 20), (8, 16), (4, 16), (0, 20), (0, 12), (-20, 12), (-6, 6), (0, 0)]
                 ,seed_curve = [(40, 20),(55, 22.5), (70, 25)],Efactor = 0.05,F = 180,xoffset = 25.0,yoffset = 20.0,supportpitch = 10.0,extruderTemp = 200,center = (80,80),supportpitch_across = 20,angle = 45,filename = "default.gcode"):
    #innitialises the lists that will recieve the coordinates for the locations of the supports
    
    #determines in which curve the supports are placed. Every curve with an index divisible by this number generates support locations
    supportpitch_indexes = max(1,int(supportpitch_across/(linewidth*(1-overlap))))
    
    x_coord_support = []
    y_coord_support = []

    def place_support(dist_since_support):
        nonlocal x_coord_support
        nonlocal y_coord_support
        nonlocal i
        nonlocal j
        nonlocal xfiltered
        nonlocal yfiltered
        nonlocal isOnBoundary_filtered
        if i%supportpitch_indexes==0:
            if (dist_since_support>=supportpitch)or isOnBoundary_filtered[j]:
                x_coord_support.append(xfiltered[j])
                y_coord_support.append(yfiltered[j])
                dist_since_support=0
        return dist_since_support

    
    #turns fan to full and heats up the extruder
    change_fanspeed(255,filename)
    
    #set_extrusionTemp(extruderTemp,True,filename)
    #moves and rotates the seed curve geometry, so that the geometry is located and rotated correctly
    
    boundary_curve = rotate_coord(coord_set=boundary_curve,center = center,angle=angle)
    boundary_curve = translate_seed(boundary_curve,xoffset,yoffset)
    seed_curve = rotate_coord(coord_set=seed_curve,center=center,angle=angle)
    seed_curve = translate_seed(seed_curve,xoffset,yoffset)
    # inputs 
    # - linewidth       width of the line               mm
    # - overlap         overlap of printed lines        %
    # - boundary_curve  boundary of the printed area    [x-coordinate array],[y-coorinate array] mm
    # - seed_curve      curve that generates overhangs  list of shapely points mm
    # - fileName        filepath of the .gcode file     string
    # - F               feedrate of the overhang        mm/min
    
    L_min=0.01
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
    i = 0
    
    curr_extruded_length = 0
    xseam = []
    yseam = []

    xcoords = []
    ycoords = []
    xlast = 0
    ylast = 0
    gcode_lines = []
    with open(filename,"a") as a:
        a.write("M82;set printer to absolute mode\n")
        a.write("G92 E0; Reset extruder position\n")
    while not current_shape.is_empty and i < 1000: #runs while the current wave is not empty
        gcode_lines = []
        E=0 #resets the current E value
        E_prev = 0
        if current_shape.is_empty|len(coords[0])<2:              #exits the loop if there is no more offsets to generate
            break
        dist_since_support = 0.0
        if current_shape.geom_type == 'Polygon':
            x, y = current_shape.exterior.xy
            if i==0:
                xlast = x[0]
                ylast = y[0]
            isOnBoundary = np.zeros(len(x),dtype=bool)
            
            valid_action_indices = [0]
            for j in range(len(x)):
                xcurr =x[j]
                ycurr =y[j]
                if boundary_polygon.boundary.distance(Point(xcurr,ycurr))<1e-8:
                    isOnBoundary[j] = True
            
            for j in range(1,len(x)-1):
                if not(isOnBoundary[j-1] and isOnBoundary[j] and isOnBoundary[j+1]):
                    valid_action_indices.append(j) #filter out every point that is on the boundary, and is surrounded by other boundary points
            valid_action_indices.append(len(x)-1)
            if i%2==0:   #switch direction per curve
                isOnBoundary_filtered = [isOnBoundary[a] for a in valid_action_indices] 
                xfiltered =     [x[a] for a in valid_action_indices]    
                yfiltered =     [y[a] for a in valid_action_indices] 
                print(i)
            else:
                
                isOnBoundary_filtered = list(reversed([isOnBoundary[a] for a in valid_action_indices]) )
                xfiltered =             list(reversed([x[a] for a in valid_action_indices]) ) 
                yfiltered =             list(reversed([y[a] for a in valid_action_indices]))
                print(i)
            if len(xfiltered)<4:
                break
            #select the first point that is on the boundary, to determine the starting point

            points_filtered = list(zip(xfiltered, yfiltered))
            first_index = closest_point(xlast=xlast,ylast=ylast,points=points_filtered)
            xfiltered = list(xfiltered[first_index:])+list(xfiltered[:first_index])
            yfiltered = list(yfiltered[first_index:])+list(yfiltered[:first_index])
            isOnBoundary_filtered = list(isOnBoundary_filtered[first_index:])+list(isOnBoundary_filtered[:first_index])
            x_prev = xfiltered[0]
            y_prev = yfiltered[0]
            plt.plot(xfiltered[0],yfiltered[0],".r")
            plt.plot([xlast,xfiltered[0]],[ylast,yfiltered[0]],'-g')
            line = f";offset {i} \nG0 X{xfiltered[0]:.3f} Y{yfiltered[0]:.3f} F2400\n"
            gcode_lines.append(line)
            j=0
            dist_since_support=place_support(dist_since_support)
            E_coord = np.zeros(len(xfiltered)) 
            for j in range(1,len(xfiltered)-1):
                if isOnBoundary_filtered[j-1] and isOnBoundary_filtered[j] : #if the current and previous point are on the boundary, it is not extruding
                    E_coord[j]=E
                    #plot travel paths in green
                    plt.plot([xfiltered[j],xfiltered[j-1]],[yfiltered[j],yfiltered[j-1]],'-g')
                    line = f"G0 X{xfiltered[j]:.3f} Y{yfiltered[j]:.3f} F2400\n"
                    gcode_lines.append(line)
                    dist_since_support=place_support(dist_since_support)
                else:
                    dist = np.sqrt( (xfiltered[j]-xfiltered[j-1])**2+(yfiltered[j]-yfiltered[j-1])**2)
                    dist_since_support+=dist
                    dist_since_support = place_support(dist_since_support)
                    Edifference = dist *Efactor
                    E+=Edifference
                    E_coord[j] =E
                    if isOnBoundary_filtered[j]:# if the current coordinate is on the boundary, but the previous not, extrude 
                        #plot extruded paths is blue
                        plt.plot([xfiltered[j],x_prev],[yfiltered[j],y_prev],'-b')
                        line = f"G1 X{xfiltered[j]:.3f} Y{yfiltered[j]:.3f} E{E:.3f} F{F:.3f}\n"
                        E_prev = E
                        x_prev = xfiltered[j]
                        y_prev = yfiltered[j]
                        gcode_lines.append(line)
                    elif ((E-E_prev)>L_min): #if the difference in E exceeds the minimum lenght, extrude the line
                        plt.plot([xfiltered[j],x_prev],[yfiltered[j],y_prev],'-b')
                        E_prev = E
                        x_prev = xfiltered[j]
                        y_prev = yfiltered[j]
                        line = f"G1 X{xfiltered[j]:.3f} Y{yfiltered[j]:.3f} E{E:.3f} F{F:.3f}\n"
                        gcode_lines.append(line)

                        
            j=-1
            dist_since_support=place_support(dist_since_support)      
            xlast = xfiltered[-1] #saves the last point to show the travel to the next offset
            ylast = yfiltered[-1]

        with open(filename,"a") as a:
            a.writelines(gcode_lines)
            a.write("G92 E0;\n")#resets the E coordinate
            a.close()
        E=0 #resets the current E value
        E_prev = 0

        i+=1
        # creates an offset
        coords = list(current_shape.exterior.coords) 
        a,b,next_shape = offsets(coords, r=r)
        current_shape = next_shape.buffer(0.001).intersection(boundary_polygon)    
            
     
    plt.axis('equal')
    
    return r, min_length,x_coord_support,y_coord_support

# --- making the support pilar at the point of the seed curve
def supportPilar(seed_curve = [(40, 20),(55, 22.5), (70, 25)],layertickness = 0.2,brimsize=5.0,towerheight=10.0,
                 feedrate_brim = 300,feedrate_tower = 1000,nozzlesize = 0.4,xoffset = 25,yoffset = 20,extruderTemp = 200,
                 center = (0,0), angle = 0,supportx= [],supporty = [],supportpitch = 10,fileName = "default.gcode"):
    set_extrusionTemp(extruderTemp,False,fileName)
    comment(f"Start Brim, {brimsize} mm  thick",fileName)
    move(z=layertickness,fileName=fileName)
    brimarr = np.linspace(brimsize,nozzlesize,int(brimsize/nozzlesize))
    
    seed_curve = rotate_coord(seed_curve,center,angle)
    seed_curve = translate_seed(seed_curve,xoffset,yoffset)
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
        move(x=xoffset[0],y=yoffset[0],z=0.15,fileName=fileName)
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
                        brimSize = 5.0,height = 10.0,center = (80,80), angle = 0.1,supported=False, tower = [],
                        block = False, overhanglength = 0):
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
    move(z=height,fileName=fn)
    bridge = open("placeholder.gcode",'r')
    toolchangestop = """\nG0 Y0
    G0 X10 Y10 
    G4 S200;Wait 200 seconds
    G1 E1 ; purge the nozzle
"""
    
    with open(fn, 'a') as a:
        a.write(toolchangestop)
        a.write(bridge.read())
        if block:
            blockfile = open(f"gcodes/Block{int(overhanglength+20)}X20X10{printer}.gcode","r")
            a.write("\nG90; Absolute position\nM83; Relative E position\n")
            a.write("G0 X0 Y0\n")
            a.write(f"G92 X{-x_offset} Y{0} Z0; redefines the current position to z=0\n")
            a.write(blockfile.read())
            a.write("\nG0 X0 Y0\n")
            a.write("\nG92 X{x_offset} Y{0}\n")
            blockfile.close()
        
    move(z=min(height*10,100),fileName=fn) #move extruder out of the way
    if printer == "Ender":
        fileEndGcode = open("gcodes/Ender3EndGcode.gcode",'r')
    elif printer == "Bambu":
        fileEndGcode = open("gcodes/BambuLabsA1MiniEnd.gcode",'r')
    with open(fn, 'a') as a:
        a.write(fileEndGcode.read())#write the appropiate end gcode to the file 
    plt.plot(x,y,".b") #plot the location of the supports
   

seed_curve = [(50,0),(40, 20), (70, 25)]
"""

tower = [(50,0),(40,20),(70,25),(50,0)]
wavePathGeneration(bead_area=0.15,nozzle_size=0.4,layerheight_support=0.2,filament_diam=1.75,flow_multiplier=1,ExType="whydoesntitwork", 
                   printer = "Ender",center=(40,35),overlap=0.125,tower=tower,boundary=boundary_curve,seed=seed_curve,supported=True,height=5,brimSize=5, support_pitch=10.0,support_pitch_across=10.0,angle=180)
"""
plt.figure(1)
plt.suptitle("Definition of an Offset Curve",fontsize = 20)
boundary_curve = coordinate_trans([
    [0, 50, 40, 70, 80, 70, 40, 40, 20, -10, 0],
    [0, 0, 20, 25, 40, 70, 70, 40, 60, 20, 0],
    ])
plt.subplot(231)
plt.xlim([-10,80])
plt.ylim([-10, 100])
plt.title("A")
plt.axis("off")
plt.plot([50,40,70],[0,20,25],"-k",label = "Seed Curve")
plt.plot([0, 50, 40, 70, 80, 70, 40, 40, 20, -10, 0],
    [0, 0, 20, 25, 40, 70, 70, 40, 60, 20, 0],":k", label = "Boundary Overhang")
plt.axis("equal")

plt.subplot(232)
plt.xlim([-10,80])
plt.ylim([-10, 100])
plt.title("B")
plt.axis("off")
[x,y,poly]=offsets(seed_curve,5)
plt.plot(x,y, "--r", label = "Geometric Offset")
plt.plot([50,40,70],[0,20,25],"-k",label = "Seed Curve")
plt.plot([0, 50, 40, 70, 80, 70, 40, 40, 20, -10, 0],
    [0, 0, 20, 25, 40, 70, 70, 40, 60, 20, 0],":k", label = "Boundary Overhang")
plt.axis("equal")

plt.subplot(233)
plt.xlim([-10,80])
plt.ylim([-10, 100])
plt.title("C")
plt.axis("off")
plt.plot(x,y, "--r", label = "Geometric Offset")
plt.plot([50,40,70],[0,20,25],"-k",label = "Seed Curve")
plt.plot([0, 50, 40, 70, 80, 70, 40, 40, 20, -10, 0],
    [0, 0, 20, 25, 40, 70, 70, 40, 60, 20, 0],":k", label = "Boundary Overhang")
boundary_polygon = Polygon(boundary_curve)
current_shape = poly.intersection(boundary_polygon)
x, y = current_shape.exterior.xy
plt.plot(x,y,"-y",label = "Offset and boundary intersection")
plt.axis("equal")

plt.subplot(234)
plt.xlim([-10,80])
plt.ylim([-10, 100])
plt.axis("off")
plt.title("D")
plt.plot([50,40,70],[0,20,25],"-k",label = "Seed Curve")
plt.plot([0, 50, 40, 70, 80, 70, 40, 40, 20, -10, 0],
    [0, 0, 20, 25, 40, 70, 70, 40, 60, 20, 0],":k", label = "Boundary Overhang")
isOnBoundary = np.zeros(len(x),dtype=bool)
for j in range(len(x)):
                xcurr =x[j]
                ycurr =y[j]
                if boundary_polygon.boundary.distance(Point(xcurr,ycurr))<1e-8:
                    isOnBoundary[j] = True
valid_action_indices = [0]
for j in range(1,len(x)-1):
    if not(isOnBoundary[j-1] and isOnBoundary[j] and isOnBoundary[j+1]):
        valid_action_indices.append(j) 
xfiltered =     [x[a] for a in valid_action_indices]    
yfiltered =     [y[a] for a in valid_action_indices] 
points_filtered = list(zip(xfiltered, yfiltered))
first_index = closest_point(xlast=44,ylast=0,points=points_filtered)
print(first_index)
xfiltered = list(xfiltered[first_index:])+list(xfiltered[:first_index])
yfiltered = list(yfiltered[first_index:])+list(yfiltered[:first_index])

plt.plot(0,0, "--r", label = "Geometric Offset")
plt.plot(0,0,"-y",label = "Offset and boundary intersection")
plt.plot(xfiltered,yfiltered,"-b", linewidth = 2,label = "Filtered Offset Curve")
plt.xlim([-10,80])
plt.ylim([-10, 100])
plt.axis("equal")

plt.subplot(236)
plt.plot(0,0,"-k",label = "Seed Curve")
plt.plot(0,0,":k", label = "Boundary Overhang")
plt.plot(0,0, "--r", label = "Geometric Offset")
plt.plot(0,0,"-y",label = "Offset and boundary intersection")
plt.plot(0,0,"-b", linewidth = 2,label = "Filtered Offset Curve")
plt.axis("off")
plt.figure(1)
plt.legend()
plt.show()

