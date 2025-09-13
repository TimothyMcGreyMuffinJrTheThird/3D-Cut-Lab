


#3D Cut Lab 

import numpy as np
import os
import io
import base64
from PIL import Image, ImageDraw, ImageFont, ImageTk
from skimage import measure
import svgwrite
from scipy import ndimage
from scipy.interpolate import interp1d
import trimesh
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading

def apply_calibration(z_scaled, calibration_points, min_depth_mm, max_depth_mm):
    """
    Applies a non-linear calibration to the height data.

    :param z_scaled: The height data, scaled to the depth range.
    :param calibration_points: A list of tuples (Target depth, Actual depth).
    :param min_depth_mm: The minimum depth.
    :param max_depth_mm: The maximum depth.
    :return: The corrected height data.
    """
    if calibration_points is None or len(calibration_points) < 2:
        return z_scaled

    sorted_points = sorted(calibration_points, key=lambda p: p[1])
    target = np.array([p[0] for p in sorted_points])
    actual = np.array([p[1] for p in sorted_points])

    f = interp1d(actual, target, kind='linear', bounds_error=False, fill_value=(target[0], target[-1]))

    corrected = f(z_scaled)
    
    return np.clip(corrected, min_depth_mm, max_depth_mm)

def stl_to_heightmap_absolute_depth(stl_file, pixels_per_mm=2.0, max_engraving_depth_mm=10.0, zero_z_plane_mm=None, calibration_points=None):
    """
    Creates an absolute heightmap from an STL file.
    Depths are calculated from a global Z-plane.
    
    :param stl_file: Path to the STL file.
    :param pixels_per_mm: The number of pixels per millimeter for the generated heightmap.
    :param max_engraving_depth_mm: Maximum depth in mm for the engraving (corresponds to black).
    :param zero_z_plane_mm: The absolute Z-coordinate of the top engraving plane.
    :param calibration_points: A list of (Target, Actual) depth tuples for correction.
    :return: A tuple with the paths to the generated files, dimensions, and the raw height data.
    """
    if not os.path.exists(stl_file):
        return None, None, None, None, None

    mesh = trimesh.load(stl_file)
    minx, miny, minz = mesh.bounds[0]
    maxx, maxy, maxz = mesh.bounds[1]
    stl_width = maxx - minx
    stl_height = maxy - miny

    if stl_width == 0 or stl_height == 0:
        return None, None, None, None, None
        
    if zero_z_plane_mm is None:
        zero_z_plane_mm = maxz
    
    resolution_x = int(stl_width * pixels_per_mm)
    resolution_y = int(stl_height * pixels_per_mm)
    
    if resolution_x < 1 or resolution_y < 1:
        resolution_x = max(1, resolution_x)
        resolution_y = max(1, resolution_y)
        messagebox.showwarning("Warning", "The STL object is very small, a minimum resolution of 1x1 pixel will be used.")

    z_values = np.zeros((resolution_y, resolution_x))
    xs = np.linspace(minx, maxx, resolution_x)
    # Loop over y-coordinates in descending order to match PIL's top-left origin
    ys = np.linspace(maxy, miny, resolution_y)

    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            origins = np.array([[x, y, maxz + 1]])
            directions = np.array([[0, 0, -1]])
            locations, _, _ = mesh.ray.intersects_location(origins, directions, multiple_hits=False)
            if len(locations) > 0:
                z_values[j, i] = locations[:, 2].max()
            else:
                z_values[j, i] = np.nan
    
    depths_from_zero = zero_z_plane_mm - z_values
    
    depths_from_zero[np.isnan(depths_from_zero)] = max_engraving_depth_mm + 1.0 

    if calibration_points:
        depths_from_zero = apply_calibration(depths_from_zero, calibration_points, 0.0, max_engraving_depth_mm)
    
    z_clamped = np.clip(depths_from_zero, 0.0, max_engraving_depth_mm)
    
    heightmap_gray = 255 - ((z_clamped / max_engraving_depth_mm) * 255)
    
    engraving_mask = ~np.isnan(z_values)
    
    heightmap_rgba = np.zeros((z_clamped.shape[0], z_clamped.shape[1], 4), dtype=np.uint8)
    
    heightmap_rgba[engraving_mask, 0] = heightmap_gray[engraving_mask].astype(np.uint8)
    heightmap_rgba[engraving_mask, 1] = heightmap_gray[engraving_mask].astype(np.uint8)
    heightmap_rgba[engraving_mask, 2] = heightmap_gray[engraving_mask].astype(np.uint8)
    heightmap_rgba[engraving_mask, 3] = 255
    heightmap_rgba[~engraving_mask, 3] = 0

    # Convert the file path to lowercase before replacing
    base_file_name = stl_file.lower().replace(".stl", "")
    output_png = base_file_name + "_heightmap.png"
    output_npy = base_file_name + "_heightmap.npy"
    
    img = Image.fromarray(heightmap_rgba)
    img.save(output_png, dpi=(pixels_per_mm * 25.4, pixels_per_mm * 25.4))

    np.save(output_npy, z_clamped)
    return output_npy, output_png, stl_width, stl_height, z_clamped

def heightmap_to_svg_with_png(npy_file, png_file, stl_width, stl_height, output_svg_path):
    """
    Converts a heightmap (.npy) to an SVG file with embedded PNG and contour paths.
    
    :param npy_file: Path to the heightmap Numpy file.
    :param png_file: Path to the heightmap PNG file.
    :param stl_width: Real width of the STL file.
    :param stl_height: Real height of the STL file.
    :param output_svg_path: Path to the final SVG file.
    """
    if not os.path.exists(npy_file) or not os.path.exists(png_file):
        return []

    # Load heightmap data to get dimensions
    z_scaled = np.load(npy_file)
    height_px, width_px = z_scaled.shape
    
    if stl_width == 0 or stl_height == 0:
        return []
        
    scale_factor_x = stl_width / width_px
    scale_factor_y = stl_height / height_px
    
    dwg = svgwrite.Drawing(output_svg_path, size=(f"{stl_width}mm", f"{stl_height}mm"), viewBox=f"0 0 {stl_width} {stl_height}")
    
    with open(png_file, 'rb') as f:
        png_data = f.read()
    base64_data = base64.b64encode(png_data).decode('utf-8')
    data_uri = f"data:image/png;base64,{base64_data}"
    
    image_data = svgwrite.image.Image(data_uri, insert=(0, 0), size=(stl_width, stl_height))
    dwg.add(image_data)

    # Use the alpha channel to find all boundaries between shapes and the background
    img = Image.open(png_file)
    heightmap_rgba = np.array(img)
    binary_mask = heightmap_rgba[:, :, 3] > 0
    
    # Pad the mask to ensure contours on the edge are found
    padded_mask = np.pad(binary_mask, pad_width=1, mode='constant', constant_values=0)
    
    contours = measure.find_contours(padded_mask, 0.5)
    
    if contours:
        # Iterate over all found contours
        for contour in contours:
            # Add a check to ensure it's not a tiny contour and draw it
            if len(contour) > 10:
                # Correct for padding and create path string
                path_str = "M" + " L".join(f"{ (x - 1) * scale_factor_x }, { (y - 1) * scale_factor_y }" for y, x in contour)
                dwg.add(dwg.path(d=path_str, stroke=svgwrite.rgb(255, 0, 0, 'RGB'), fill='none', stroke_width=0.05))
            
    dwg.save()
    return contours

def create_calibration_svg(max_engraving_depth_mm, output_svg_path):
    """
    Creates a calibration SVG file with 5 grayscale squares and depth labels.
    
    :param max_engraving_depth_mm: Maximum depth for the engraving.
    :param output_svg_path: Path to the final SVG file.
    """
    num_steps = 5
    box_size_px = 100
    spacing_px = 50
    text_size_px = 24
    
    total_width_px = num_steps * box_size_px + (num_steps - 1) * spacing_px + 2 * spacing_px
    total_height_px = box_size_px + text_size_px + 2 * spacing_px

    img = Image.new('RGB', (total_width_px, total_height_px), color='white')
    d = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", text_size_px)
    except IOError:
        font = ImageFont.load_default()

    for i in range(num_steps):
        depth_for_step = (i / (num_steps - 1)) * max_engraving_depth_mm
        
        gray_value = int(255 - (depth_for_step / max_engraving_depth_mm) * 255)
        gray_value = max(0, min(255, gray_value))
        
        fill_color = (gray_value, gray_value, gray_value)
        x_pos_px = spacing_px + i * (box_size_px + spacing_px)
        
        d.rectangle([x_pos_px, spacing_px, x_pos_px + box_size_px, spacing_px + box_size_px], fill=fill_color)
        
        text_str = f"{depth_for_step:.2f}mm"
        bbox = d.textbbox((0, 0), text_str, font=font)
        text_width = bbox[2] - bbox[0]
        
        d.text((x_pos_px + box_size_px / 2 - text_width / 2, spacing_px + box_size_px + 5), text_str, fill='black', font=font)

    buffered = io.BytesIO()
    img.save(buffered, format='PNG')
    png_data = buffered.getvalue()
    base64_data = base64.b64encode(png_data).decode('utf-8')
    data_uri = f"data:image/png;base64,{base64_data}"

    dwg = svgwrite.Drawing(output_svg_path, size=(f"{total_width_px}px", f"{total_height_px}px"))
    image_data = svgwrite.image.Image(data_uri, insert=(0, 0), size=(f"{total_width_px}px", f"{total_height_px}px"))
    dwg.add(image_data)
    dwg.save()
    
    messagebox.showinfo("Success", f"Calibration file created: {output_svg_path}\n\n"
                                     "Now engrave this file and measure the actual depths for each gray square. "
                                     "Then, enter the measured values in the 'Actual' column of the table.")

def create_max_depth_svg(max_engraving_depth_mm, output_svg_path):
    """
    Creates a single-square SVG calibration file for max depth.
    
    :param max_engraving_depth_mm: Maximum depth for the engraving.
    :param output_svg_path: Path to the final SVG file.
    """
    box_size_px = 200
    spacing_px = 50
    text_size_px = 24
    
    total_width_px = box_size_px + 2 * spacing_px
    total_height_px = box_size_px + text_size_px + 2 * spacing_px

    img = Image.new('RGB', (total_width_px, total_height_px), color='white')
    d = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", text_size_px)
    except IOError:
        font = ImageFont.load_default()

    fill_color = (0, 0, 0)  # Max depth is pure black
    x_pos_px = spacing_px
    
    d.rectangle([x_pos_px, spacing_px, x_pos_px + box_size_px, spacing_px + box_size_px], fill=fill_color)
    
    text_str = f"{max_engraving_depth_mm:.2f}mm"
    bbox = d.textbbox((0, 0), text_str, font=font)
    text_width = bbox[2] - bbox[0]
    
    d.text((x_pos_px + box_size_px / 2 - text_width / 2, spacing_px + box_size_px + 5), text_str, fill='black', font=font)

    buffered = io.BytesIO()
    img.save(buffered, format='PNG')
    png_data = buffered.getvalue()
    base64_data = base64.b64encode(png_data).decode('utf-8')
    data_uri = f"data:image/png;base64,{base64_data}"

    dwg = svgwrite.Drawing(output_svg_path, size=(f"{total_width_px}px", f"{total_height_px}px"))
    image_data = svgwrite.image.Image(data_uri, insert=(0, 0), size=(f"{total_width_px}px", f"{total_height_px}px"))
    dwg.add(image_data)
    dwg.save()
    
    messagebox.showinfo("Success", f"Max Depth Calibration file created: {output_svg_path}\n\n"
                                     "Engrave this file with your maximum power to measure the actual depth.")


def get_stl_maxz(stl_file):
    if not os.path.exists(stl_file):
        return None
    try:
        mesh = trimesh.load(stl_file)
        return mesh.bounds[1][2]
    except Exception as e:
        return None

def create_preview_image(png_file, contours):
    """
    Creates a PNG preview image with the heightmap and red contour lines.
    
    :param png_file: Path to the heightmap PNG file.
    :param contours: List of contours from skimage.measure.find_contours.
    :return: A PIL Image object.
    """
    img = Image.open(png_file).convert('RGBA')
    draw = ImageDraw.Draw(img)

    for contour in contours:
        # Correct for padding and convert contour points from (row, col) to (x, y)
        line_points = [(p[1] - 1, p[0] - 1) for p in contour]
        draw.line(line_points, fill="red", width=1)
    
    return img

class App:
    def __init__(self, master):
        self.master = master
        master.title("3D Cut Lab")
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabel', background='#f0f0f0')
        self.style.configure('Header.TLabel', font=('Helvetica', 16, 'bold')) # Added this line for the new title label
        self.frame = ttk.Frame(master, padding=15)
        self.frame.pack(fill='both', expand=True)

        self.file_path = tk.StringVar(value="No file selected")
        self.pixels_per_mm = tk.StringVar(value="2.0")
        self.max_engraving_depth = tk.StringVar(value="10.0")
        self.top_z_plane = tk.StringVar(value="")
        self.calibration_points = []
        self.editor = None
        self.current_stl_max_z = None
        self.preview_image = None

        self.create_widgets()

    def create_widgets(self):
        # Added this block for the new title label
        ttk.Label(self.frame, text="3D Cut Lab", style='Header.TLabel').pack(pady=(0, 15))
        
        ttk.Label(self.frame, text="1. Select STL File").pack(anchor='w', pady=(0, 5))
        file_frame = ttk.Frame(self.frame)
        file_frame.pack(fill='x', pady=(0, 10))
        ttk.Entry(file_frame, textvariable=self.file_path, state='readonly').pack(side='left', fill='x', expand=True)
        ttk.Button(file_frame, text="Browse...", command=self.browse_file).pack(side='right', padx=(5, 0))

        ttk.Label(self.frame, text="2. Pixel Density (Pixels per mm)").pack(anchor='w', pady=(0, 5))
        ttk.Entry(self.frame, textvariable=self.pixels_per_mm).pack(fill='x', pady=(0, 10))

        ttk.Label(self.frame, text="3. Engraving Depth and Plane (mm)").pack(anchor='w', pady=(0, 5))
        depth_frame = ttk.Frame(self.frame)
        depth_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(depth_frame, text="Max. Depth").pack(side='left', padx=(0, 5))
        max_depth_entry = ttk.Entry(depth_frame, textvariable=self.max_engraving_depth, width=8)
        max_depth_entry.pack(side='left', padx=(0, 15))
        # Add trace to update calibration points
        self.max_engraving_depth.trace_add('write', self.on_max_depth_change)

        ttk.Label(self.frame, text="4. Top Z Plane (mm)").pack(anchor='w', pady=(0, 5))
        top_z_frame = ttk.Frame(self.frame)
        top_z_frame.pack(fill='x', pady=(0, 10))
        ttk.Entry(top_z_frame, textvariable=self.top_z_plane, width=20).pack(side='left', fill='x', expand=True)
        ttk.Button(top_z_frame, text="Auto-fill from STL", command=self.autofill_top_z).pack(side='right', padx=(5, 0))
        
        ttk.Button(self.frame, text="5. Auto-populate Calibration Points", command=self.auto_populate_targets).pack(fill='x', pady=(10, 5))

        ttk.Label(self.frame, text="6. Calibration Points (Target -> Actual) - Double-click to edit Actual values").pack(anchor='w', pady=(10, 0))
        self.tree = ttk.Treeview(self.frame, columns=("Target", "Actual"), show='headings', height=5)
        self.tree.heading("Target", text="Target (mm)")
        self.tree.heading("Actual", text="Actual (mm)")
        self.tree.column("Target", width=150, anchor='center')
        self.tree.column("Actual", width=150, anchor='center')
        self.tree.pack(fill='x')
        self.tree.bind("<Double-1>", self.on_cell_double_click)
        
        button_frame = ttk.Frame(self.frame)
        button_frame.pack(fill='x', pady=(10, 5))
        ttk.Button(button_frame, text="7. Create Calibration SVG...", command=self.run_calibration_creation).pack(side='left', fill='x', expand=True, padx=(0, 5))
        ttk.Button(button_frame, text="Create Max Depth Calibration SVG...", command=self.run_max_depth_creation).pack(side='right', fill='x', expand=True, padx=(5, 0))

        ttk.Button(self.frame, text="8. Convert & Save As...", command=self.run_conversion).pack(fill='x', pady=(10, 5))
        
        # New Preview Label
        self.preview_label = ttk.Label(self.frame, text="SVG Preview will appear here.")
        self.preview_label.pack(pady=(10, 0))

        self.status_label = ttk.Label(self.frame, text="")
        self.status_label.pack(anchor='w', pady=(5, 0))

    def on_max_depth_change(self, *args):
        """
        Updates the calibration points when the max depth value changes.
        """
        val_str = self.max_engraving_depth.get().replace(',', '.')
        if not val_str:
            return # Exit early if the string is empty
            
        try:
            max_d = float(val_str)
            if max_d <= 0:
                return # Don't update for invalid values
        except ValueError:
            return # Don't update if input is not a number

        num_steps = 5
        self.calibration_points.clear()

        # Get existing actual values to preserve them
        actual_values = [self.tree.item(item, 'values')[1] for item in self.tree.get_children()]

        # Clear existing treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Re-populate with new target values and old actual values
        for i in range(num_steps):
            target_val = (i / (num_steps - 1)) * max_d
            actual_val = actual_values[i] if i < len(actual_values) else ""
            self.calibration_points.append((target_val, actual_val))
            self.tree.insert('', 'end', values=(f"{target_val:.2f}", actual_val))

        self.status_label.config(text="Calibration target values updated.")

    def on_cell_double_click(self, event):
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        
        if not item or column != '#2':
            return
            
        x, y, width, height = self.tree.bbox(item, column)
        
        if self.editor:
            self.editor.destroy()
        
        initial_value = self.tree.item(item, 'values')[1]
        self.editor = ttk.Entry(self.tree)
        self.editor.place(x=x, y=y, width=width, height=height, anchor='nw')
        self.editor.insert(0, initial_value)
        self.editor.focus_set()
        
        def save_value(event=None):
            try:
                new_value = self.editor.get().replace(',', '.')
                # Immediate validation of the new value
                if new_value != '':
                    float(new_value)
                
                self.tree.set(item, column, new_value)
                idx = int(item[1], 16) - 1 if item.startswith('I') else int(self.tree.index(item))
                
                if 0 <= idx < len(self.calibration_points):
                    target_val = self.calibration_points[idx][0]
                    self.calibration_points[idx] = (target_val, new_value)
                
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter a valid number.")
                self.tree.set(item, column, "") # Clear the cell to show error
                
            finally:
                self.editor.destroy()
                self.editor = None
        
        self.editor.bind("<Return>", save_value)
        self.editor.bind("<FocusOut>", save_value)

    def browse_file(self):
        file = filedialog.askopenfilename(defaultextension=".stl", filetypes=[("STL files", "*.stl")])
        if file:
            self.file_path.set(file)
            self.current_stl_max_z = get_stl_maxz(file)
            if self.current_stl_max_z is not None:
                self.top_z_plane.set(f"{self.current_stl_max_z:.2f}")
                self.status_label.config(text="File selected. Top Z plane auto-filled.")
            else:
                self.top_z_plane.set("")
                self.status_label.config(text="File selected. Could not read Z bounds.")

    def autofill_top_z(self):
        if self.current_stl_max_z is not None:
            self.top_z_plane.set(f"{self.current_stl_max_z:.2f}")
            self.status_label.config(text="Top Z plane auto-filled.")
        else:
            self.status_label.config(text="Error: No STL file selected or could not read Z bounds.")
    
    def auto_populate_targets(self):
        try:
            max_d = float(self.max_engraving_depth.get().replace(',', '.'))
            if max_d <= 0:
                raise ValueError("The maximum depth must be greater than 0.")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid depth value. {e}")
            return
        
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        self.calibration_points.clear()
        
        num_steps = 5
        for i in range(num_steps):
            target_val = (i / (num_steps - 1)) * max_d
            self.calibration_points.append((target_val, ""))
            self.tree.insert('', 'end', values=(f"{target_val:.2f}", ""))

        self.status_label.config(text="Target values auto-filled. Double-click to enter 'Actual' values.")

    def run_calibration_creation(self):
        try:
            max_depth_val = float(self.max_engraving_depth.get().replace(',', '.'))
        except ValueError:
            messagebox.showerror("Error", "Error: Maximum depth must be a number.")
            return

        output_svg_path = filedialog.asksaveasfilename(
            defaultextension=".svg",
            filetypes=[("SVG files", "*.svg")],
            initialfile="Calibration.svg"
        )
        if not output_svg_path:
            self.status_label.config(text="Save operation canceled.")
            return

        self.status_label.config(text="Creating calibration file... Please wait.")
        self.master.update_idletasks()
        
        thread = threading.Thread(target=create_calibration_svg, args=(max_depth_val, output_svg_path))
        thread.start()

    def run_max_depth_creation(self):
        try:
            max_depth_val = float(self.max_engraving_depth.get().replace(',', '.'))
        except ValueError:
            messagebox.showerror("Error", "Error: Maximum depth must be a number.")
            return

        output_svg_path = filedialog.asksaveasfilename(
            defaultextension=".svg",
            filetypes=[("SVG files", "*.svg")],
            initialfile="MaxDepthCalibration.svg"
        )
        if not output_svg_path:
            self.status_label.config(text="Save operation canceled.")
            return

        self.status_label.config(text="Creating max depth calibration file... Please wait.")
        self.master.update_idletasks()
        
        thread = threading.Thread(target=create_max_depth_svg, args=(max_depth_val, output_svg_path))
        thread.start()

    def run_conversion(self):
        stl_path = self.file_path.get()
        if stl_path == "No file selected":
            self.status_label.config(text="Please select a file.")
            return
            
        try:
            pixels_per_mm = float(self.pixels_per_mm.get().replace(',', '.'))
            max_depth_val = float(self.max_engraving_depth.get().replace(',', '.'))
            top_z_val = float(self.top_z_plane.get().replace(',', '.'))
            if pixels_per_mm <= 0 or max_depth_val <= 0:
                raise ValueError("The values must be greater than 0.")
        except ValueError as e:
            self.status_label.config(text=f"Error: {e}")
            return

        calibration_points_to_use = []
        
        # Read the most up-to-date values directly from the Treeview
        items = self.tree.get_children()
        if items:
            try:
                for item in items:
                    target, actual = self.tree.item(item, 'values')
                    target_float = float(target.replace(',', '.'))
                    # If the actual value is not provided, use the target value instead
                    if not actual:
                        actual_float = target_float
                    else:
                        actual_float = float(actual.replace(',', '.'))
                    calibration_points_to_use.append((target_float, actual_float))
            except ValueError:
                messagebox.showerror("Invalid Input", "An actual value could not be converted to a number. Please check your entries.")
                return

        output_svg_path = filedialog.asksaveasfilename(
            defaultextension=".svg",
            filetypes=[("SVG files", "*.svg")],
            initialfile=os.path.basename(stl_path).replace(".stl", "_Engraving.svg")
        )
        if not output_svg_path:
            self.status_label.config(text="Save operation canceled.")
            return

        self.status_label.config(text="Processing... Please wait.")
        self.master.update_idletasks()
        
        thread = threading.Thread(target=self.process_files, args=(stl_path, pixels_per_mm, max_depth_val, top_z_val, output_svg_path, calibration_points_to_use))
        thread.start()
    
    def update_preview_label(self, image):
        """Updates the preview label with a new image."""
        if self.preview_label:
            self.preview_label.config(image=image)
            self.preview_label.image = image # Keep a reference to prevent garbage collection

    def process_files(self, stl_path, pixels_per_mm, max_depth_val, top_z_val, output_svg_path, calibration_points_to_use):
        try:
            npy_file, png_file, stl_width, stl_height, z_clamped = stl_to_heightmap_absolute_depth(
                stl_path, 
                pixels_per_mm=pixels_per_mm, 
                max_engraving_depth_mm=max_depth_val,
                zero_z_plane_mm=top_z_val,
                calibration_points=calibration_points_to_use
            )
            
            if not npy_file or not png_file:
                self.status_label.config(text="Error during conversion.")
                return

            contours = heightmap_to_svg_with_png(npy_file, png_file, stl_width, stl_height, output_svg_path)
            
            # --- New Preview Code ---
            try:
                # Open the generated heightmap PNG
                pil_image = create_preview_image(png_file, contours)
                # Resize the image for a good preview size, e.g., max 400x400
                pil_image.thumbnail((400, 400), Image.Resampling.LANCZOS)
                # Create a PhotoImage from the PIL Image
                self.preview_image = ImageTk.PhotoImage(pil_image)
                # Schedule the GUI update on the main thread
                self.master.after(0, self.update_preview_label, self.preview_image)
            except Exception as e:
                # Log the error but don't crash
                print(f"Failed to create image preview: {e}")
            # --- End Preview Code ---
            
            self.status_label.config(text=f"Done! SVG file created: {output_svg_path}")

        except Exception as e:
            self.status_label.config(text=f"An error occurred: {e}")

if __name__ == '__main__':
    root = tk.Tk()
    root.geometry("600x650")
    app = App(root)
    root.mainloop()