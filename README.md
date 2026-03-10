# wave_LaSO
Investigating the warping of Laterally Supported Overhangs in fused deposition modelling; The python code.

This code was written in the context of Rieks Kaiser's master thesis, for the study Mechanical Engineering at the University of Twente
# What is a wave LaSO?
A wave LaSO, or a wave laterally supported overhang is a novel feature for 3D printed FDM parts, that allows overhanging structures (structures that are not supported by previous layers) to be printed without any supports.
By overlapping the printed tracks slightly, tracks get connected to the previous printed track. The printed tracks get defined as the geometric offset of the previous track. This can be seen in the figure below.
<img width="714" height="539" alt="WaveOverhangs" src="https://github.com/user-attachments/assets/baade059-4a39-4534-a189-b588ecf3e6c5" /> 

To prevent warping of this overhang, small pin supports are added underneath it. This prevents the overhang from curling upward.
# What are the benefits of wave LaSO's?
Large overhangs generally can not be printed without supports. Support interfaces, where the regular support structures are connected to the overhang, can be hard to remove, can leave scarring, or result in a bottom layer of the overhang that is not completely filled. In contrast, wave LaSO's with pin supports have less scarring, waste less material for support material, print faster, and leave a surface that is completely water tight. Moreover, using wave LaSO's does not require nozzles with larger clearances (which are needed for non planar printing) or expensive 5-axis printers. All test prints made with these scripts were made with a stock Ender 3 V3.

<img width="1924" height="658" alt="RasterMicroscope" src="https://github.com/user-attachments/assets/429d8e4c-e40e-4063-80ef-76422217a8fb" />


A microscopy image of the bottom layer of a test piece with 0.12 mm (A) and 0.06 mm (B) distance between the supports and the part, and printed with a wave LaSO (C)


![BottomSurfaceQuality_contrast2](https://github.com/user-attachments/assets/520d30e8-7891-47dc-b99c-fc077ad2d3c5)


Pictures of the bottom of an overhang for normal (N) and tree (T) supports, and a custom (C) pin-supported wave LaSO.

# What is the difference between this and the arc overhang github?
The arc overhang github is actually what inspired my supervisor to create wave LaSO's. Arc overhangs define the overhang tracks by filling the overhanging shape with cocentric circular arcs instead of geometric offset. The downside of that approach is that the nozzle stays near the center of these concentric circles quite long, which means that the materials doesnt cool there evenly. This leads to sagging in the center if the process is not tuned well. It also struggles with shaper corners and straight lines as it would result in lots of small circles placed close to each other. Wave LaSO's do not have this issue. Another difference is that the arc overhang is coded a lot better. I have no formal training in Python, so it is badly optimised. However, this code does allow for immediately integrating the LaSO into an existing sliced part.


Check out the arc overhang repository at https://github.com/stmcculloch/arc-overhang for Steven McCulloch's solution to overhangs
# Is this all your original work?
The concept of wave LaSO's, as well as the name wave LaSO's, was made by my thesis supervisor Janis Anderson. However, as his implementation of the wave LaSO algoritm was made in the parametric design software Grashopper (which is not free) I rewrote it in Python so that it could be shared with other people better. The method that I use to read the gcode file and the placement of the support pins is my own idea. I did use some chatGPT for debugging or to generate some smaller functions.
# What input does the script require?
The script requires a gcode file, preferrably sliced by OrcaSlicer. The script compiles the perimeters of the part by reading the coordinate listed in the gcode file to generate the tracks the printer has to make. Additionally, all layers that are not replaced by a wave LaSO get copied from the original gcode file. The script specifically looks for flags in the gcode such as ;TYPE:Outer_wall to determine what it is looking at. This has only been tested for files made by OrcaSlicer. You will be promted by the script to give the height at where the overhang begins, the name of the file, the nozzle and track width, the size of the pin brims and if you want pin support.
# What does running the customsupportinjector require?
Shapely (which requires GEOS), NumPy and Matplotlib. Run the file in a python terminal, with the input gcode file in a folder "gcode" in the same directory as the customsupportinjector script.
# What was the code tested on?
The code was tested for an Ender 3 V3, with Overture Rock PLA, a .12 mm layer height, a nozzle temperature of 220 degrees celcius and a bed temperature of 60 degrees celcius. I strongly recommend to review the resultant gcode with tools like https://ncviewer.com/ before printing, and keeping a close eye on the printing of first layer, the overhang, and the layer that is placed on top of the overhang. This script builds custom gcode, it is experimental. I do not take any responsibilty for damage to 3D printers or computers that results from the use of this page.
# I have suggestions for improving the code. 
I currently do not have an email set up for suggestions yet, and I am not that familliar with the workings of Github. When I am done with my thesis, I will look into how to get suggestions, and how to incorporate them.
