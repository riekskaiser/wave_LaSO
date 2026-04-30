import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import time
a=input("experiment")
b=input("number")
fileName = f"Ex{a}_{b}"
outputFile = f"Tools\SingleLayerResults\{fileName}_results.txt"
fileName = f"Tools\SingleLayerImages\{fileName}.jpg"
# -------------------- plotting ------------------------------------
#make an array for the first two points
#----innitiate coordinate arrays----------
#start an array for the clicked origin points
x_points_origin = []
y_points_origin = []
#starts an array for the clicked horizontal scaling points
x_points_hscale = []
y_points_hscale = []
#starts an array for the clicked vertical scaling points
x_points_vscale = []
y_points_vscale = []
#starts an array for the clicked top end points
x_points_end_top = []
y_points_end_top = []
#starts an array for the clicked bottom end points
x_points_end_bot = []
y_points_end_bot = []

#starts an array for the height measurements on the top of the block
top_loc_block_mm = []

#points for declaring the vectors to create the axes 
origin_loc = [-np.inf,-np.inf]
x_axis_loc = [-np.inf,-np.inf]
y_axis_loc = [-np.inf,-np.inf]

# transformation matrix from pixels to mm
transformationMatrix = [[1,0,0],[0,1,0],[0,0,1]]

# height of the block with respect to the origin
height_offset = 0

# Create a figure and axis
fig, ax = plt.subplots()
image = plt.imread(fileName)
imheight, imwidth = image.shape[:2]
plt.imshow(image)
ax.set_title("Click on Origin")
ax.set_xlim(0,imwidth)
ax.set_ylim(0,imheight)
State = "origin"
def place_stop():
    imheight, imwidth = image.shape[:2]
    rect = patches.Rectangle((0, imheight), imwidth, int(imheight/10), linewidth=1, edgecolor='black', facecolor='red')
    ax.add_patch(rect)
    # Add the word "STOP" inside the rectangle
    ax.text(imwidth/2,imheight*1.05, 'Save result and go to next step', fontsize=12, color='white',va = "center",ha = "center")
    ax.set_ylim(0,imheight*1.1)
place_stop()

def create_transformation_matrix():
    global origin_loc, x_axis_loc, y_axis_loc

    # Known real-world distance
    mm = 30.0  # 3 cm = 30 mm

    origin = np.array(origin_loc, dtype=float)
    x_axis = np.array(x_axis_loc, dtype=float)
    y_axis = np.array(y_axis_loc, dtype=float)

    # Pixel basis vectors
    vx = x_axis - origin
    vy = y_axis - origin

    # Pixel basis matrix
    P = np.column_stack((vx, vy))  # 2×2

    # Linear transform: pixel → mm
    A = np.array([
        [mm, 0],
        [0, mm]
    ]) @ np.linalg.inv(P)

    # Translation (embed origin shift)
    t = -A @ origin

    # Homogeneous affine transform
    H = np.eye(3)
    H[:2, :2] = A
    H[:2, 2] = t

    print("\nTransformation matrix (pixel → mm):")
    print(H)

    return H
def pixel_to_mm(xp, yp):
    global transformationMatrix
    p = np.array([xp, yp, 1.0])
    return (transformationMatrix @ p)[:2]
def mm_to_pixel(x_mm, y_mm):
    """
    Convert real-world coordinates in millimeters to pixel coordinates.
    """
    H_inv = np.linalg.inv(transformationMatrix)

    p_mm = np.array([x_mm, y_mm, 1.0])
    p_pix = H_inv @ p_mm

    return p_pix[:2]

def saveData():
    with open(outputFile,'w') as out:
        out.write(f"Source file             : {fileName}")
        out.write(f"\nMoment of measurement   : {time.ctime(time.time())}")
        out.write("\n---------------------------------------------------------------")
        out.write(f"\n----------top displacements ----------------------------------")
        out.write("\nX_mm\tY_mm\n")
        for x, y in zip(x_points_end_top, y_points_end_top):
            out.write(f"{x:.4f}\t{y:.4f}\n")
        out.write(f"\n--------------------------------------------------------------")
        out.write(f"\n----------bottom displacements--------------------------------")
        out.write("\nX_mm\tY_mm\n")
        for x, y in zip(x_points_end_bot, y_points_end_bot):
            out.write(f"{x:.4f}\t{y:.4f}\n")

        
    plt.close("all")   


def buttonclicked():
    global State
    global origin_loc
    global x_axis_loc
    global y_axis_loc
    global transformationMatrix
    global height_offset
    match State:
        case "origin":
            points_clicked = len(x_points_origin)
            averagex = sum(x_points_origin)/points_clicked
            averagey = sum(y_points_origin)/points_clicked
            origin_loc = [averagex,averagey]
            
            print(f"Origin set at pixels ({np.round(averagex),0},{np.round(averagey),0})")
            ax.plot(averagex,averagey,"kx")# places a black x at the origin
            State = "horizontal scaling"
            ax.set_title("Click on the location 3 cm (6 blocks) from the origin, in horizontal direction")
        case "horizontal scaling":
            points_clicked = len(x_points_hscale)
            averagex = sum(x_points_hscale)/points_clicked
            averagey = sum(y_points_hscale)/points_clicked
            x_axis_loc = [averagex,averagey]
            
            print(f"Horizontal axis vector from origin to  ({np.round(averagex),0},{np.round(averagey),0})")
            ax.set_title("Click on the location 3 cm (6 blocks) from the origin, in vertical direction")
            State = "vertical scaling"
        case "vertical scaling":
            points_clicked = len(x_points_vscale)
            averagex = sum(x_points_vscale)/points_clicked
            averagey = sum(y_points_vscale)/points_clicked
            y_axis_loc = [averagex,averagey]
            
            print(f"Vertical axis vector from origin to  ({np.round(averagex),0},{np.round(averagey),0})")
            ax.set_title("Click on the top of the block")
            ax.plot([origin_loc[0],x_axis_loc[0]],[origin_loc[1],x_axis_loc[1]],"-k")
            ax.plot([origin_loc[0],y_axis_loc[0]],[origin_loc[1],y_axis_loc[1]],"-k")
            transformationMatrix=create_transformation_matrix()
            State = "block zeroing"

        case "block zeroing":
            points_clicked = len(top_loc_block_mm)
            height_offset = sum(top_loc_block_mm)/points_clicked
            point0 = mm_to_pixel(-1000,height_offset)
            point1 = mm_to_pixel(1000,height_offset)
            ax.plot([point0[0],point1[0]],[point0[1],point1[1]], ":r")
            State = "top measurement"
            ax.set_title("Click on top of the end of the overhang")
        case "top measurement":
            State = "bottom measurement"
            ax.set_title("Click on bottom of the end of the overhang")
        case "bottom measurement":
            State = "finish"
            ax.set_title("Click the button again to close and save the data")
        case "finish":
            saveData()


def origin(x,y):
    x_points_origin.append(x)
    y_points_origin.append(y)
    
    points_clicked = len(x_points_origin)
    averagex = sum(x_points_origin)/points_clicked
    averagey = sum(y_points_origin)/points_clicked
    print(f"Clicked point ({x},{y})")
    print(f"Points clicked :{points_clicked}")
    print(f"Average location ({averagex},{averagey})")

def horizontal(x,y):
    x_points_hscale.append(x)
    y_points_hscale.append(y)
    points_clicked = len(x_points_hscale)
    averagex = sum(x_points_hscale)/points_clicked
    averagey = sum(y_points_hscale)/points_clicked
    print(f"Clicked point ({x},{y})")
    print(f"Points clicked :{points_clicked}")
    print(f"Average location ({averagex},{averagey})")

def vertical(x,y):
    x_points_vscale.append(x)
    y_points_vscale.append(y)
    points_clicked = len(x_points_vscale)
    averagex = sum(x_points_vscale)/points_clicked
    averagey = sum(y_points_vscale)/points_clicked
    print(f"Clicked point ({x},{y})")
    print(f"Points clicked :{points_clicked}")
    print(f"Average location ({averagex},{averagey})")   

def zero_height(x,y):
    [x_mm,y_mm]=pixel_to_mm(x,y)
    top_loc_block_mm.append(y_mm)
    points_clicked = len(top_loc_block_mm)
    average = sum(top_loc_block_mm)/points_clicked
    print("-----------------------------------------")
    print(f"clicked point: ({x_mm} mm, {y_mm} mm)")
    print(f"Points clicked : {points_clicked}")
    print(f"Average height block: {average} mm")

def topmeasurement(x,y):
    [x_mm,y_mm] = pixel_to_mm(x,y)
    x_points_end_top.append(x_mm)
    y_points_end_top.append(y_mm-height_offset)
    points_clicked = len(x_points_end_top)
    averagex = sum(x_points_end_top)/points_clicked
    averagey = sum(y_points_end_top)/points_clicked
    print(f"Clicked point ({x_mm},{y_mm-height_offset})")
    print(f"Points clicked :{points_clicked}")
    print(f"Average location ({averagex},{averagey-height_offset})")  

def botmeasurement(x,y):
    [x_mm,y_mm] = pixel_to_mm(x,y)
    x_points_end_bot.append(x_mm)
    y_points_end_bot.append(y_mm-height_offset)
    points_clicked = len(x_points_end_bot)
    averagex = sum(x_points_end_bot)/points_clicked
    averagey = sum(y_points_end_bot)/points_clicked
    print(f"Clicked point ({x_mm},{y_mm-height_offset})")
    print(f"Points clicked :{points_clicked}")
    print(f"Average location ({averagex},{averagey-height_offset})")  
    
def on_click(event):
    
    if event.inaxes:  # Only if the click is inside the axes
        global Amount_of_clicks
        
        x, y = event.xdata, event.ydata
        if y>imheight: #recognise that the user clicked outside the image, so they clicked on a button
           buttonclicked() 
           
        else:
            match State:
                case "origin":
                    origin(x,y)
                case "horizontal scaling":
                    horizontal(x,y)
                case "vertical scaling":
                    vertical(x,y)
                case "block zeroing":
                    zero_height(x,y)
                case "top measurement":
                    topmeasurement(x,y)
                case "bottom measurement":
                    botmeasurement(x,y)

        # Redraw the canvas to show the new dot
        fig.canvas.draw()



# Connect the handler to the figure
fig.canvas.mpl_connect('button_press_event', on_click)

# Show the figure
plt.show()

