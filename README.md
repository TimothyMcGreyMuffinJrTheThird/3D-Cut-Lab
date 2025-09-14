3D Cut Lab
---

<img width="256" height="256" alt="3D_Cut_Lab_Logo" src="https://github.com/user-attachments/assets/4ee91058-e413-4276-8c0b-56782a7dcbd0" /> <br> 

<img width="256" height="256" alt="IMG_0080" src="https://github.com/user-attachments/assets/7a07976d-5756-4f3b-9801-949a43729693" />

<img width="256" height="256" alt="IMG_00572" src="https://github.com/user-attachments/assets/77f6a312-8175-4030-be1e-5619682aaf12" />
  
<img width="256" height="256" alt="IMG_00772" src="https://github.com/user-attachments/assets/ccf72ea4-89ba-48c7-9519-bc9654379479" />
<br> 
<br> 
This Python GUI application makes it easy to convert complex 3D STL models, including those with chamfers and countersinks, into 2D heightmaps for precise laser engraving. It is a user-friendly tool that generates SVG files that are ready for laser cutting.
🚀 Features

STL to Heightmap: Converts an STL file into a grayscale PNG heightmap.

Calibration: Includes a unique calibration feature that allows you to correct for non-linear depth output of your laser engraver.

SVG Output: Generates a final SVG file with the embedded heightmap and optional red contour lines for cutting.

User-Friendly Interface: An easy-to-use GUI for setting parameters like pixel density, engraving depth, and top Z-plane.

Preview Functionality: Provides a preview of the generated heightmap with contour lines before saving.

Installation
---

This program was developed for Windows and does not require a separate Python installation, as it is provided as a standalone executable (.exe) file. Simply download the latest version from the releases section (on the right side)  and run it directly to start the program.



How to Use the Program
---

<img width="299,5" height="375,5" alt="image" src="https://github.com/user-attachments/assets/d6c36527-6b25-47cd-ad0f-b42d3be05099" />
<br> 


1. Load your STL File: Click the "Open STL File" button and select the STL model you want to process.



2. Calibrate Maximum Depth (Highly Recommended): This is a critical step for accurate results. To find the correct value for your laser, enter the value of your deepest feature (e.g., a chamfer of 0.8 mm) into the "Max Depth" field. Then, click "Create Max Depth Calibration SVG". It is essential that the test rectangle from the generated SVG is cut on the exact same material as your final workpiece. Repeat this process until you reach the desired depth of your deepest feature. The more accurate this value, the more precise your result will be. I used multiple raster cuts and DPI 500.
<br> 

<img width="210" height="250" alt="Test_1_MaxDepthCalibration" src="https://github.com/user-attachments/assets/efc54547-a208-4432-b4e2-09219bee1996" />

<img width="256" height="256" alt="qweqwe" src="https://github.com/user-attachments/assets/76c4c9b0-ebb1-487a-a50d-ec8ea187b32e" />
<br> 
<br> 
3. Pixel Density: It is highly recommended to set the pixel density to 10. A higher value results in a more detailed heightmap and more accurate cutting paths. Here the comparison pixel density 2 vs 10: <br> 
<br> 

<img width="190" height="199,5" alt="3_engraving2" src="https://github.com/user-attachments/assets/803f2819-11fe-4116-a2eb-002ce4f48c67" />

<img width="190" height="199,5" alt="3_engraving" src="https://github.com/user-attachments/assets/933250d9-10b6-46e7-80cd-4e8b98bf3224" />
<br> 
<br> 
Top Z Plane: This value will be filled in automatically based on your "Max Depth" calibration.

Pro Setting: Calibration Points (Optional): After you have performed the Max Depth calibration, you can use additional calibration points to improve precision across the entire depth range. This helps to correct for non-linear cutting behavior of your laser, where the actual depth might not perfectly match the target depth. You can add these points as a list of (Target Depth, Actual Depth) values. This will change the heigthmap values at these points and makes the texture at the selected height darker or lighter.

4. Generate the SVG: Click the "Generate SVG" button to start the conversion process. The application will create one or more SVG files that can be used for laser cutting. The process can take some time depending on the model size and pixel density. For example, a 20x20 mm square with a pixel density of 10 should take less than a minute.
<br> 
<img width="256" height="256" alt="3_engraving" src="https://github.com/user-attachments/assets/5ef53b55-1985-4051-afd0-e9605e74e347" />
<br> 
<br> 
5. Import and Laser: Import the generated SVG files into your laser software. Only import the SVG file; the other files are only needed for the creation process. Use the cutting values that you determined during the Max Depth calibration to raster the image. For cutting the outer paths, you can use your standard cutting values. I used for my test MeerK40T, but other software like Lightburn works too.<br> 
<br> 
<img width="256" height="256" alt="IMG_00832" src="https://github.com/user-attachments/assets/5552570a-23da-4a7e-a2e4-c6963e9407d4" />
<br> 
<br> 
Known Issues
---
Slight Path Offset: The generated paths may have a minimal offset. This offset is reduced as the pixel density is increased.<br> 
<br> 
<img width="225" height="350" alt="image" src="https://github.com/user-attachments/assets/469978e8-b7bc-4b90-b7f6-e28ddf393ee1" />
<br> 
<br> 
Special Characters: Be aware that the program may encounter issues with file or path names containing special characters like German umlauts (ä, ö, ü).

A Note from the Developer
---
Hello, I'm the developer of this tool. I have very little experience programming in Python, and most of the code was created with the help of AI. This is also my first time using GitHub, and I developed this tool for research and testing purposes. I hope it's useful for you too. HAVE FUN ! 

