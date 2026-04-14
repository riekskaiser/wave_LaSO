import numpy as np
import re
from shapely.geometry import Point,LineString, Polygon
from shapely.affinity import rotate
#from shapely import geometry
#from func import *
import matplotlib.pyplot as plt
import time
slicer = "Orca"
GivenName = input("Please provide the name of the gcode file, withouth the extension: ")
fileName = f"gcodes/{GivenName}.gcode"
inputfile = open(fileName,"r")
fn = f"gcodes/{GivenName}out.gcode"
print(f"outputfile: {fn}")
BaseHeight = input("At what height is the overhang located? (in mm), using a dot as a decimal operator: ")
BaseHeight = float(BaseHeight) #converting the given aswer to a float
OverhangHeight = [BaseHeight,BaseHeight+0.12]# lower and upper height of the overhang layer
SupportQuestion = input("Do you want pin supports? (y/n): ")
if SupportQuestion == 'y':
    Supported = True
elif SupportQuestion =="n":
    Supported = False

if Supported:
    Brimsize = input("what size should the brim of the pins be? (in mm)(recommended 5.0): ")
    Brimsize = float(Brimsize)#
    supportpitch = input("what is the distance between supports from track to track? (in mm): ")
    supportpitch = float(supportpitch)
    supportpitch_across = input("what is the distance between supports on a track?(in mm): ")
    supportpitch_across = float(supportpitch_across)
    
else:
    Brimsize = 0
    supportpitch=100
    supportpitch_across=100

nozzlesize =  input("What is the nozzlediameter (in mm)(recommended 0.4): ")
nozzlesize = float(nozzlesize)

trackwidth = input(f"What is the track width? (in mm)(recommended {nozzlesize}): ")
trackwidth = float(trackwidth)


starttime = time.time()


outputfile = open(fn,'w')
Base_GCode = inputfile.readlines()
ZLoc = 0
BedOffset = 0.2

OverhangPrinted = False
seedLoc = (0,0)
seedCurve = [(0,0),(0,1)]

Efactor= nozzlesize**2/(0.25*np.pi*1.75**2)



seedlayerFound = False
seedlayerComplete = False
seedshape = []
seedpoly = Polygon(seedshape)
outerWallFound = False
perimeterComplete = False
suspendSearch = False
BoundaryShape = []
current_x = 0
current_y = 0
def flagdefinition(slicer):
    outerWallFlag = ";TYPE:Outer wall"
    overhangWallFlag = ";TYPE:Overhang wall"
    innerWallFlag = ";TYPE:Inner wall"
    match slicer:
        case "Orca":
            outerWallFlag = ";TYPE:Outer wall"
            overhangWallFlag = ";TYPE:Overhang wall"
            innerWallFlag = ";TYPE:Inner wall"
        case "Prusa":
            a=1
    return outerWallFlag,innerWallFlag,overhangWallFlag

def CapturePerimeter(command):
    #captures the shape of the overhang to be printed by looking at the gcode for the outer wall generation
    global outerWallFound
    global perimeterComplete
    global BoundaryShape
    global suspendSearch
    global current_x
    global current_y
    global slicer
    outerWallFlag,innerWallFlag,overhangWallFlag = flagdefinition(slicer)
    x_re = re.compile(r'X([-+]?[0-9]*\.?[0-9]+)')
    y_re = re.compile(r'Y([-+]?[0-9]*\.?[0-9]+)')
    if not outerWallFound:
        if command.startswith(outerWallFlag) or command.startswith(overhangWallFlag):
            outerWallFound=True
            suspendSearch=False
    elif command.startswith(";TYPE:") and "infill" in command : #as the outer wall ends wth an retraction, the boundary definition is exited after a retraction is found
        perimeterComplete = True
        if not (BoundaryShape[0]==BoundaryShape[-1]):# if the perimeter does not form a closed loop, it gets closed here
            BoundaryShape.append(BoundaryShape[0])
        print(f"Detected outer shape of boundary: {BoundaryShape}")
    elif command.startswith(";TYPE:Inner wall"):
        suspendSearch=True
    elif command.startswith("G1") and not suspendSearch and " E" in command and not ("E-" in command): #when the 
        x_match = x_re.search(command)
        y_match = y_re.search(command)

        if x_match:
            current_x = float(x_match.group(1))
        if y_match:
            current_y = float(y_match.group(1))

        # Record point if both coordinates are known
        if current_x is not None and current_y is not None:
            BoundaryShape.append((current_x, current_y))
        

shapeShadow = Polygon()
currentOutline = []
outerWallFound2 = False
perimeterComplete2 = False
def createSupportRestriction(command):
    #captures the combined shape of all previous layers, so that the supports are not printed inside them
    global outerWallFound2
    global perimeterComplete2
    global shapeShadow
    global currentOutline
    global current_x
    global current_y
    x_re = re.compile(r'X([-+]?[0-9]*\.?[0-9]+)')
    y_re = re.compile(r'Y([-+]?[0-9]*\.?[0-9]+)')
    if not outerWallFound2:
        if command.startswith(";TYPE:Outer wall"):
            outerWallFound2=True
            perimeterComplete2=False
    elif command.startswith("G1") and "E-" in command : #as the outer wall ends wth an retraction, the boundary definition is exited after a retraction is found
        perimeterComplete2 = True
        polyBound = Polygon(currentOutline)
        shapeShadow = shapeShadow.union(polyBound) #combine the layer with the outline of all previous layers, so t
        currentOutline=[]
        outerWallFound2 = False
    elif command.startswith("G1") and " E" in command: #when the 
        x_match = x_re.search(command)
        y_match = y_re.search(command)

        if x_match:
            current_x = float(x_match.group(1))
        if y_match:
            current_y = float(y_match.group(1))

        # Record point if both coordinates are known
        if current_x is not None and current_y is not None:
            currentOutline.append((current_x, current_y))


def getSeedloc(command):
    global seedlayerFound
    global seedlayerComplete
    global current_x
    global current_y
    global seedshape
    global seedLoc
    global seedpoly
    x_re = re.compile(r'X([-+]?[0-9]*\.?[0-9]+)')
    y_re = re.compile(r'Y([-+]?[0-9]*\.?[0-9]+)')
    if not seedlayerFound:
        if command.startswith(";TYPE:Outer wall"):
            seedlayerFound = True
    elif command.startswith(";TYPE:Inner wall") or "infill" in command:
        seedlayerComplete = True
        
        seedpoly = Polygon(seedshape).buffer(-2*nozzlesize)
        x, y = zip(*seedshape)
        plt.figure(1)
        plt.plot(x,y)
        plt.show()
    elif command.startswith("G1") and "E" in command:
        x_match = x_re.search(command)
        y_match = y_re.search(command)

        if x_match:
            current_x = float(x_match.group(1))
        if y_match:
            current_y = float(y_match.group(1))

        # Record point if both coordinates are known
        if current_x is not None and current_y is not None:
            seedshape.append((current_x, current_y))

# --- Helper functions ---
def densify_curve(seed_curve, spacing=0.1):
    
    #Add intermediate points along a line so that no segment is longer than spacing (in mm).
    line = LineString(seed_curve)
    length = line.length
    num_points = int(length / spacing)
    dense_points = [line.interpolate(dist).coords[0] for dist in np.linspace(0, length, num_points + 1)]
    return dense_points


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
    if not isinstance(seed_curve, list):
        seed_curve = list(seed_curve.exterior.coords) 
    line = LineString(seed_curve)
    offset_shape = line.buffer(r, resolution=8)
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

def closest_point(xlast, ylast, points,isonBoundary):
    # inputs : 
    # xlast      x coordinate of reference point
    # ylast      y coordinate of reference point
    # points     list of points (each point is [x, y])

    def dist(xlast, ylast, point):
        return (xlast - point[0])**2 + (ylast - point[1])**2 #square root is not needed for the comparison, it just takes up time

    min_dist = float('inf')
    index_last_point = None

    for i in range(len(points)):
        if isonBoundary[i]:
            d = dist(xlast, ylast, points[i])
        else:
            d= float('inf')
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
    OverhangToolpaths = "\nM82;extruder to absolute coordinates\nG92 E0; Reset the extruder coordinate\n"
    a,b =zip(*boundary_curve)
    x_coord_support = list(a)
    y_coord_support = list(b)
    

    def place_support(
        xcoords,
        ycoords,
        isOnBoundary,
        supportpitch,trackindex):
        """
        Evenly distribute supports along a polyline.
        Force supports at boundary points defined by isOnBoundary array.
        """

        xsupports = []
        ysupports = []

        n = len(xcoords)
        if n < 2 or not Supported:
            return xsupports, ysupports

        accumulated = 0.0
        next_support_at = supportpitch

        x_prev = xcoords[0]
        y_prev = ycoords[0]

        # --- Force support at first boundary point ---
        if isOnBoundary[0]:
            xsupports.append(x_prev)
            ysupports.append(y_prev)

        for i in range(1, n):
            x_curr = xcoords[i]
            y_curr = ycoords[i]

            dx = x_curr - x_prev
            dy = y_curr - y_prev
            seg_len = (dx*dx + dy*dy) ** 0.5

            if seg_len == 0:
                continue

        # ---- Evenly spaced supports via interpolation ----
            while accumulated + seg_len >= next_support_at:
                remaining = next_support_at - accumulated
                t = remaining / seg_len

                x_support = x_prev + t * dx
                y_support = y_prev + t * dy

                xsupports.append(x_support)
                ysupports.append(y_support)

                next_support_at += supportpitch

            accumulated += seg_len

            # ---- Force support if this point is boundary ----
            if isOnBoundary[i]:
                # avoid duplicate if very close to last placed support
                if len(xsupports) == 0 or (
                    (x_curr - xsupports[-1])**2 +
                    (y_curr - ysupports[-1])**2 > 16
                ):
                    xsupports.append(x_curr)
                    ysupports.append(y_curr)

            x_prev = x_curr
            y_prev = y_curr
        print(f"placed {len(xsupports)} supports on line {trackindex}")
        return xsupports, ysupports

    
    
    #turns fan to full and heats up the extruder
    #change_fanspeed(255,filename)
    #set_extrusionTemp(extruderTemp,True,filename)
        #to reduce the dependancy on external scripts, this code is removed
    #moves and rotates the seed curve geometry, so that the geometry is located and rotated correctly
    
    # inputs 
    # - linewidth       width of the line               mm
    # - overlap         overlap of printed lines        %
    # - boundary_curve  boundary of the printed area    [x-coordinate array],[y-coorinate array] mm
    # - seed_curve      curve that generates overhangs  list of shapely points mm
    # - fileName        filepath of the .gcode file     string
    # - F               feedrate of the overhang        mm/min
    
    L_min=0.001
    # --- define the r (radius of the offset circles) as the track offset --- 
    # this becomes the distance between each curve
    r = linewidth*(1-overlap)
    # --- define a minimum extruded length to prevent the printer from printing a line with a E value that rounds to 0
    E_min = 0.02
    min_length = max([0.05,E_min/Efactor])
    # determine the boundary polygon and densify the seed curve
    boundary_polygon = Polygon(boundary_curve) #generate a polygon of the boundary coordinates
    boundary_polygon = boundary_polygon.buffer(-r).buffer(0)
   
    # --- Initial offset ---
    bin1, bin2, shape = offsets(seed_curve, r/2) #offset of the seedcurve
    current_shape = shape.intersection(boundary_polygon) #offset of the seedcurve where it intersects with the boundary polygon. Note this also includes the boundary
    coords = list(current_shape.exterior.coords)

    # --- innitialise index ----
    i = 0
    
    xlast = 0
    ylast = 0
    gcode_lines = []

    while not current_shape.is_empty and i < 10e4: #runs while the current wave is not empty
        print(f"calculating track {i}", end="\r")
        gcode_lines = []
        E=0 #resets the current E value
        E_prev = 0
        if current_shape.is_empty|len(coords[0])<2:              #exits the loop if there is no more offsets to generate
            break
        
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
                if boundary_polygon.boundary.distance(Point(xcurr,ycurr))<1e-6:
                    isOnBoundary[j] = True
            
            for j in range(1,len(x)-1):
                if not(isOnBoundary[j-1] and isOnBoundary[j] and isOnBoundary[j+1]):
                    valid_action_indices.append(j) #filter out every point that is on the boundary, and is surrounded by other boundary points
            valid_action_indices.append(len(x)-1)
            if i%2==0:   #switch direction per curve
                isOnBoundary_filtered = [isOnBoundary[a] for a in valid_action_indices] 
                xfiltered =     [x[a] for a in valid_action_indices]    
                yfiltered =     [y[a] for a in valid_action_indices] 
                
            else:
                
                isOnBoundary_filtered = list(reversed([isOnBoundary[a] for a in valid_action_indices]) )
                xfiltered =             list(reversed([x[a] for a in valid_action_indices]) ) 
                yfiltered =             list(reversed([y[a] for a in valid_action_indices]))
                
            if len(xfiltered)<4:
                break
            #select the first point that is on the boundary, to determine the starting point

            points_filtered = list(zip(xfiltered, yfiltered))
            first_index = closest_point(xlast=xlast,ylast=ylast,points=points_filtered,isonBoundary=isOnBoundary_filtered)
            xfiltered = list(xfiltered[first_index:])+list(xfiltered[:first_index])
            yfiltered = list(yfiltered[first_index:])+list(yfiltered[:first_index])
            isOnBoundary_filtered = list(isOnBoundary_filtered[first_index:])+list(isOnBoundary_filtered[:first_index])
            x_prev = xfiltered[0]
            y_prev = yfiltered[0]
            plt.plot(xfiltered[0],yfiltered[0],".r")
            plt.plot([xlast,xfiltered[0]],[ylast,yfiltered[0]],'-g')
            line = f";offset {i} \nG0 X{xfiltered[0]:.3f} Y{yfiltered[0]:.3f} F2400\n" # moves the nozzle to the beginning of the curve
            gcode_lines.append(line)
            j=0
           
            #places a support at the start of the curve
            E_coord = np.zeros(len(xfiltered)) 
            for j in range(1,len(xfiltered)):
                distance = np.sqrt((xfiltered[j]-xfiltered[j-1])**2+(yfiltered[j]-yfiltered[j-1])**2)
                
                if (isOnBoundary_filtered[j-1] and isOnBoundary_filtered[j]) : #if the current and previous point are on the boundary, it is not extruding
                    E_coord[j]=E
                    #plot travel paths in green
                    plt.plot([xfiltered[j],xfiltered[j-1]],[yfiltered[j],yfiltered[j-1]],'-r')
                    line = f"G0 X{xfiltered[j]:.3f} Y{yfiltered[j]:.3f} F2400\n"
                    gcode_lines.append(line)
                    

                    #places a support on each boundary point
                else:
                    
                    
                    
                    Edifference = distance *Efactor
                    E+=Edifference
                    E_coord[j] =E
                    if isOnBoundary_filtered[j]:# if the current coordinate is on the boundary, but the previous is not, extrude 
                        #plot extruded paths is blue
                        plt.plot([xfiltered[j],x_prev],[yfiltered[j],y_prev],'-b')
                        line = f"G1 X{xfiltered[j]:.3f} Y{yfiltered[j]:.3f} E{E:.3f} F{F:.3f}\n"
                        E_prev = E
                        x_prev = xfiltered[j]
                        y_prev = yfiltered[j]
                        gcode_lines.append(line)
                    elif ((E-E_prev)>L_min): #if the difference in E exceeds the minimum length, extrude the line
                        plt.plot([xfiltered[j],x_prev],[yfiltered[j],y_prev],'-b')
                        E_prev = E
                        x_prev = xfiltered[j]
                        y_prev = yfiltered[j]
                        line = f"G1 X{xfiltered[j]:.3f} Y{yfiltered[j]:.3f} E{E:.3f} F{F:.3f}\n"
                        gcode_lines.append(line)

                        
            j=-1
            if i % supportpitch_indexes == 0:
                xs_tmp, ys_tmp = place_support(
                    xfiltered,
                    yfiltered,
                    isOnBoundary_filtered,
                    supportpitch,
                    i
                )
                x_coord_support.extend(xs_tmp)
                y_coord_support.extend(ys_tmp)
     
            xlast = xfiltered[-1] #saves the last point to show the travel to the next offset
            ylast = yfiltered[-1]
        gcode_block = "".join(gcode_lines)
        OverhangToolpaths += f"\n;-----------Line {i}-------------\nG92 E0;reset extruder position\n{gcode_block}"

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
    #prints the perimeter
    gcode_lines=[]
    gcode_lines.append(f"\nG92 E0; resets E coordinate")
    E=0
    xcoords,ycoords = zip(*BoundaryShape)
    xcoords=list(xcoords)
    ycoords=list(ycoords)
    gcode_lines.append(f"\n;------ start printing boundary ------\n")
    gcode_lines.append(f"G1 E-0.5 \n")
    gcode_lines.append(f"G0 X{xcoords[-1]} Y{ycoords[-1]} \n")
    gcode_lines.append(f"G1 E0\n")
    for i in range(len(xcoords)):
        x_curr=xcoords[i]
        y_curr=ycoords[i]
        x_prev=xcoords[i-1]
        y_prev=ycoords[i-1]
        dist = np.sqrt((x_curr-x_prev)**2+(y_curr-y_prev)**2)
        E+=dist*Efactor
        gcode_lines.append(f"G1 X{x_curr} Y{y_curr} E{E} F{F}\n")        
    gcode_block = "".join(gcode_lines)
    OverhangToolpaths += f"\n{gcode_block}\n;-----------Boundary finished-------------\nG92 E0;reset extruder position\n"
    plt.axis('equal')
    
    return x_coord_support,y_coord_support,OverhangToolpaths

def remove_near_duplicates(xsupports, ysupports, threshold=1.0):
    points = np.column_stack((xsupports, ysupports))
    threshold_sq = threshold ** 2
    
    keep_mask = np.ones(len(points), dtype=bool)

    for i in range(len(points)):
        if not keep_mask[i]:
            continue
        
        # Compute squared distances to remaining points
        diffs = points[i+1:] - points[i]
        dists_sq = np.sum(diffs**2, axis=1)
        
        # Mark close points for removal
        close_points = dists_sq < threshold_sq
        keep_mask[i+1:][close_points] = False

    filtered = points[keep_mask]
    return filtered[:, 0], filtered[:, 1]


def GenerateOverhangToolpaths():
    global seedpoly
    
    xsupports,ysupports,OverhangToolpaths = offset2gcode(linewidth = 0.4,overlap = 0.15,boundary_curve = BoundaryShape,seed_curve = seedpoly,Efactor = Efactor,F = 180,xoffset = 0,yoffset = 0,supportpitch = supportpitch,extruderTemp = 200,center = seedLoc,supportpitch_across = supportpitch_across,angle = 0,filename = "default.gcode")
    xsupports,ysupports=remove_near_duplicates(xsupports,ysupports,4)
     # Create mask for shadow filtering
    shadow_buffer = shapeShadow.buffer(5)
    
    mask = np.array([
        not shadow_buffer.contains(Point(x, y))
        for x, y in zip(xsupports, ysupports)
    ])
    if mask.size>0:
        xsupports = xsupports[mask]
        ysupports = ysupports[mask]

    return xsupports.tolist(),ysupports.tolist(),OverhangToolpaths

def DetectOverhang(shape_prev_layer = Polygon(),shape_curr_layer = Polygon(),alpha_max = 45,layer_height = 0.2):
    #determines overhanging shapes in a layer, by comparing it to the previous layer
    #   NOT YET IMPLEMENTED IN THE CODE
    #shape_prev_layer           Shapely polygon of the previous layer
    #shape_curr_layer           Shapely polygon of the current layer
    #aplha_max                  max angle of the overhang, degrees
    #layer_height               layer height, mm
    alpha_max_rad = alpha_max/180*np.pi
    d_crit = layer_height/(np.tan(alpha_max_rad)) #critical distance, at larger distances, the shape needs to be supported
    buffered_shape_prev = shape_prev_layer.buffer(d_crit)

    OverhangShape = shape_curr_layer.difference(buffered_shape_prev)
    if OverhangShape.is_empty:
        Overhang_present = True
    else:
        Overhang_present = False
    return Overhang_present, OverhangShape





#generate toolpaths for the overhang and locations for the placements of the supportpins
for line in range(len(Base_GCode)-3):
    if Base_GCode[line].strip().startswith(";Z:"):
        ZLoc=float(Base_GCode[line].strip()[3:])
    
    if not seedlayerComplete and (ZLoc>=OverhangHeight[0]-0.13):
        getSeedloc(Base_GCode[line].strip())    
    if ZLoc>OverhangHeight[0]+0.12:
        if not perimeterComplete:
            CapturePerimeter(Base_GCode[line].strip())
        else:
            if BoundaryShape:
                xs, ys = zip(*BoundaryShape)
                plt.figure()
                plt.plot(xs, ys, '-o')
                plt.axis("equal")
                plt.show()
            xsupports,ysupports,toolPaths = GenerateOverhangToolpaths()
            
            break
    elif ZLoc<BaseHeight: 
        createSupportRestriction(Base_GCode[line].strip())


ZLocPrev = BedOffset
ZLoc=BedOffset
SupportBrimsPrinted = False        
for line in range(len(Base_GCode)-3):
    if Base_GCode[line].strip().startswith(";Z:"):
        ZLocPrev = ZLoc
        ZLoc=float(Base_GCode[line].strip()[3:]) 
        
        layerHeight = ZLoc-ZLocPrev
        Efactor = ((trackwidth-layerHeight)*layerHeight + 0.25*np.pi*layerHeight**2)/(0.25*np.pi*1.75**2)
    
    
    if ZLoc>=OverhangHeight[0] and ZLoc<=OverhangHeight[1]:# write the overhang gcode if it isnt there already
        if not OverhangPrinted:
            outputfile.writelines(";Start printing overhang\n")
            outputfile.writelines(toolPaths)
            outputfile.writelines(";stop printing overhangs\n")
            outputfile.writelines("G92 E0; Resetting the coordinates of the extruder one last time for good measure\n")
            outputfile.writelines("M83; Change the extruder back to relative coordinates\n")
            OverhangPrinted = True
        


    else:
        if Base_GCode[line].strip() == ";LAYER_CHANGE" and ZLoc<OverhangHeight[0]: #writing the support pins
            if ZLocPrev <=BedOffset and Supported and not SupportBrimsPrinted:
                brimArr = np.linspace(Brimsize,0,int(Brimsize/trackwidth))
                SupportBrimsPrinted=True
                
                if True:
                    outputfile.write("\n;Start support pin brims ")
                    for i in range(len(xsupports)):
                        xpos = xsupports[i]
                        ypos = ysupports[i]
                        outputfile.write(f"\n;Brim {i}\n")
                        for brimpos in brimArr:
                            outputfile.write(f"\nG1 E-0.5 Z{ZLoc+1};Zhop and retract\n")
                            outputfile.write(f'G0 X{xpos-brimpos} Y{ypos - brimpos};\n')
                            outputfile.write(f"G1  Z{ZLoc} E0.50; undo zhop and reprime nozzle\n")
                            outputfile.write(f"G1 X{xpos+brimpos} E{2*brimpos*Efactor*0.95} F500\n")
                            outputfile.write(f"G1 Y{ypos+brimpos} E{2*brimpos*Efactor*0.95}\n")
                            outputfile.write(f"G1 X{xpos-brimpos} E{2*brimpos*Efactor*0.95}\n")
                            outputfile.write(f"G1 Y{ypos-brimpos} E{2*brimpos*Efactor*0.95}\n")


                    
            elif Supported:
                outputfile.write(";Start printing supports\n")
                for i in range(len(xsupports)):
                    shape = 0.5*Brimsize-ZLoc*(0.5*Brimsize-0.5)/BaseHeight
                    outputfile.write(f"G1 E-0.5 F9000; retract\n")
                    outputfile.write(f"G0 Z{ZLoc+0.4}")
                    outputfile.write(f"G0 X{xsupports[i]-shape} Y{ysupports[i]} F9000\n")
                    outputfile.write(f"G0 Z{ZLoc}")
                    outputfile.write(f"G1 E0.501 F2000; reprime nozzle\n")
                    outputfile.write(f"G1 X{xsupports[i]+shape} Y{ysupports[i]} E{Efactor*2*shape}F2400\n")
                    outputfile.write(f"G1 E-0.5 F2000; retract\n")
                    outputfile.write(f"G0 X{xsupports[i]} Y{ysupports[i]-shape} F9000\n")
                    outputfile.write(f"G1 E0.50 F2000; reprime nozzle\n")
                    outputfile.write(f"G1 X{xsupports[i]} Y{ysupports[i]+shape} E{Efactor*2*shape}F2400\n")
                outputfile.write(";Finish printing supports\n")
        outputfile.write(Base_GCode[line])


endtime = time.time()
totalTime = endtime-starttime

print(f"Finished in {int(totalTime/60)} minutes and {int(totalTime%60)} seconds at {time.ctime(time.time())}")

if BoundaryShape:
    xs, ys = zip(*BoundaryShape)
    plt.figure()
    plt.plot(xs, ys, '-o')
    plt.plot(xsupports,ysupports,".k")
    plt.plot(*seedLoc,'xk')
    plt.axis('equal')
    plt.title("Outer Wall Perimeter")
    plt.show()

