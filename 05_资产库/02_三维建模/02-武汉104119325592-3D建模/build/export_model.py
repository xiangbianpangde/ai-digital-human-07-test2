#!/usr/bin/env python3
"""Export the model to the formats a video pipeline can consume.

Run:  blender -b model/<blend> -P build/export_model.py
"""
import json
import os

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, "..", "model"))
NAME = "shaHu9hao_104119325592"


def prep():
    """Drop the rig-only cameras so exports stay clean."""
    c = bpy.data.collections.get("07_相机")
    if c:
        for ob in list(c.objects):
            bpy.data.objects.remove(ob, do_unlink=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    prep()

    path = os.path.join(OUT, NAME + ".glb")
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        use_selection=False,
        export_apply=True,
        export_yup=True,
        export_materials="EXPORT",
    )
    print("GLB  ->", path, os.path.getsize(path))

    path = os.path.join(OUT, NAME + "_blender.fbx")
    bpy.ops.export_scene.fbx(
        filepath=path,
        use_selection=False,
        apply_unit_scale=True,
        global_scale=1.0,
        apply_scale_options="FBX_SCALE_NONE",
        object_types={"MESH", "EMPTY", "CAMERA", "LIGHT"},
        use_mesh_modifiers=True,
        mesh_smooth_type="FACE",
    )
    print("FBX  ->", path, os.path.getsize(path))

    path = os.path.join(OUT, NAME + ".obj")
    bpy.ops.wm.obj_export(
        filepath=path,
        export_selected_objects=False,
        export_materials=True,
        forward_axis="NEGATIVE_Z",
        up_axis="Y",
    )
    print("OBJ  ->", path, os.path.getsize(path))

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "沙湖九号_104119325592.blend"))
    print("BLEND saved")


if __name__ == "__main__":
    main()