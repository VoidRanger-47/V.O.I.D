# skills/cad_engine.py
"""
V.O.I.D. CAD & Geometric Manipulation Engine
Deterministic CAD processing for 2D DXF and 3D STL/STEP/OBJ meshes.
Powered by ezdxf and trimesh.
"""

import os
from typing import Dict, Any, List, Optional, Tuple
from skills.library.base_skill import BaseSkill, SkillManifest


class CADEngine:
    """
    Core functional implementation of CAD & 3D geometry manipulation.
    """

    @staticmethod
    def inspect_dxf(file_path: str) -> Dict[str, Any]:
        """
        Loads a DXF file, extracts layers, line types, entity counts, and bounding dimensions.
        Prerequisite: pip install ezdxf
        """
        try:
            import ezdxf
            from ezdxf import recover
        except ImportError:
            return {
                "success": False,
                "error": "ezdxf library is not installed. Execute: pip install ezdxf"
            }

        if not os.path.exists(file_path):
            return {"success": False, "error": f"File not found: {file_path}"}

        # Check binary vs ASCII DXF header
        try:
            with open(file_path, "rb") as f:
                header = f.read(20)
                is_binary = b"AutoCAD Binary DXF" in header
        except Exception:
            is_binary = False

        if is_binary:
            return {
                "success": False,
                "error": "Binary DXF format detected. ezdxf strictly supports standard ASCII DXF. "
                         "Please convert binary DXF to ASCII DXF via Autodesk DWG TrueView or LibreCAD."
            }

        try:
            # Use recover mode to handle slightly corrupted or non-standard CAD exports
            doc, auditor = recover.readfile(file_path)
            if auditor.has_errors:
                auditor.print_error_report()
        except Exception as e:
            return {"success": False, "error": f"Failed to parse DXF: {str(e)}"}

        msp = doc.modelspace()

        # Extract Layers
        layers = []
        for layer in doc.layers:
            layers.append({
                "name": layer.dxf.name,
                "color": layer.color,
                "linetype": layer.dxf.linetype,
                "is_locked": layer.is_locked(),
                "is_off": layer.is_off()
            })

        # Count Entities in Modelspace
        entity_counts: Dict[str, int] = {}
        for entity in msp:
            dxftype = entity.dxftype()
            entity_counts[dxftype] = entity_counts.get(dxftype, 0) + 1

        return {
            "success": True,
            "dxf_version": doc.dxfversion,
            "encoding": doc.encoding,
            "layer_count": len(layers),
            "layers": layers,
            "total_entities": sum(entity_counts.values()),
            "entity_breakdown": entity_counts
        }

    @staticmethod
    def create_dxf_drawing(output_path: str, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generates a new ASCII DXF document with custom entities.
        Supported entities: line, circle, arc, text, rectangle.
        """
        try:
            import ezdxf
        except ImportError:
            return {
                "success": False,
                "error": "ezdxf library is not installed. Execute: pip install ezdxf"
            }

        doc = ezdxf.new("R2010")
        msp = doc.modelspace()

        created_count = 0
        for item in entities:
            etype = item.get("type", "").lower()
            layer = item.get("layer", "0")
            color = item.get("color", 7)  # 7 = White/Black default

            if etype == "line":
                start = item.get("start", (0, 0))
                end = item.get("end", (10, 10))
                msp.add_line(start, end, dxfattribs={"layer": layer, "color": color})
                created_count += 1

            elif etype == "circle":
                center = item.get("center", (0, 0))
                radius = item.get("radius", 5.0)
                msp.add_circle(center, radius, dxfattribs={"layer": layer, "color": color})
                created_count += 1

            elif etype == "arc":
                center = item.get("center", (0, 0))
                radius = item.get("radius", 5.0)
                start_angle = item.get("start_angle", 0.0)
                end_angle = item.get("end_angle", 180.0)
                msp.add_arc(center, radius, start_angle, end_angle, dxfattribs={"layer": layer, "color": color})
                created_count += 1

            elif etype == "text":
                text = item.get("text", "")
                insert = item.get("insert", (0, 0))
                height = item.get("height", 2.5)
                msp.add_text(text, dxfattribs={"layer": layer, "color": color, "height": height}).set_placement(insert)
                created_count += 1

            elif etype == "rectangle":
                p1 = item.get("p1", (0, 0))
                p2 = item.get("p2", (10, 10))
                points = [p1, (p2[0], p1[1]), p2, (p1[0], p2[1]), p1]
                msp.add_lwpolyline(points, dxfattribs={"layer": layer, "color": color})
                created_count += 1

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc.saveas(output_path)

        return {
            "success": True,
            "output_path": output_path,
            "entities_created": created_count,
            "dxf_version": "R2010"
        }

    @staticmethod
    def inspect_3d_mesh(file_path: str) -> Dict[str, Any]:
        """
        Inspects 3D CAD mesh (STL, OBJ, GLTF, PLY).
        Extracts vertex/face counts, watertightness, volume, and bounding dimensions.
        Prerequisite: pip install trimesh numpy
        """
        try:
            import trimesh
        except ImportError:
            return {
                "success": False,
                "error": "trimesh library is not installed. Execute: pip install trimesh numpy"
            }

        if not os.path.exists(file_path):
            return {"success": False, "error": f"File not found: {file_path}"}

        try:
            mesh = trimesh.load(file_path, force="mesh")
            is_watertight = bool(mesh.is_watertight)
            volume = float(mesh.volume) if is_watertight else None
            extents = [float(x) for x in mesh.extents]
            bounds = [[float(val) for val in row] for row in mesh.bounds]

            return {
                "success": True,
                "is_watertight": is_watertight,
                "vertices_count": len(mesh.vertices),
                "faces_count": len(mesh.faces),
                "volume": volume,
                "surface_area": float(mesh.area),
                "bounding_box_extents": extents,
                "bounds": bounds,
                "center_mass": [float(x) for x in mesh.center_mass] if is_watertight else None
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to parse 3D mesh: {str(e)}"}


class CADManipulationSkill(BaseSkill):
    """
    Skill wrapper connecting CAD engine to V.O.I.D. SkillRegistry.
    """

    def __init__(self):
        super().__init__(SkillManifest(
            name="cad_manipulator",
            domain="engineering_cad",
            purpose="Inspect, parse, generate, and analyze 2D DXF and 3D STL/OBJ CAD models",
            inputs={
                "action": "inspect_dxf | create_dxf | inspect_3d_mesh",
                "file_path": "Path to target CAD file",
                "entities": "Optional list of entities for creation"
            },
            outputs={"result": "CAD geometry metrics or generated file status"},
            tools=["ezdxf", "trimesh"],
            procedure=[
                "1. Verify input file format and existence",
                "2. Check library dependencies (ezdxf, trimesh)",
                "3. Perform deterministic extraction or file generation",
                "4. Return structured metric telemetry"
            ],
            verification="geometry_integrity_verified",
            failure_modes=["binary_dxf_unsupported", "non_watertight_mesh", "file_not_found"],
            recovery_strategy="Fallback to recover mode for DXF or report specific geometry faults"
        ))

    def execute(self, inputs: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        action = inputs.get("action", "inspect_dxf").lower()
        file_path = inputs.get("file_path", "")

        if action == "inspect_dxf":
            return CADEngine.inspect_dxf(file_path)
        elif action == "create_dxf":
            entities = inputs.get("entities", [])
            return CADEngine.create_dxf_drawing(file_path, entities)
        elif action == "inspect_3d_mesh":
            return CADEngine.inspect_3d_mesh(file_path)
        else:
            return {"success": False, "error": f"Unknown CAD action: {action}"}
