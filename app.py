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

try:
    import segno
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
    print("WARNING: segno not installed. QR codes are not available.")

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


# Cache of measured text widths per (text, font) at a 1mm font size
_text_width_cache = {}


def measure_text_width(text, font_size, font=None):
    """Return the rendered width of a single line of text in mm.

    Measures the real glyph outlines with CadQuery when a font is given.
    Text width scales linearly with font size, so each (text, font) pair is
    measured once and cached. Falls back to an estimate of 0.6 * font_size
    per character if CadQuery or the font is not available.
    """
    if not text.strip():
        return 0.0
    if not CADQUERY_AVAILABLE or font is None:
        return len(text) * font_size * 0.6

    key = (text, font)
    if key not in _text_width_cache:
        try:
            bb = (
                cq.Workplane("XY")
                .text(text, 10.0, 0.1, font=font, halign="center", valign="center")
                .val()
                .BoundingBox()
            )
            width_per_mm = bb.xlen / 10.0
        except Exception:
            width_per_mm = len(text) * 0.6
        if len(_text_width_cache) > 5000:
            _text_width_cache.clear()
        _text_width_cache[key] = width_per_mm
    return _text_width_cache[key] * font_size


def calculate_text_dimensions(text, font_size, font_path):
    """Estimate text dimensions based on font size."""
    # Approximate character width as 0.6 * font_size for sans-serif
    char_width = font_size * 0.6
    text_width = len(text) * char_width
    text_height = font_size
    return text_width, text_height


def wrap_text(text, max_width, font_size, font=None):
    """Wrap text to fit within max_width (measured with the given font)."""
    words = text.split()
    lines = []
    current_line = ""
    
    for word in words:
        test_line = f"{current_line} {word}".strip()
        if measure_text_width(test_line, font_size, font) <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    return lines if lines else [text]


def calculate_auto_font_size(text, label_width, label_height, margin, line_wrap=False, margin_horizontal=None, font=None):
    """Calculate the largest font size that fits text within label dimensions.
    
    Args:
        text: Text to fit
        label_width: Label width in mm
        label_height: Label height in mm
        margin: Default margin (used for top/bottom, and left/right if margin_horizontal is None)
        line_wrap: Enable line wrapping
        margin_horizontal: Optional separate horizontal margin (for screw hole clearance)
        font: Registered font name used to measure the text (estimate if None)
    """
    h_margin = margin_horizontal if margin_horizontal is not None else margin
    available_width = label_width - 2 * h_margin
    available_height = label_height - 2 * margin
    max_size = max(available_height * 0.8, 1.0)
    
    if not text or not text.strip() or available_width <= 0:
        return max(min(max_size, 10.0), 1.0)
    
    if not line_wrap:
        # Single line: width scales linearly with font size
        width_at_1mm = measure_text_width(text, 1.0, font)
        font_size = available_width / width_at_1mm if width_at_1mm > 0 else max_size
        return max(min(font_size, max_size), 1.0)  # Minimum 1mm
    
    # Wrapped text: shrink until all lines fit in width and the block fits in height
    font_size = max_size
    while font_size > 1.0:
        lines = wrap_text(text, available_width, font_size, font)
        widest = max(measure_text_width(line, font_size, font) for line in lines)
        block_height = (len(lines) - 1) * font_size * 1.2 + font_size
        if widest <= available_width and block_height <= available_height:
            return font_size
        font_size *= 0.95
    return 1.0  # Minimum 1mm


def check_text_fits(params):
    """Return a warning message if the text does not fit on the label, else None.

    Only relevant for a fixed font size; auto-size always fits (down to 1mm).
    """
    if params.get("auto_size", True) or not params.get("font_size"):
        return None
    
    font = get_font_path(params["font_name"], params["bold"], params["italic"])
    font_size = params["font_size"]
    margin = params["margin"]
    if params["screw_holes"] in [2, 4]:
        h_margin = max(margin, params["screw_hole_edge_distance"] * 2)
    else:
        h_margin = margin
    text_width = params["width"]
    if params.get("qr_enabled"):
        # QR code takes one side of the label, text only gets the remaining width
        text_width = get_qr_layout(
            params["width"], params["height"], margin, h_margin,
            params["qr_size"], params["qr_position"]
        )["text_width"]
    available_width = text_width - 2 * h_margin
    available_height = params["height"] - 2 * margin
    
    if params["use_plate"]:
        texts = [t.strip() for t in params["text"].split(";") if t.strip()]
    else:
        texts = [params["text"]] if params["text"].strip() else []
    
    for text in texts:
        if params["line_wrap"]:
            lines = wrap_text(text, available_width, font_size, font)
        else:
            lines = [text]
        widest = max(measure_text_width(line, font_size, font) for line in lines)
        block_height = (len(lines) - 1) * font_size * 1.2 + font_size
        if widest > available_width + 0.01 or block_height > available_height + 0.01:
            return (
                f"Text '{text}' does not fit the label at {font_size:g}mm "
                f"(needs {widest:.1f} x {block_height:.1f}mm, "
                f"available {available_width:.1f} x {available_height:.1f}mm)"
            )
    return None


def get_qr_matrix(content, error_correction="M"):
    """
    Encode content as a QR code matrix.

    Args:
        content: Text or URL to encode
        error_correction: Error correction level (L, M, Q, H)

    Returns:
        List of rows, each a list of booleans (True = dark module), without quiet zone
    """
    qr = segno.make(content, error=error_correction.lower(), micro=False)
    return [[bool(module) for module in row] for row in qr.matrix]


def qr_matrix_to_rects(matrix):
    """
    Merge dark modules into as few rectangles as possible to keep the CAD model small.

    Horizontal runs per row are merged first, then identical runs in consecutive rows
    are merged vertically.

    Returns:
        List of (col, row, width, height) in module units, row 0 = top
    """
    rects = []
    open_runs = {}  # (start_col, length) -> [start_row, height]

    for row_idx, row in enumerate(matrix + [[]]):
        runs = set()
        col = 0
        while col < len(row):
            if row[col]:
                start = col
                while col < len(row) and row[col]:
                    col += 1
                runs.add((start, col - start))
            else:
                col += 1

        # Close runs that don't continue in this row
        for run in list(open_runs):
            if run in runs:
                open_runs[run][1] += 1
            else:
                start_row, run_height = open_runs.pop(run)
                rects.append((run[0], start_row, run[1], run_height))

        for run in runs:
            if run not in open_runs:
                open_runs[run] = [row_idx, 1]

    return rects


def create_qr_solid(content, size, depth, error_correction="M"):
    """
    Create the dark modules of a QR code as a single solid.

    The QR code is centered at the origin in XY with its bottom face at Z=0.

    Args:
        content: Text or URL to encode
        size: Edge length of the QR code in mm (without quiet zone)
        depth: Height of the modules in mm
        error_correction: Error correction level (L, M, Q, H)

    Returns:
        Tuple of (CadQuery Workplane, number of modules per side)
    """
    matrix = get_qr_matrix(content, error_correction)
    modules = len(matrix)
    module_size = size / modules

    boxes = []
    for col, row, w, h in qr_matrix_to_rects(matrix):
        x = -size / 2 + col * module_size
        y = size / 2 - (row + h) * module_size
        boxes.append(cq.Solid.makeBox(w * module_size, h * module_size, depth, cq.Vector(x, y, 0)))

    solid = boxes[0].fuse(*boxes[1:]).clean() if len(boxes) > 1 else boxes[0]
    return cq.Workplane("XY").add(solid), modules


def get_qr_layout(width, height, margin, margin_horizontal, qr_size=None, qr_position="left"):
    """
    Calculate QR code size/position and the remaining area for text.

    Args:
        width: Label width in mm
        height: Label height in mm
        margin: Margin between edges, QR code and text in mm
        margin_horizontal: Horizontal margin to the label edge (screw hole clearance)
        qr_size: QR edge length in mm (None = fill label height minus margins)
        qr_position: "left" or "right"

    Returns:
        Dict with qr_size, qr_x, text_width (available width incl. its horizontal margins)
        and text_x (center of text area)
    """
    max_size = min(height - 2 * margin, width - 2 * margin_horizontal)
    if qr_size is None or qr_size <= 0:
        qr_size = max_size
    qr_size = max(min(qr_size, max_size), 1.0)

    side = -1 if qr_position == "left" else 1
    qr_x = side * (width / 2 - margin_horizontal - qr_size / 2)

    # Text uses the area between QR code (+ margin) and the opposite edge
    text_width = width - qr_size - margin
    text_x = -side * (qr_size + margin) / 2

    return {"qr_size": qr_size, "qr_x": qr_x, "text_width": text_width, "text_x": text_x}


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
    separate_body=True,
    screw_holes=0,
    screw_hole_diameter=3.0,
    screw_hole_edge_distance=3.0,
    qr_enabled=False,
    qr_content="",
    qr_size=None,
    qr_position="left",
    qr_error_correction="M"
):
    """
    Create a 3D label with text and an optional QR code.
    
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
        screw_holes: Number of screw holes (0, 2, or 4)
        screw_hole_diameter: Diameter of screw holes in mm
        screw_hole_edge_distance: Distance from edge to hole center in mm
        qr_enabled: Add a QR code to the label
        qr_content: Text or URL encoded in the QR code (empty = use label text)
        qr_size: QR code edge length in mm (None = fill label height minus margins)
        qr_position: Position of the QR code, "left" or "right"
        qr_error_correction: QR error correction level (L, M, Q, H)
    
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
    
    # Add screw holes if requested
    if screw_holes in [2, 4]:
        hole_radius = screw_hole_diameter / 2
        edge_dist = screw_hole_edge_distance
        
        if screw_holes == 2:
            # 2 holes: left and right, vertically centered
            hole_positions = [
                (-width/2 + edge_dist, 0),  # Left center
                (width/2 - edge_dist, 0),   # Right center
            ]
        else:  # 4 holes
            # 4 holes: in the corners
            hole_positions = [
                (-width/2 + edge_dist, -height/2 + edge_dist),  # Bottom-left
                (width/2 - edge_dist, -height/2 + edge_dist),   # Bottom-right
                (-width/2 + edge_dist, height/2 - edge_dist),   # Top-left
                (width/2 - edge_dist, height/2 - edge_dist),    # Top-right
            ]
        
        # Create all holes at once using pushPoints
        plate = (
            plate
            .faces(">Z")
            .workplane(centerOption="CenterOfBoundBox")
            .pushPoints(hole_positions)
            .circle(hole_radius)
            .cutThruAll()
        )
    
    # For screw holes, use double edge distance as horizontal margin to avoid text overlap
    if screw_holes in [2, 4]:
        margin_horizontal = max(margin, screw_hole_edge_distance * 2)
    else:
        margin_horizontal = margin
    
    # Ensure text depth doesn't exceed thickness
    text_depth = min(text_depth, thickness - 0.1)
    z_offset = thickness / 2 if not subtract_text else thickness / 2 - text_depth
    
    # QR code takes one side of the label, text gets the remaining area
    qr_object = None
    text_width = width
    text_x = 0
    qr_data = (qr_content or "").strip() or (text or "").strip()
    if qr_enabled and qr_data and QR_AVAILABLE:
        layout = get_qr_layout(width, height, margin, margin_horizontal, qr_size, qr_position)
        qr_wp, _ = create_qr_solid(qr_data, layout["qr_size"], text_depth, qr_error_correction)
        qr_object = qr_wp.translate((layout["qr_x"], 0, z_offset))
        text_width = layout["text_width"]
        text_x = layout["text_x"]
    
    if not text or not text.strip():
        return _combine_label_parts(plate, None, qr_object, subtract_text, separate_body)
    
    # Get font name for CadQuery (fonts are registered with OCP on startup)
    font_path = get_font_path(font_name, bold, italic)
    
    # Calculate font size if auto
    if auto_size or font_size is None:
        font_size = calculate_auto_font_size(text, text_width, height, margin, line_wrap, margin_horizontal, font=font_path)
    
    # Handle line wrapping
    if line_wrap:
        lines = wrap_text(text, text_width - 2 * margin_horizontal, font_size, font=font_path)
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
                .translate((text_x, y_pos, z_offset))
            )
            text_objects.append(text_wp)
        except Exception as e:
            print(f"Error creating text '{line}': {e}")
            # Fallback: create simple placeholder
            continue
    
    combined_text = None
    if text_objects:
        # Combine all text objects
        combined_text = text_objects[0]
        for txt in text_objects[1:]:
            combined_text = combined_text.union(txt)
    
    return _combine_label_parts(plate, combined_text, qr_object, subtract_text, separate_body)


def _combine_label_parts(plate, text, qr, subtract_text, separate_body):
    """
    Combine plate, text and QR code into the final model.
    
    Text and QR code are either kept as separate bodies (assembly) or fused/cut
    into the plate. In subtract mode they are cut into the plate.
    """
    parts = [(name, obj) for name, obj in (("text", text), ("qr", qr)) if obj is not None]
    if not parts:
        return plate
    
    if subtract_text:
        for _, obj in parts:
            plate = plate.cut(obj)
    elif not separate_body:
        for _, obj in parts:
            plate = plate.union(obj)
    
    if not separate_body:
        # Return as single fused body
        return plate
    
    # Return as assembly with separate bodies (text/QR embedded in plate when subtracted)
    colors = {
        "text": cq.Color(1.0, 0.5, 0.0),  # orange
        "qr": cq.Color(0.1, 0.1, 0.1),  # black
    }
    assembly = cq.Assembly()
    assembly.add(plate, name="plate", color=cq.Color(0.83, 0.83, 0.83))  # lightgray
    for name, obj in parts:
        assembly.add(obj, name=name, color=colors[name])
    return assembly


def arrange_labels_on_plate(
    texts,
    label_width,
    label_height,
    plate_width,
    plate_height,
    spacing=0.5,
    consistent_font_size=False,
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
        consistent_font_size: Use same font size for all labels (the largest size that fits every text)
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
    
    # Calculate consistent font size if requested (largest size that fits every text)
    fixed_font_size = None
    if consistent_font_size and label_kwargs.get("auto_size", True):
        margin = label_kwargs.get("margin", 2.0)
        line_wrap = label_kwargs.get("line_wrap", False)
        
        # Calculate horizontal margin for screw holes
        screw_holes = label_kwargs.get("screw_holes", 0)
        screw_hole_edge_distance = label_kwargs.get("screw_hole_edge_distance", 3.0)
        if screw_holes in [2, 4]:
            margin_horizontal = max(margin, screw_hole_edge_distance * 2)
        else:
            margin_horizontal = margin
        
        text_width = label_width
        if label_kwargs.get("qr_enabled", False):
            text_width = get_qr_layout(
                label_width, label_height, margin, margin_horizontal,
                label_kwargs.get("qr_size"), label_kwargs.get("qr_position", "left")
            )["text_width"]
        
        font = get_font_path(
            label_kwargs.get("font_name", "Arial"),
            label_kwargs.get("bold", False),
            label_kwargs.get("italic", False)
        )
        
        # The text that needs the smallest size is not always the longest one
        # (e.g. "WWW" is wider than "iiii"), so take the minimum over all texts
        fixed_font_size = min(
            calculate_auto_font_size(t, text_width, label_height, margin, line_wrap, margin_horizontal, font=font)
            for t in texts
        )
    
    # One QR content per label if the QR field has as many ";"-separated entries as labels
    qr_contents = [q.strip() for q in (label_kwargs.get("qr_content") or "").split(";")]
    if len(qr_contents) != len(texts):
        qr_contents = None
    
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
        
        # Override font size if consistent sizing is enabled
        create_kwargs = label_kwargs.copy()
        if fixed_font_size is not None:
            create_kwargs["font_size"] = fixed_font_size
            create_kwargs["auto_size"] = False
        if qr_contents is not None:
            create_kwargs["qr_content"] = qr_contents[i]
        
        label = create_label(
            text=text,
            width=label_width,
            height=label_height,
            **create_kwargs
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
        "consistent_font_size": data.get("consistentFontSize", False),
        "screw_holes": int(data.get("screwHoles", 0)),
        "screw_hole_diameter": float(data.get("screwHoleDiameter", 3)),
        "screw_hole_edge_distance": float(data.get("screwHoleEdgeDistance", 3)),
        "qr_enabled": data.get("qrEnabled", False),
        "qr_content": data.get("qrContent", ""),
        "qr_size": float(data.get("qrSize")) if data.get("qrSize") and not data.get("qrAutoSize", True) else None,
        "qr_position": data.get("qrPosition", "left"),
        "qr_error_correction": data.get("qrErrorCorrection", "M"),
    }
    return params


def _get_qr_info(params):
    """
    Describe the QR code of the first label for the UI (module count and module size).
    
    Returns:
        Tuple of (info dict or None, error message or None)
    """
    if not params["qr_enabled"]:
        return None, None
    if not QR_AVAILABLE:
        return None, "QR codes require the 'segno' package (pip install segno)"
    
    first_text = params["text"].split(";")[0].strip() if params["use_plate"] else params["text"].strip()
    content = params["qr_content"].split(";")[0].strip() if params["use_plate"] else params["qr_content"].strip()
    content = content or first_text
    if not content:
        return None, None
    
    try:
        modules = len(get_qr_matrix(content, params["qr_error_correction"]))
    except Exception as e:
        return None, f"QR code content too long: {e}"
    
    margin = params["margin"]
    if params["screw_holes"] in [2, 4]:
        margin_horizontal = max(margin, params["screw_hole_edge_distance"] * 2)
    else:
        margin_horizontal = margin
    qr_size = get_qr_layout(
        params["width"], params["height"], margin, margin_horizontal,
        params["qr_size"], params["qr_position"]
    )["qr_size"]
    
    return {
        "modules": modules,
        "size": round(qr_size, 2),
        "module_size": round(qr_size / modules, 3)
    }, None


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
            consistent_font_size=params["consistent_font_size"],
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
            separate_body=params["separate_body"],
            screw_holes=params["screw_holes"],
            screw_hole_diameter=params["screw_hole_diameter"],
            screw_hole_edge_distance=params["screw_hole_edge_distance"],
            qr_enabled=params["qr_enabled"],
            qr_content=params["qr_content"],
            qr_size=params["qr_size"],
            qr_position=params["qr_position"],
            qr_error_correction=params["qr_error_correction"]
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
            separate_body=params["separate_body"],
            screw_holes=params["screw_holes"],
            screw_hole_diameter=params["screw_hole_diameter"],
            screw_hole_edge_distance=params["screw_hole_edge_distance"],
            qr_enabled=params["qr_enabled"],
            qr_content=params["qr_content"],
            qr_size=params["qr_size"],
            qr_position=params["qr_position"],
            qr_error_correction=params["qr_error_correction"]
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
        
        qr_info, error = _get_qr_info(params)
        if error:
            return jsonify({"error": error}), 400
        
        model, error = _generate_model_from_params(params)
        
        if error:
            return jsonify({"error": error}), 400
        
        mesh_data = model_to_mesh_data(model)
        if qr_info:
            mesh_data["qr"] = qr_info
        warning = check_text_fits(params)
        if warning:
            mesh_data["warning"] = warning
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
        _, error = _get_qr_info(params)
        if error:
            return jsonify({"error": error}), 400
        
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
    
    # Never enable the Werkzeug debugger on a public server; opt in locally with FLASK_DEBUG=1
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug, host="0.0.0.0", port=5000)
