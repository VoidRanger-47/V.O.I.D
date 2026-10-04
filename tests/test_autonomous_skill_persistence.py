# tests/test_autonomous_skill_persistence.py
"""
Unit and integration tests for V.O.I.D. Autonomous Evolution & Adaptive Skill Persistence Protocol.
Verifies parsing of ```memory_entry blocks, SQLite persistence, FTS/keyword retrieval,
and CAD file handling workflows.
"""

import sys
import os
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from void_memory.skill_persistence import SkillPersistenceManager, SkillMemoryEntry
from skills.cad_engine import CADEngine, CADManipulationSkill
from skills.library.skill_registry import skill_registry


SAMPLE_MODEL_RESPONSE = """
Here is the solution to parse your DXF file:
You can use `ezdxf` to extract layers and geometries from DXF files.

```python
import ezdxf
doc = ezdxf.readfile("sample.dxf")
for layer in doc.layers:
    print(layer.dxf.name)
```

```memory_entry
[NEW_SKILL_PERSISTENCE]
Domain: CAD/DXF Manipulation
Trigger Keywords: dxf, cad, dwg, step, extract layers, cadquery
Core Tooling: ezdxf, trimesh
Validated Workflow:
1. Verify file exists and is standard ASCII DXF (not binary).
2. Load via recover.readfile(filepath) to bypass minor export corruptions.
3. Iterate over doc.modelspace() to extract LINE, CIRCLE, ARC, and LWPOLYLINE entities.
Failure Modes & Caveats:
- Binary DXF format causes parse failures in ezdxf; convert to ASCII first.
- Corrupted R12 headers require ezdxf.recover mode.
Verification Status: Verified (>90% confidence via official documentation)
```
"""


class TestAutonomousSkillPersistence(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.test_dir, "test_skills.db")
        self.manager = SkillPersistenceManager(db_path=self.test_db)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_parse_memory_entry(self):
        entry = self.manager.parse_memory_entry(SAMPLE_MODEL_RESPONSE)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.domain, "CAD/DXF Manipulation")
        self.assertIn("dxf", entry.trigger_keywords)
        self.assertIn("ezdxf", entry.core_tooling)
        self.assertIn("recover.readfile", entry.validated_workflow)
        self.assertTrue(len(entry.failure_modes) >= 2)
        self.assertIn("Verified", entry.verification_status)

    def test_save_and_retrieve_skill(self):
        entry = self.manager.process_model_output(SAMPLE_MODEL_RESPONSE)
        self.assertIsNotNone(entry)

        # Query matching keywords
        matched = self.manager.find_relevant_skills("how do I extract cad dxf layers?")
        self.assertTrue(len(matched) > 0)
        self.assertEqual(matched[0].domain, "CAD/DXF Manipulation")

        # Context injection formatting
        context = self.manager.build_skill_injection_context("help with dxf parsing")
        self.assertIn("CAD/DXF MANIPULATION", context)
        self.assertIn("ezdxf", context)

    def test_cad_engine_dxf_creation_and_inspection(self):
        dxf_path = os.path.join(self.test_dir, "test_output.dxf")
        entities = [
            {"type": "line", "start": (0, 0), "end": (20, 20), "color": 1},
            {"type": "circle", "center": (10, 10), "radius": 5.0, "color": 2},
            {"type": "text", "text": "V.O.I.D. CAD TEST", "insert": (0, -5)}
        ]

        # Check if ezdxf is installed before running test
        try:
            import ezdxf
        except ImportError:
            self.skipTest("ezdxf not installed in test environment")

        create_res = CADEngine.create_dxf_drawing(dxf_path, entities)
        self.assertTrue(create_res["success"])
        self.assertTrue(os.path.exists(dxf_path))

        inspect_res = CADEngine.inspect_dxf(dxf_path)
        self.assertTrue(inspect_res["success"])
        self.assertGreaterEqual(inspect_res["total_entities"], 3)
        self.assertIn("LINE", inspect_res["entity_breakdown"])
        self.assertIn("CIRCLE", inspect_res["entity_breakdown"])

    def test_skill_registry_integration(self):
        cad_skill = skill_registry.get_skill("cad_manipulator")
        self.assertIsNotNone(cad_skill)
        self.assertEqual(cad_skill.manifest.domain, "engineering_cad")


if __name__ == "__main__":
    unittest.main()
