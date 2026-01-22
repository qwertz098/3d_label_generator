"""
3D Label Generator - Web UI for creating customizable 3D labels
Uses Flask for web interface and CadQuery for 3D model generation
"""

import os
import io
import json
import tempfile
import math
import sys
import ctypes
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file

# CadQuery imports
try:
    import cadquery as cq
    from cadquery import exporters
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False
    print("WARNING: CadQuery not installed. 3D generation will be simulated.")

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Configuration
FONTS_DIR = Path(__file__).parent / "fonts"
EXPORTS_DIR = Path(__file__).parent / "exports"
EXPORTS_DIR.mkdir(exist_ok=True)

# Model cache to avoid regenerating for export
_model_cache = {
    "params_hash": None,
    "model": None
}


def _compute_params_hash(params_dict):
    """Compute a hash of the parameters to detect changes."""
    import hashlib
    # Sort keys for consistent hashing
    param_str = json.dumps(params_dict, sort_keys=True)
    return hashlib.md5(param_str.encode()).hexdigest()


def _get_cached_model(params_dict):
    """Get cached model if parameters haven't changed."""
    params_hash = _compute_params_hash(params_dict)
    if _model_cache["params_hash"] == params_hash and _model_cache["model"] is not None:
        return _model_cache["model"]
    return None


def _cache_model(params_dict, model):
    """Cache the generated model."""
    _model_cache["params_hash"] = _compute_params_hash(params_dict)
    _model_cache["model"] = model


def register_fonts_with_ocp():
    """Register custom fonts with OpenCASCADE Font Manager."""
    try:
        from OCP.Font import Font_FontMgr, Font_SystemFont, Font_FontAspect
        from OCP.TCollection import TCollection_AsciiString
        
        mgr = Font_FontMgr.GetInstance_s()
        
        registered = 0
        for font_file in FONTS_DIR.glob("*.ttf"):
            try:
                font_path_str = str(font_file)
                font_name = font_file.stem  # e.g., "Roboto-Regular"
                
                # Create Font_SystemFont and register with OpenCASCADE
                font = Font_SystemFont(TCollection_AsciiString(font_name))
                font.SetFontPath(Font_FontAspect.Font_FA_Regular, TCollection_AsciiString(font_path_str))
                
                if mgr.RegisterFont(font, True):
                    registered += 1
            except Exception:
                pass
        
        if registered > 0:
            print(f"Registered {registered} fonts with OpenCASCADE")
    except Exception as e:
        print(f"Warning: Could not register fonts with OCP: {e}")


# Register fonts on startup
register_fonts_with_ocp()

# Available fonts (sans-serif, priority order)
# Only fonts that exist in the fonts folder will be shown
ALL_FONTS = [
    {"name": "Osifont", "base": "osifont", "preview": "Osifont - Technical"},
    {"name": "Overpass", "base": "Overpass", "preview": "Overpass - Modern"},
    {"name": "Roboto", "base": "Roboto", "preview": "Roboto - Clean"},
    {"name": "Open Sans", "base": "OpenSans", "preview": "Open Sans - Readable"},
    {"name": "Lato", "base": "Lato", "preview": "Lato - Elegant"},
    {"name": "Montserrat", "base": "Montserrat", "preview": "Montserrat - Geometric"},
    {"name": "Source Sans 3", "base": "SourceSans3", "preview": "Source Sans 3 - Versatile"},
    {"name": "Nunito", "base": "Nunito", "preview": "Nunito - Rounded"},
    {"name": "Poppins", "base": "Poppins", "preview": "Poppins - Trendy"},
]


def get_available_fonts():
    """Return list of fonts that actually exist in the fonts folder."""
    available = []
    for font in ALL_FONTS:
        # Check for regular variant (ttf or otf)
        regular_file = None
        for ext in [".ttf", ".otf"]:
            candidate = FONTS_DIR / f"{font['base']}-Regular{ext}"
            if candidate.exists():
                regular_file = candidate
                break
            # Try without -Regular suffix (e.g., osifont.ttf)
            candidate = FONTS_DIR / f"{font['base']}{ext}"
            if candidate.exists():
                regular_file = candidate
                break
        
        if regular_file:
            available.append({
                "name": font["name"],
                "base": font["base"],
                "preview": font["preview"]
            })
    
    # Fallback: if no fonts found, use system font
    if not available:
        available.append({
            "name": "System Default",
            "base": "arial",
            "preview": "System Default"
        })
    
    return available

def get_font_name_for_cadquery(font_name, bold=False, italic=False):
    """
    Get the font name for CadQuery.
    
    We register fonts with OCP using filename stems (e.g., "Roboto-Regular").
    CadQuery will use these names to find the fonts.
    
    Returns the registered font name.
    """
    # Map our font names to the base filename (without extension)
    font_base_map = {
        "Osifont": "osifont",
        "Overpass": "Overpass",
        "Roboto": "Roboto",
        "Open Sans": "OpenSans",
        "Lato": "Lato",
        "Montserrat": "Montserrat",
        "Source Sans 3": "SourceSans3",
        "Nunito": "Nunito",
        "Poppins": "Poppins",
        "System Default": "Arial",
    }
    
    # Get the base name
    base = font_base_map.get(font_name, "Arial")
    
    # Osifont doesn't have variants
    if base == "osifont":
        return "osifont"
    
    # System fonts don't need suffix
    if base == "Arial":
        return "Arial"
    
    # Determine variant suffix
    if bold and italic:
        variant = "-BoldItalic"
    elif bold:
        variant = "-Bold"
    elif italic:
        variant = "-Italic"
    else:
        variant = "-Regular"
    
    return f"{base}{variant}"


def get_font_path(font_name, bold=False, italic=False):
    """Get the font name for CadQuery (kept for backwards compatibility)."""
    return get_font_name_for_cadquery(font_name, bold, italic)
    return "arial.ttf"


def calculate_text_dimensions(text, font_size, font_path):
    """Estimate text dimensions based on font size."""
    # Approximate character width as 0.6 * font_size for sans-serif
    char_width = font_size * 0.6
    text_width = len(text) * char_width
    text_height = font_size
    return text_width, text_height


def wrap_text(text, max_width, font_size):
    """Wrap text to fit within max_width."""
    char_width = font_size * 0.6
    max_chars = int(max_width / char_width)
    
    if max_chars <= 0:
        return [text]
    
    words = text.split()
    lines = []
    current_line = ""
    
    for word in words:
        test_line = f"{current_line} {word}".strip()
        if len(test_line) <= max_chars:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    return lines if lines else [text]


def calculate_auto_font_size(text, label_width, label_height, margin, line_wrap=False):
    """Calculate font size to fit text within label dimensions."""
    available_width = label_width - 2 * margin
    available_height = label_height - 2 * margin
    
    if line_wrap:
        # For wrapped text, start with a reasonable size and adjust
        font_size = min(available_height * 0.8, available_width * 0.15)
    else:
        # Single line: fit to width
        char_count = len(text) if text else 1
        font_size = available_width / (char_count * 0.6)
        # Don't exceed height
        font_size = min(font_size, available_height * 0.8)
    
    return max(font_size, 1.0)  # Minimum 1mm


def create_label(
    text,
    width=50.0,
    height=20.0,
    thickness=2.0,
    corner_radius=2.0,
    font_name="Arial",
    font_size=None,
    auto_size=True,
    bold=False,
    italic=False,
    text_depth=0.8,
    margin=2.0,
    line_wrap=False,
    subtract_text=False,
    separate_body=True
):
    """
    Create a 3D label with text.
    
    Args:
        text: The text to display
        width: Label width in mm
        height: Label height in mm
        thickness: Label thickness in mm
        corner_radius: Corner radius in mm
        font_name: Name of the font to use
        font_size: Font size in mm (None for auto)
        auto_size: Whether to auto-size the font
        bold: Use bold font
        italic: Use italic font
        text_depth: Depth of extruded/subtracted text in mm
        margin: Margin from edges in mm
        line_wrap: Enable line wrapping
        subtract_text: If True, subtract text from plate; if False, extrude on top
        separate_body: Keep text as separate body
    
    Returns:
        CadQuery assembly or workplane object
    """
    if not CADQUERY_AVAILABLE:
        return None
    
    # Ensure corner radius doesn't exceed half of smallest dimension
    max_radius = min(width, height) / 2 - 0.1
    corner_radius = min(corner_radius, max_radius)
    corner_radius = max(corner_radius, 0)
    
    # Create base plate
    if corner_radius > 0:
        plate = (
            cq.Workplane("XY")
            .box(width, height, thickness)
            .edges("|Z")
            .fillet(corner_radius)
        )
    else:
        plate = cq.Workplane("XY").box(width, height, thickness)
    
    if not text or not text.strip():
        return plate
    
    # Calculate font size if auto
    if auto_size or font_size is None:
        font_size = calculate_auto_font_size(text, width, height, margin, line_wrap)
    
    # Ensure text depth doesn't exceed thickness
    text_depth = min(text_depth, thickness - 0.1)
    
    # Get font name for CadQuery (fonts are registered with OCP on startup)
    font_path = get_font_path(font_name, bold, italic)
    
    # Handle line wrapping
    if line_wrap:
        lines = wrap_text(text, width - 2 * margin, font_size)
    else:
        lines = [text]
    
    # Calculate total text block height
    line_height = font_size * 1.2
    total_text_height = len(lines) * line_height
    
    # Starting Y position (center the text block)
    start_y = total_text_height / 2 - line_height / 2
    
    # Create text objects
    text_objects = []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        
        y_pos = start_y - i * line_height
        
        try:
            text_wp = (
                cq.Workplane("XY")
                .text(
                    line,
                    fontsize=font_size,
                    distance=text_depth,
                    font=font_path,
                    halign="center",
                    valign="center"
                )
                .translate((0, y_pos, thickness / 2 if not subtract_text else thickness / 2 - text_depth))
            )
            text_objects.append(text_wp)
        except Exception as e:
            print(f"Error creating text '{line}': {e}")
            # Fallback: create simple placeholder
            continue
    
    if not text_objects:
        return plate
    
    # Combine all text objects
    combined_text = text_objects[0]
    for txt in text_objects[1:]:
        combined_text = combined_text.union(txt)
    
    if separate_body:
        # Return as assembly with separate bodies
        assembly = cq.Assembly()
        assembly.add(plate, name="plate", color=cq.Color(0.83, 0.83, 0.83))  # lightgray
        
        if subtract_text:
            # Cut text into plate, text is separate (embedded)
            plate_with_cut = plate.cut(combined_text)
            assembly = cq.Assembly()
            assembly.add(plate_with_cut, name="plate", color=cq.Color(0.83, 0.83, 0.83))  # lightgray
            assembly.add(combined_text, name="text", color=cq.Color(1.0, 0.5, 0.0))  # orange
        else:
            # Text on top of plate
            assembly.add(combined_text, name="text", color=cq.Color(1.0, 0.5, 0.0))  # orange
        
        return assembly
    else:
        # Return as single fused body
        if subtract_text:
            return plate.cut(combined_text)
        else:
            return plate.union(combined_text)


def arrange_labels_on_plate(
    texts,
    label_width,
    label_height,
    plate_width,
    plate_height,
    spacing=0.5,
    **label_kwargs
):
    """
    Arrange multiple labels on a build plate.
    
    Args:
        texts: List of text strings (or semicolon-separated string)
        label_width: Width of each label
        label_height: Height of each label
        plate_width: Build plate width
        plate_height: Build plate height
        spacing: Space between labels (default 0.5mm)
        **label_kwargs: Additional arguments for create_label
    
    Returns:
        Tuple of (assembly, error_message or None)
    """
    if isinstance(texts, str):
        texts = [t.strip() for t in texts.split(";") if t.strip()]
    
    if not texts:
        return None, "No text provided"
    
    # Calculate how many labels fit
    cols = int((plate_width + spacing) / (label_width + spacing))
    rows = int((plate_height + spacing) / (label_height + spacing))
    
    max_labels = cols * rows
    
    if len(texts) > max_labels:
        return None, f"Too many labels ({len(texts)}) for plate size. Maximum: {max_labels} ({cols} columns x {rows} rows)"
    
    if cols < 1 or rows < 1:
        return None, f"Label size ({label_width}x{label_height}mm) too large for plate ({plate_width}x{plate_height}mm)"
    
    assembly = cq.Assembly()
    
    # Calculate starting position (center the grid)
    actual_width = len(texts) if len(texts) < cols else cols
    actual_rows = math.ceil(len(texts) / cols)
    
    start_x = -((actual_width - 1) * (label_width + spacing)) / 2
    start_y = ((actual_rows - 1) * (label_height + spacing)) / 2
    
    for i, text in enumerate(texts):
        col = i % cols
        row = i // cols
        
        x = start_x + col * (label_width + spacing)
        y = start_y - row * (label_height + spacing)
        
        label = create_label(
            text=text,
            width=label_width,
            height=label_height,
            **label_kwargs
        )
        
        if label is not None:
            if isinstance(label, cq.Assembly):
                # Add assembly parts with offset
                for name, obj in label.objects.items():
                    if obj.obj is not None:
                        # Handle different object types
                        try:
                            if hasattr(obj.obj, 'translate'):
                                translated = obj.obj.translate((x, y, 0))
                            elif hasattr(obj.obj, 'moved'):
                                # For shapes, use moved instead
                                from OCP.gp import gp_Trsf, gp_Vec
                                trsf = gp_Trsf()
                                trsf.SetTranslation(gp_Vec(x, y, 0))
                                translated = obj.obj.moved(cq.Location(trsf))
                            else:
                                translated = obj.obj
                            assembly.add(
                                translated,
                                name=f"{name}_{i}",
                                color=obj.color
                            )
                        except Exception as e:
                            print(f"Warning: Could not translate assembly part {name}: {e}")
            else:
                assembly.add(
                    label.translate((x, y, 0)),
                    name=f"label_{i}",
                    color=cq.Color(0.83, 0.83, 0.83)  # lightgray
                )
    
    return assembly, None


def export_model(model, format_type, filename=None):
    """
    Export model to specified format.
    
    Args:
        model: CadQuery model (Workplane or Assembly)
        format_type: 'step', '3mf', or 'stl'
        filename: Optional filename (without extension)
    
    Returns:
        Path to exported file
    """
    if not CADQUERY_AVAILABLE:
        return None
    
    if filename is None:
        filename = "label_export"
    
    filepath = EXPORTS_DIR / f"{filename}.{format_type}"
    
    # High quality tessellation for mesh exports (3MF, STL)
    # Lower tolerance = more triangles = better quality for small text details
    mesh_tolerance = 0.01  # 0.01mm tolerance for fine text details
    angular_tolerance = 0.1  # Angular tolerance in radians
    
    try:
        if isinstance(model, cq.Assembly):
            if format_type.lower() == "step":
                model.save(str(filepath), exportType="STEP")
            elif format_type.lower() == "stl":
                # Export with higher quality
                model.save(str(filepath), exportType="STL")
            elif format_type.lower() == "3mf":
                # For 3MF with assembly, we need to fuse all parts and export
                # CadQuery Assembly.save doesn't support 3MF directly
                # Fuse all parts into a single compound
                compound = None
                for name, obj in model.objects.items():
                    if obj.obj is not None:
                        if hasattr(obj.obj, 'val'):
                            shape = obj.obj.val()
                        else:
                            shape = obj.obj
                        if compound is None:
                            compound = cq.Workplane().add(shape)
                        else:
                            compound = compound.add(shape)
                if compound is not None:
                    # Export with high quality tessellation
                    exporters.export(
                        compound, 
                        str(filepath), 
                        exporters.ExportTypes.THREEMF,
                        tolerance=mesh_tolerance,
                        angularTolerance=angular_tolerance
                    )
                else:
                    return None
            else:
                return None
        else:
            if format_type.lower() == "step":
                exporters.export(model, str(filepath), exporters.ExportTypes.STEP)
            elif format_type.lower() == "stl":
                exporters.export(
                    model, 
                    str(filepath), 
                    exporters.ExportTypes.STL,
                    tolerance=mesh_tolerance,
                    angularTolerance=angular_tolerance
                )
            elif format_type.lower() == "3mf":
                exporters.export(
                    model, 
                    str(filepath), 
                    exporters.ExportTypes.THREEMF,
                    tolerance=mesh_tolerance,
                    angularTolerance=angular_tolerance
                )
            else:
                return None
        
        return filepath
    except Exception as e:
        print(f"Export error: {e}")
        return None


def model_to_mesh_data(model):
    """Convert CadQuery model to mesh data for Three.js visualization."""
    if not CADQUERY_AVAILABLE or model is None:
        # Return dummy data for testing
        return {"meshes": []}
    
    try:
        meshes = []
        
        def process_shape(shape, color=(0.7, 0.7, 0.7), name="mesh"):
            """Process a single shape and return mesh data."""
            try:
                # Tessellate the shape
                tess = shape.tessellate(0.1)  # tolerance
                
                verts = tess[0]  # List of vertices
                tris = tess[1]   # List of triangle indices
                
                if not verts or not tris:
                    return None
                
                vertices = []
                faces = []
                
                # Add vertices
                for v in verts:
                    vertices.extend([float(v.x), float(v.y), float(v.z)])
                
                # Add faces
                for tri in tris:
                    faces.extend([int(tri[0]), int(tri[1]), int(tri[2])])
                
                return {
                    "name": name,
                    "vertices": vertices,
                    "faces": faces,
                    "color": [float(color[0]), float(color[1]), float(color[2])]
                }
            except Exception as e:
                print(f"  Warning: Could not tessellate shape: {e}")
                return None
        
        def process_workplane(wp, color=(0.7, 0.7, 0.7), name="mesh"):
            """Process a CadQuery Workplane object."""
            results = []
            try:
                if hasattr(wp, 'val'):
                    val = wp.val()
                    if val is not None:
                        mesh = process_shape(val, color, name)
                        if mesh:
                            results.append(mesh)
                elif hasattr(wp, 'vals'):
                    for i, s in enumerate(wp.vals()):
                        if s is not None:
                            mesh = process_shape(s, color, f"{name}_{i}")
                            if mesh:
                                results.append(mesh)
            except Exception as e:
                print(f"  Warning: Could not process workplane: {e}")
            return results
        
        if isinstance(model, cq.Assembly):
            for name, obj in model.objects.items():
                color = (0.7, 0.7, 0.7)
                try:
                    if obj.color is not None:
                        # Use toTuple() to get RGBA values
                        rgba = obj.color.toTuple()
                        color = (rgba[0], rgba[1], rgba[2])
                except Exception as e:
                    print(f"  Warning: Could not get color for {name}: {e}")
                
                if obj.obj is None:
                    continue
                
                # Check if it's a Workplane
                if hasattr(obj.obj, 'val') or hasattr(obj.obj, 'vals'):
                    meshes.extend(process_workplane(obj.obj, color, name))
                else:
                    # Try to tessellate directly
                    try:
                        mesh = process_shape(obj.obj, color, name)
                        if mesh:
                            meshes.append(mesh)
                    except Exception as e:
                        print(f"  Warning: Could not process object {name}: {e}")
        else:
            meshes.extend(process_workplane(model, (0.7, 0.7, 0.7), "model"))
        
        return {"meshes": meshes}
    except Exception as e:
        print(f"Mesh conversion error: {e}")
        return {"meshes": [], "error": str(e)}


# Flask Routes

@app.route("/")
def index():
    """Render the main page."""
    return render_template("index.html", fonts=get_available_fonts())


@app.route("/api/fonts")
def api_get_fonts():
    """Get list of available fonts."""
    return jsonify(get_available_fonts())


def _extract_label_params(data):
    """Extract and normalize label parameters from request data."""
    params = {
        "text": data.get("text", "Sample"),
        "width": float(data.get("width", 50)),
        "height": float(data.get("height", 20)),
        "thickness": float(data.get("thickness", 2)),
        "corner_radius": float(data.get("cornerRadius", 2)),
        "font_name": data.get("fontName", "Arial"),
        "font_size": float(data.get("fontSize")) if data.get("fontSize") else None,
        "auto_size": data.get("autoSize", True),
        "bold": data.get("bold", False),
        "italic": data.get("italic", False),
        "text_depth": float(data.get("textDepth", 0.8)),
        "margin": float(data.get("margin", 2)),
        "line_wrap": data.get("lineWrap", False),
        "subtract_text": data.get("subtractText", False),
        "separate_body": data.get("separateBody", True),
        "use_plate": data.get("usePlate", False),
        "plate_width": float(data.get("plateWidth", 200)),
        "plate_height": float(data.get("plateHeight", 200)),
    }
    return params


def _generate_model_from_params(params):
    """Generate model from parameters, using cache if available."""
    # Check cache first
    cached = _get_cached_model(params)
    if cached is not None:
        return cached, None
    
    # Generate new model
    if params["use_plate"] and ";" in params["text"]:
        model, error = arrange_labels_on_plate(
            texts=params["text"],
            label_width=params["width"],
            label_height=params["height"],
            plate_width=params["plate_width"],
            plate_height=params["plate_height"],
            thickness=params["thickness"],
            corner_radius=params["corner_radius"],
            font_name=params["font_name"],
            font_size=params["font_size"],
            auto_size=params["auto_size"],
            bold=params["bold"],
            italic=params["italic"],
            text_depth=params["text_depth"],
            margin=params["margin"],
            line_wrap=params["line_wrap"],
            subtract_text=params["subtract_text"],
            separate_body=params["separate_body"]
        )
        if error:
            return None, error
    else:
        model = create_label(
            text=params["text"],
            width=params["width"],
            height=params["height"],
            thickness=params["thickness"],
            corner_radius=params["corner_radius"],
            font_name=params["font_name"],
            font_size=params["font_size"],
            auto_size=params["auto_size"],
            bold=params["bold"],
            italic=params["italic"],
            text_depth=params["text_depth"],
            margin=params["margin"],
            line_wrap=params["line_wrap"],
            subtract_text=params["subtract_text"],
            separate_body=params["separate_body"]
        )
        error = None
    
    # Cache the model
    if model is not None:
        _cache_model(params, model)
    
    return model, error


@app.route("/api/preview", methods=["POST"])
def generate_preview():
    """Generate 3D preview mesh data."""
    try:
        data = request.get_json()
        params = _extract_label_params(data)
        
        model, error = _generate_model_from_params(params)
        
        if error:
            return jsonify({"error": error}), 400
        
        mesh_data = model_to_mesh_data(model)
        return jsonify(mesh_data)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/export", methods=["POST"])
def export_label():
    """Export label to file format. Uses cached model if parameters haven't changed."""
    try:
        data = request.get_json()
        format_type = data.get("format", "step").lower()
        
        if format_type not in ["step", "stl"]:
            # Note: 3MF export suspended due to quality issues with text tessellation
            return jsonify({"error": f"Unsupported format: {format_type}"}), 400
        
        # Extract parameters and use cached model if available
        params = _extract_label_params(data)
        model, error = _generate_model_from_params(params)
        
        if error:
            return jsonify({"error": error}), 400
        
        if model is None:
            return jsonify({"error": "Failed to generate model"}), 500
        
        # Generate filename from text
        safe_text = "".join(c if c.isalnum() else "_" for c in params["text"][:20])
        filename = f"label_{safe_text}"
        
        filepath = export_model(model, format_type, filename)
        
        if filepath and filepath.exists():
            return send_file(
                filepath,
                as_attachment=True,
                download_name=f"{filename}.{format_type}"
            )
        else:
            return jsonify({"error": "Export failed"}), 500
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/status")
def status():
    """Check system status."""
    return jsonify({
        "cadquery_available": CADQUERY_AVAILABLE,
        "fonts_dir": str(FONTS_DIR),
        "fonts_available": FONTS_DIR.exists(),
        "exports_dir": str(EXPORTS_DIR)
    })


if __name__ == "__main__":
    print("=" * 50)
    print("3D Label Generator")
    print("=" * 50)
    print(f"CadQuery available: {CADQUERY_AVAILABLE}")
    print(f"Fonts directory: {FONTS_DIR}")
    print(f"Exports directory: {EXPORTS_DIR}")
    print("=" * 50)
    print("Starting server at http://localhost:5000")
    print("=" * 50)
    
    app.run(debug=True, host="0.0.0.0", port=5000)
