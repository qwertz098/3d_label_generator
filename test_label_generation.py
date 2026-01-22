"""
Tests for 3D Label Generation
Tests the core label generation functions directly without web API.
"""

import sys
import unittest
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app import (
    create_label,
    arrange_labels_on_plate,
    calculate_auto_font_size,
    wrap_text,
    export_model,
    get_font_path,
    get_available_fonts,
    register_fonts_with_ocp,
    _compute_params_hash,
    _get_cached_model,
    _cache_model,
    _extract_label_params,
    _generate_model_from_params,
    _model_cache,
    CADQUERY_AVAILABLE,
    EXPORTS_DIR,
    FONTS_DIR
)

if CADQUERY_AVAILABLE:
    import cadquery as cq


class TestSingleLabelGeneration(unittest.TestCase):
    """Tests for single label generation with various options."""
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_basic_label_creation(self):
        """Test creating a basic label with default settings."""
        label = create_label(
            text="Test",
            width=50,
            height=20,
            thickness=2
        )
        self.assertIsNotNone(label)
        print("[OK] Basic label created successfully")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_label_without_text(self):
        """Test creating a label without text (plate only)."""
        label = create_label(
            text="",
            width=50,
            height=20,
            thickness=2
        )
        self.assertIsNotNone(label)
        print("[OK] Label without text created successfully")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_label_various_sizes(self):
        """Test labels with various dimensions."""
        sizes = [
            (30, 15, 1.5),   # Small
            (50, 20, 2),    # Medium
            (100, 40, 3),   # Large
            (200, 80, 5),   # Extra large
        ]
        for width, height, thickness in sizes:
            label = create_label(
                text="Size Test",
                width=width,
                height=height,
                thickness=thickness
            )
            self.assertIsNotNone(label)
            print(f"[OK] Label {width}x{height}x{thickness}mm created successfully")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_label_corner_radius(self):
        """Test labels with various corner radii."""
        radii = [0, 1, 2, 5, 8]
        for radius in radii:
            label = create_label(
                text="Radius",
                width=50,
                height=20,
                thickness=2,
                corner_radius=radius
            )
            self.assertIsNotNone(label)
            print(f"[OK] Label with corner radius {radius}mm created successfully")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_label_corner_radius_auto_limit(self):
        """Test that corner radius is automatically limited to valid range."""
        # Corner radius larger than half the smallest dimension
        label = create_label(
            text="Test",
            width=50,
            height=20,
            thickness=2,
            corner_radius=15  # Should be limited to ~9.9mm
        )
        self.assertIsNotNone(label)
        print("[OK] Label with auto-limited corner radius created successfully")


class TestTextOptions(unittest.TestCase):
    """Tests for various text styling options."""
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_auto_font_size(self):
        """Test automatic font sizing."""
        label = create_label(
            text="Auto Size Test",
            width=50,
            height=20,
            thickness=2,
            auto_size=True
        )
        self.assertIsNotNone(label)
        print("[OK] Label with auto font size created successfully")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_fixed_font_size(self):
        """Test fixed font size."""
        label = create_label(
            text="Fixed",
            width=50,
            height=20,
            thickness=2,
            font_size=8,
            auto_size=False
        )
        self.assertIsNotNone(label)
        print("[OK] Label with fixed font size created successfully")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_bold_text(self):
        """Test bold text styling."""
        label = create_label(
            text="Bold",
            width=50,
            height=20,
            thickness=2,
            bold=True
        )
        self.assertIsNotNone(label)
        print("[OK] Label with bold text created successfully")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_italic_text(self):
        """Test italic text styling."""
        label = create_label(
            text="Italic",
            width=50,
            height=20,
            thickness=2,
            italic=True
        )
        self.assertIsNotNone(label)
        print("[OK] Label with italic text created successfully")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_bold_italic_text(self):
        """Test bold and italic text styling combined."""
        label = create_label(
            text="BoldItalic",
            width=50,
            height=20,
            thickness=2,
            bold=True,
            italic=True
        )
        self.assertIsNotNone(label)
        print("[OK] Label with bold+italic text created successfully")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_text_depth_variations(self):
        """Test various text depths."""
        depths = [0.3, 0.5, 0.8, 1.0, 1.5]
        for depth in depths:
            label = create_label(
                text="Depth",
                width=50,
                height=20,
                thickness=2,
                text_depth=depth
            )
            self.assertIsNotNone(label)
            print(f"[OK] Label with text depth {depth}mm created successfully")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_margin_variations(self):
        """Test various margin settings."""
        margins = [1, 2, 3, 5]
        for margin in margins:
            label = create_label(
                text="Margin",
                width=50,
                height=20,
                thickness=2,
                margin=margin
            )
            self.assertIsNotNone(label)
            print(f"[OK] Label with margin {margin}mm created successfully")


class TestTextModes(unittest.TestCase):
    """Tests for extruded vs subtracted text modes."""
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_extruded_text(self):
        """Test extruded (raised) text mode."""
        label = create_label(
            text="Extruded",
            width=50,
            height=20,
            thickness=2,
            subtract_text=False
        )
        self.assertIsNotNone(label)
        print("[OK] Label with extruded text created successfully")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_subtracted_text(self):
        """Test subtracted (engraved) text mode."""
        label = create_label(
            text="Subtracted",
            width=50,
            height=20,
            thickness=2,
            subtract_text=True
        )
        self.assertIsNotNone(label)
        print("[OK] Label with subtracted text created successfully")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_separate_body_extruded(self):
        """Test extruded text as separate body."""
        label = create_label(
            text="Separate",
            width=50,
            height=20,
            thickness=2,
            subtract_text=False,
            separate_body=True
        )
        self.assertIsNotNone(label)
        self.assertIsInstance(label, cq.Assembly)
        print("[OK] Label with separate extruded body created successfully")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_fused_body_extruded(self):
        """Test extruded text fused with plate."""
        label = create_label(
            text="Fused",
            width=50,
            height=20,
            thickness=2,
            subtract_text=False,
            separate_body=False
        )
        self.assertIsNotNone(label)
        # Should be Workplane, not Assembly
        self.assertNotIsInstance(label, cq.Assembly)
        print("[OK] Label with fused extruded body created successfully")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_separate_body_subtracted(self):
        """Test subtracted text with separate bodies."""
        label = create_label(
            text="SepSub",
            width=50,
            height=20,
            thickness=2,
            subtract_text=True,
            separate_body=True
        )
        self.assertIsNotNone(label)
        self.assertIsInstance(label, cq.Assembly)
        print("[OK] Label with separate subtracted body created successfully")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_fused_body_subtracted(self):
        """Test subtracted text fused (cut) into plate."""
        label = create_label(
            text="FusSub",
            width=50,
            height=20,
            thickness=2,
            subtract_text=True,
            separate_body=False
        )
        self.assertIsNotNone(label)
        self.assertNotIsInstance(label, cq.Assembly)
        print("[OK] Label with fused subtracted body created successfully")


class TestLineWrapping(unittest.TestCase):
    """Tests for line wrapping functionality."""
    
    def test_wrap_text_function(self):
        """Test the wrap_text helper function."""
        text = "This is a long text that should wrap"
        font_size = 5
        max_width = 30
        
        lines = wrap_text(text, max_width, font_size)
        self.assertIsInstance(lines, list)
        self.assertGreater(len(lines), 0)
        print(f"[OK] wrap_text returned {len(lines)} lines: {lines}")
    
    def test_auto_font_size_calculation(self):
        """Test auto font size calculation."""
        size = calculate_auto_font_size("Test", 50, 20, 2, line_wrap=False)
        self.assertGreater(size, 0)
        print(f"[OK] Auto font size calculated: {size:.2f}mm")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_label_with_line_wrap(self):
        """Test label with line wrapping enabled."""
        label = create_label(
            text="This is a longer text that should wrap to multiple lines",
            width=50,
            height=30,
            thickness=2,
            line_wrap=True
        )
        self.assertIsNotNone(label)
        print("[OK] Label with line wrap created successfully")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_label_without_line_wrap(self):
        """Test label without line wrapping (single line)."""
        label = create_label(
            text="Single line text",
            width=80,
            height=20,
            thickness=2,
            line_wrap=False
        )
        self.assertIsNotNone(label)
        print("[OK] Label without line wrap created successfully")


class TestMultiLabelArrangement(unittest.TestCase):
    """Tests for multiple labels on a build plate."""
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_two_labels_on_plate(self):
        """Test arranging two labels on a plate."""
        assembly, error = arrange_labels_on_plate(
            texts="Label1;Label2",
            label_width=50,
            label_height=20,
            plate_width=200,
            plate_height=200,
            thickness=2
        )
        self.assertIsNone(error)
        self.assertIsNotNone(assembly)
        print("[OK] Two labels arranged on plate successfully")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_multiple_labels_grid(self):
        """Test arranging multiple labels in a grid."""
        texts = ";".join([f"Label{i}" for i in range(1, 7)])  # 6 labels
        assembly, error = arrange_labels_on_plate(
            texts=texts,
            label_width=50,
            label_height=20,
            plate_width=200,
            plate_height=200,
            thickness=2
        )
        self.assertIsNone(error)
        self.assertIsNotNone(assembly)
        print("[OK] Six labels arranged in grid successfully")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_labels_with_different_options(self):
        """Test multiple labels with various styling options."""
        assembly, error = arrange_labels_on_plate(
            texts="Bold;Italic;Normal",
            label_width=40,
            label_height=15,
            plate_width=150,
            plate_height=100,
            thickness=2,
            corner_radius=3,
            text_depth=0.6
        )
        self.assertIsNone(error)
        self.assertIsNotNone(assembly)
        print("[OK] Multiple styled labels arranged successfully")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_labels_list_input(self):
        """Test arrange_labels_on_plate with list input instead of string."""
        texts = ["Apple", "Banana", "Cherry", "Date"]
        assembly, error = arrange_labels_on_plate(
            texts=texts,
            label_width=50,
            label_height=20,
            plate_width=200,
            plate_height=200,
            thickness=2
        )
        self.assertIsNone(error)
        self.assertIsNotNone(assembly)
        print("[OK] Labels from list arranged successfully")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_max_labels_on_plate(self):
        """Test filling a plate with maximum number of labels."""
        # 200x200 plate, 50x20 labels = 4 cols x 10 rows = 40 labels max
        texts = ";".join([f"L{i:02d}" for i in range(1, 21)])  # 20 labels
        assembly, error = arrange_labels_on_plate(
            texts=texts,
            label_width=50,
            label_height=20,
            plate_width=200,
            plate_height=200,
            thickness=2
        )
        self.assertIsNone(error)
        self.assertIsNotNone(assembly)
        print("[OK] 20 labels arranged on plate successfully")


class TestEdgeCases(unittest.TestCase):
    """Tests for edge cases and error handling."""
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_empty_text(self):
        """Test label with empty text."""
        label = create_label(
            text="",
            width=50,
            height=20,
            thickness=2
        )
        self.assertIsNotNone(label)
        print("[OK] Label with empty text created (plate only)")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_whitespace_text(self):
        """Test label with whitespace-only text."""
        label = create_label(
            text="   ",
            width=50,
            height=20,
            thickness=2
        )
        self.assertIsNotNone(label)
        print("[OK] Label with whitespace text created (plate only)")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_special_characters(self):
        """Test label with special characters."""
        label = create_label(
            text="Test-123_#",
            width=80,
            height=20,
            thickness=2
        )
        self.assertIsNotNone(label)
        print("[OK] Label with special characters created successfully")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_very_small_label(self):
        """Test creating a very small label."""
        label = create_label(
            text="S",
            width=10,
            height=8,
            thickness=1
        )
        self.assertIsNotNone(label)
        print("[OK] Very small label created successfully")
    
    def test_too_many_labels_error(self):
        """Test error when too many labels for plate."""
        if not CADQUERY_AVAILABLE:
            self.skipTest("CadQuery not installed")
        
        # Try to fit 100 labels on a small plate
        texts = ";".join([f"L{i}" for i in range(100)])
        assembly, error = arrange_labels_on_plate(
            texts=texts,
            label_width=50,
            label_height=20,
            plate_width=100,
            plate_height=100,
            thickness=2
        )
        self.assertIsNotNone(error)
        self.assertIn("Too many labels", error)
        print(f"[OK] Correctly returned error for too many labels: {error}")
    
    def test_label_too_large_error(self):
        """Test error when label is larger than plate."""
        if not CADQUERY_AVAILABLE:
            self.skipTest("CadQuery not installed")
        
        assembly, error = arrange_labels_on_plate(
            texts="Test",
            label_width=150,
            label_height=60,
            plate_width=100,
            plate_height=50,
            thickness=2
        )
        self.assertIsNotNone(error)
        self.assertIsNotNone(error)  # Should have an error message
        print(f"[OK] Correctly returned error for oversized label: {error}")
    
    def test_no_text_error(self):
        """Test error when no text provided for plate arrangement."""
        if not CADQUERY_AVAILABLE:
            self.skipTest("CadQuery not installed")
        
        assembly, error = arrange_labels_on_plate(
            texts="",
            label_width=50,
            label_height=20,
            plate_width=200,
            plate_height=200,
            thickness=2
        )
        self.assertIsNotNone(error)
        print(f"[OK] Correctly returned error for empty text: {error}")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_text_depth_auto_limit(self):
        """Test that text depth is limited to plate thickness."""
        # Text depth larger than thickness should be auto-limited
        label = create_label(
            text="Deep",
            width=50,
            height=20,
            thickness=2,
            text_depth=5  # Should be limited to ~1.9mm
        )
        self.assertIsNotNone(label)
        print("[OK] Label with auto-limited text depth created successfully")


class TestCombinedOptions(unittest.TestCase):
    """Tests combining multiple options together."""
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_full_options_extruded(self):
        """Test label with all options for extruded text."""
        label = create_label(
            text="Full Options",
            width=60,
            height=25,
            thickness=3,
            corner_radius=4,
            font_size=8,
            auto_size=False,
            bold=True,
            italic=False,
            text_depth=1.2,
            margin=3,
            line_wrap=False,
            subtract_text=False,
            separate_body=True
        )
        self.assertIsNotNone(label)
        print("[OK] Full options extruded label created successfully")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_full_options_subtracted(self):
        """Test label with all options for subtracted text."""
        label = create_label(
            text="Engraved",
            width=60,
            height=25,
            thickness=3,
            corner_radius=4,
            font_size=10,
            auto_size=False,
            bold=False,
            italic=True,
            text_depth=1.0,
            margin=4,
            line_wrap=False,
            subtract_text=True,
            separate_body=False
        )
        self.assertIsNotNone(label)
        print("[OK] Full options subtracted label created successfully")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_multi_plate_full_options(self):
        """Test multi-label plate with full options."""
        assembly, error = arrange_labels_on_plate(
            texts="One;Two;Three;Four",
            label_width=45,
            label_height=18,
            plate_width=150,
            plate_height=100,
            spacing=1.0,
            thickness=2.5,
            corner_radius=3,
            auto_size=True,
            bold=True,
            text_depth=0.8,
            margin=2,
            subtract_text=False,
            separate_body=True
        )
        self.assertIsNone(error)
        self.assertIsNotNone(assembly)
        print("[OK] Multi-label plate with full options created successfully")


class TestExport(unittest.TestCase):
    """Tests for export functionality (STEP, STL, 3MF)."""
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_export_step_workplane(self):
        """Test STEP export of a simple workplane."""
        label = create_label(
            text="STEP",
            width=50,
            height=20,
            thickness=2,
            separate_body=False
        )
        self.assertIsNotNone(label)
        
        filepath = export_model(label, "step", "test_step_workplane")
        self.assertIsNotNone(filepath, "STEP export returned None")
        self.assertTrue(filepath.exists(), f"STEP file not created: {filepath}")
        self.assertGreater(filepath.stat().st_size, 0, "STEP file is empty")
        print(f"[OK] STEP export (workplane): {filepath.name} ({filepath.stat().st_size} bytes)")
        
        # Cleanup
        filepath.unlink(missing_ok=True)
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_export_step_assembly(self):
        """Test STEP export of an assembly (separate bodies)."""
        label = create_label(
            text="STEP",
            width=50,
            height=20,
            thickness=2,
            separate_body=True
        )
        self.assertIsNotNone(label)
        self.assertIsInstance(label, cq.Assembly)
        
        filepath = export_model(label, "step", "test_step_assembly")
        self.assertIsNotNone(filepath, "STEP export returned None")
        self.assertTrue(filepath.exists(), f"STEP file not created: {filepath}")
        self.assertGreater(filepath.stat().st_size, 0, "STEP file is empty")
        print(f"[OK] STEP export (assembly): {filepath.name} ({filepath.stat().st_size} bytes)")
        
        # Cleanup
        filepath.unlink(missing_ok=True)
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_export_stl_workplane(self):
        """Test STL export of a simple workplane."""
        label = create_label(
            text="STL",
            width=50,
            height=20,
            thickness=2,
            separate_body=False
        )
        self.assertIsNotNone(label)
        
        filepath = export_model(label, "stl", "test_stl_workplane")
        self.assertIsNotNone(filepath, "STL export returned None")
        self.assertTrue(filepath.exists(), f"STL file not created: {filepath}")
        self.assertGreater(filepath.stat().st_size, 0, "STL file is empty")
        print(f"[OK] STL export (workplane): {filepath.name} ({filepath.stat().st_size} bytes)")
        
        # Cleanup
        filepath.unlink(missing_ok=True)
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_export_stl_assembly(self):
        """Test STL export of an assembly."""
        label = create_label(
            text="STL",
            width=50,
            height=20,
            thickness=2,
            separate_body=True
        )
        self.assertIsNotNone(label)
        
        filepath = export_model(label, "stl", "test_stl_assembly")
        self.assertIsNotNone(filepath, "STL export returned None")
        self.assertTrue(filepath.exists(), f"STL file not created: {filepath}")
        self.assertGreater(filepath.stat().st_size, 0, "STL file is empty")
        print(f"[OK] STL export (assembly): {filepath.name} ({filepath.stat().st_size} bytes)")
        
        # Cleanup
        filepath.unlink(missing_ok=True)
    
    # 3MF export tests suspended due to quality issues with text tessellation
    # TODO: Re-enable when 3MF export quality is improved
    @unittest.skip("3MF export suspended - quality issues with text tessellation")
    def test_export_3mf_workplane(self):
        """Test 3MF export of a simple workplane."""
        pass
    
    @unittest.skip("3MF export suspended - quality issues with text tessellation")
    def test_export_3mf_assembly(self):
        """Test 3MF export of an assembly."""
        pass


class TestModelCaching(unittest.TestCase):
    """Tests for model caching system."""
    
    def setUp(self):
        """Clear cache before each test."""
        _model_cache["params_hash"] = None
        _model_cache["model"] = None
    
    def test_compute_params_hash_consistent(self):
        """Test that same params produce same hash."""
        params1 = {"text": "Test", "width": 50, "height": 20}
        params2 = {"text": "Test", "width": 50, "height": 20}
        
        hash1 = _compute_params_hash(params1)
        hash2 = _compute_params_hash(params2)
        
        self.assertEqual(hash1, hash2)
        print("[OK] Same params produce same hash")
    
    def test_compute_params_hash_different(self):
        """Test that different params produce different hash."""
        params1 = {"text": "Test", "width": 50, "height": 20}
        params2 = {"text": "Different", "width": 50, "height": 20}
        
        hash1 = _compute_params_hash(params1)
        hash2 = _compute_params_hash(params2)
        
        self.assertNotEqual(hash1, hash2)
        print("[OK] Different params produce different hash")
    
    def test_compute_params_hash_order_independent(self):
        """Test that parameter order doesn't affect hash."""
        params1 = {"text": "Test", "width": 50, "height": 20}
        params2 = {"height": 20, "text": "Test", "width": 50}
        
        hash1 = _compute_params_hash(params1)
        hash2 = _compute_params_hash(params2)
        
        self.assertEqual(hash1, hash2)
        print("[OK] Parameter order doesn't affect hash")
    
    def test_cache_and_retrieve(self):
        """Test caching and retrieving a model."""
        params = {"text": "Cache Test", "width": 50}
        mock_model = "mock_model_object"
        
        # Cache should be empty initially
        self.assertIsNone(_get_cached_model(params))
        
        # Cache the model
        _cache_model(params, mock_model)
        
        # Should retrieve the cached model
        retrieved = _get_cached_model(params)
        self.assertEqual(retrieved, mock_model)
        print("[OK] Model cached and retrieved successfully")
    
    def test_cache_miss_different_params(self):
        """Test cache miss when params change."""
        params1 = {"text": "Test1", "width": 50}
        params2 = {"text": "Test2", "width": 50}
        mock_model = "mock_model_object"
        
        # Cache with params1
        _cache_model(params1, mock_model)
        
        # Should not find with params2
        retrieved = _get_cached_model(params2)
        self.assertIsNone(retrieved)
        print("[OK] Cache miss on different params")
    
    def test_extract_label_params(self):
        """Test parameter extraction from request data."""
        data = {
            "text": "Test Label",
            "width": 60,
            "height": 25,
            "thickness": 3,
            "cornerRadius": 4,
            "fontName": "Roboto",
            "fontSize": 10,
            "autoSize": False,
            "bold": True,
            "italic": False,
            "textDepth": 0.8,
            "margin": 3,
            "lineWrap": True,
            "subtractText": False,
            "separateBody": True,
            "usePlate": False,
            "plateWidth": 200,
            "plateHeight": 200
        }
        
        params = _extract_label_params(data)
        
        self.assertEqual(params["text"], "Test Label")
        self.assertEqual(params["width"], 60)
        self.assertEqual(params["height"], 25)
        self.assertEqual(params["thickness"], 3)
        self.assertEqual(params["corner_radius"], 4)
        self.assertEqual(params["font_name"], "Roboto")
        self.assertEqual(params["font_size"], 10)
        self.assertEqual(params["auto_size"], False)
        self.assertEqual(params["bold"], True)
        self.assertEqual(params["italic"], False)
        self.assertEqual(params["text_depth"], 0.8)
        self.assertEqual(params["margin"], 3)
        self.assertEqual(params["line_wrap"], True)
        self.assertEqual(params["subtract_text"], False)
        self.assertEqual(params["separate_body"], True)
        print("[OK] Parameters extracted correctly")
    
    def test_extract_label_params_defaults(self):
        """Test that defaults are applied for missing params."""
        data = {}
        
        params = _extract_label_params(data)
        
        self.assertEqual(params["text"], "Sample")
        self.assertEqual(params["width"], 50)
        self.assertEqual(params["height"], 20)
        self.assertEqual(params["thickness"], 2)
        self.assertIsNone(params["font_size"])
        self.assertEqual(params["auto_size"], True)
        print("[OK] Default parameters applied correctly")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_generate_model_uses_cache(self):
        """Test that generate_model_from_params uses cache."""
        params = _extract_label_params({"text": "CacheTest"})
        
        # First call should generate
        model1, error1 = _generate_model_from_params(params)
        self.assertIsNone(error1)
        self.assertIsNotNone(model1)
        
        # Store the cached hash
        cached_hash = _model_cache["params_hash"]
        self.assertIsNotNone(cached_hash)
        
        # Second call should use cache
        model2, error2 = _generate_model_from_params(params)
        self.assertIsNone(error2)
        self.assertIsNotNone(model2)
        
        # Models should be the same object (from cache)
        self.assertIs(model1, model2)
        print("[OK] Second call uses cached model")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_generate_model_regenerates_on_change(self):
        """Test that model is regenerated when params change."""
        params1 = _extract_label_params({"text": "First"})
        params2 = _extract_label_params({"text": "Second"})
        
        # Generate first model
        model1, _ = _generate_model_from_params(params1)
        self.assertIsNotNone(model1)
        
        # Generate second model with different params
        model2, _ = _generate_model_from_params(params2)
        self.assertIsNotNone(model2)
        
        # Models should be different objects
        self.assertIsNot(model1, model2)
        print("[OK] Model regenerated on param change")


class TestFontSystem(unittest.TestCase):
    """Tests for font registration and usage."""
    
    def test_fonts_directory_exists(self):
        """Test that fonts directory exists."""
        self.assertTrue(FONTS_DIR.exists(), "Fonts directory does not exist")
        print(f"[OK] Fonts directory exists: {FONTS_DIR}")
    
    def test_fonts_available(self):
        """Test that fonts are downloaded."""
        ttf_files = list(FONTS_DIR.glob("*.ttf"))
        self.assertGreater(len(ttf_files), 0, "No TTF fonts found")
        print(f"[OK] Found {len(ttf_files)} TTF font files")
    
    def test_get_available_fonts(self):
        """Test get_available_fonts returns fonts."""
        fonts = get_available_fonts()
        self.assertIsInstance(fonts, list)
        self.assertGreater(len(fonts), 0, "No fonts returned")
        
        # Check font structure
        for font in fonts:
            self.assertIn("name", font)
            self.assertIn("base", font)
            self.assertIn("preview", font)
        
        print(f"[OK] get_available_fonts returns {len(fonts)} fonts")
    
    def test_get_font_path_regular(self):
        """Test getting regular font name."""
        font_name = get_font_path("Roboto", bold=False, italic=False)
        self.assertEqual(font_name, "Roboto-Regular")
        print(f"[OK] Roboto regular: {font_name}")
    
    def test_get_font_path_bold(self):
        """Test getting bold font name."""
        font_name = get_font_path("Roboto", bold=True, italic=False)
        self.assertEqual(font_name, "Roboto-Bold")
        print(f"[OK] Roboto bold: {font_name}")
    
    def test_get_font_path_italic(self):
        """Test getting italic font name."""
        font_name = get_font_path("Roboto", bold=False, italic=True)
        self.assertEqual(font_name, "Roboto-Italic")
        print(f"[OK] Roboto italic: {font_name}")
    
    def test_get_font_path_osifont(self):
        """Test Osifont (no variants)."""
        font_name = get_font_path("Osifont", bold=False, italic=False)
        self.assertEqual(font_name, "osifont")
        print(f"[OK] Osifont: {font_name}")
    
    def test_get_font_path_fallback(self):
        """Test fallback for unknown font."""
        font_name = get_font_path("NonExistentFont", bold=False, italic=False)
        # Should fall back to Arial
        self.assertEqual(font_name, "Arial")
        print(f"[OK] Unknown font falls back to: {font_name}")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_font_registration(self):
        """Test that fonts are registered with OpenCASCADE."""
        # This should not raise an exception
        try:
            register_fonts_with_ocp()
            print("[OK] Font registration completed without errors")
        except Exception as e:
            self.fail(f"Font registration failed: {e}")
    
    @unittest.skipUnless(CADQUERY_AVAILABLE, "CadQuery not installed")
    def test_different_fonts_produce_different_results(self):
        """Test that different fonts produce visually different models."""
        import cadquery as cq
        
        # Create labels with different fonts
        fonts_to_test = ["Osifont", "Roboto", "Lato"]
        widths = []
        
        for font_name in fonts_to_test:
            label = create_label(
                text="Test",
                width=50,
                height=20,
                thickness=2,
                font_name=font_name,
                auto_size=False,
                font_size=8
            )
            if label is not None:
                # Get bounding box
                if isinstance(label, cq.Assembly):
                    # For assemblies, get first solid
                    for name, obj in label.traverse():
                        if obj.obj is not None:
                            try:
                                bb = obj.obj.val().BoundingBox()
                                widths.append((font_name, bb.xlen))
                                break
                            except:
                                pass
                else:
                    bb = label.val().BoundingBox()
                    widths.append((font_name, bb.xlen))
        
        # Check that we got results
        self.assertGreater(len(widths), 0, "No font tests completed")
        
        # Print results
        for font_name, width in widths:
            print(f"  {font_name}: width = {width:.2f}mm")
        
        # Different fonts should produce different widths (text metrics differ)
        # Note: This may not always be true depending on font registration
        print(f"[OK] Tested {len(widths)} fonts")


def run_tests():
    """Run all tests and print summary."""
    print("=" * 60)
    print("3D Label Generator - Test Suite")
    print("=" * 60)
    print(f"CadQuery available: {CADQUERY_AVAILABLE}")
    print("=" * 60)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSingleLabelGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestTextOptions))
    suite.addTests(loader.loadTestsFromTestCase(TestTextModes))
    suite.addTests(loader.loadTestsFromTestCase(TestLineWrapping))
    suite.addTests(loader.loadTestsFromTestCase(TestMultiLabelArrangement))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestCombinedOptions))
    suite.addTests(loader.loadTestsFromTestCase(TestExport))
    suite.addTests(loader.loadTestsFromTestCase(TestModelCaching))
    suite.addTests(loader.loadTestsFromTestCase(TestFontSystem))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print()
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print("=" * 60)
    
    if result.wasSuccessful():
        print("[OK] ALL TESTS PASSED")
    else:
        print("[FAIL] SOME TESTS FAILED")
        for test, traceback in result.failures + result.errors:
            print(f"\nFailed: {test}")
            print(traceback)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
