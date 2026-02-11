import json
import os

import bpy
from bpy.props import EnumProperty, StringProperty
from bpy.types import Operator

from .data_io import _props_to_dict_filtered, _validate_data_dict
from .reasoning_text import set_reasoning_value


def _tag_redraw(context):
    wm = getattr(context, "window_manager", None)
    if wm is None:
        return
    for window in wm.windows:
        screen = window.screen
        if screen is None:
            continue
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def _find_part(props, part_name):
    for index, part in enumerate(props.parts):
        if part.name == part_name:
            return index, part
    if 0 <= props.active_part_index < len(props.parts):
        return props.active_part_index, props.parts[props.active_part_index]
    return -1, None


def _find_seam(part, seam_name):
    for index, seam in enumerate(part.seams):
        if seam.name == seam_name:
            return index, seam
    if 0 <= part.active_seam_index < len(part.seams):
        return part.active_seam_index, part.seams[part.active_seam_index]
    return -1, None


class GARMENT_UV_OT_paste_reasoning_text(Operator):
    bl_idname = "garment_uv.paste_reasoning_text"
    bl_label = "Paste Reasoning Text"

    target_scope: EnumProperty(
        name="Target Scope",
        items=[
            ("annotation", "Annotation", ""),
            ("part", "Part", ""),
            ("seam", "Seam", ""),
        ],
        default="annotation",
    )
    field_id: EnumProperty(
        name="Field",
        items=[
            ("design_reasoning", "Design Reasoning", ""),
            ("modeling_reasoning", "Modeling Reasoning", ""),
            ("uv_reasoning", "UV Reasoning", ""),
            ("seam_reasoning", "Seam Reasoning", ""),
        ],
        default="design_reasoning",
    )
    part_name: StringProperty(name="Part Name", default="")
    seam_name: StringProperty(name="Seam Name", default="")

    def execute(self, context):
        props = context.scene.garment_uv
        value = context.window_manager.clipboard or ""

        if self.target_scope == "annotation":
            set_reasoning_value(
                props,
                "design_reasoning_text",
                "design_reasoning",
                "annotation",
                "scene",
                "design_reasoning",
                value,
            )
            _tag_redraw(context)
            return {"FINISHED"}

        part_index, part = _find_part(props, self.part_name)
        if part is None:
            self.report({"ERROR"}, "Part not found.")
            return {"CANCELLED"}
        props.active_part_index = part_index

        if self.target_scope == "part":
            if self.field_id == "modeling_reasoning":
                pointer_prop = "modeling_reasoning_text"
                legacy_prop = "modeling_reasoning"
            elif self.field_id == "uv_reasoning":
                pointer_prop = "uv_reasoning_text"
                legacy_prop = "uv_reasoning"
            else:
                self.report({"ERROR"}, "Invalid field for part.")
                return {"CANCELLED"}

            set_reasoning_value(
                part,
                pointer_prop,
                legacy_prop,
                "part",
                part.name or "unnamed_part",
                self.field_id,
                value,
            )
            _tag_redraw(context)
            return {"FINISHED"}

        seam_index, seam = _find_seam(part, self.seam_name)
        if seam is None:
            self.report({"ERROR"}, "Seam not found.")
            return {"CANCELLED"}
        part.active_seam_index = seam_index

        set_reasoning_value(
            seam,
            "seam_reasoning_text",
            "seam_reasoning",
            "seam",
            f"{part.name or 'unnamed_part'}.{seam.name or 'unnamed_seam'}",
            "seam_reasoning",
            value,
        )
        _tag_redraw(context)
        return {"FINISHED"}


class GARMENT_UV_OT_toggle_seam_selection(Operator):
    bl_idname = "garment_uv.toggle_seam_selection"
    bl_label = "Toggle Seam Selection"

    part_name: StringProperty(name="Part Name", default="")
    seam_name: StringProperty(name="Seam Name", default="")

    def execute(self, context):
        props = context.scene.garment_uv
        part_index, part = _find_part(props, self.part_name)
        if part is None:
            self.report({"ERROR"}, "Part not found.")
            return {"CANCELLED"}
        seam_index, seam = _find_seam(part, self.seam_name)
        if seam is None:
            self.report({"ERROR"}, "Seam not found.")
            return {"CANCELLED"}

        seam.is_selected = not seam.is_selected
        if seam.is_selected:
            props.active_part_index = part_index
            part.active_seam_index = seam_index
        _tag_redraw(context)
        return {"FINISHED"}


class GARMENT_UV_OT_export_json(Operator):
    bl_idname = "garment_uv.export_json"
    bl_label = "Export JSON"

    filepath: StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        props = context.scene.garment_uv
        if hasattr(props, "last_error"):
            props.last_error = ""

        data = _props_to_dict_filtered(props, context.object)
        errors = _validate_data_dict(data)
        if errors:
            msg = errors[0]
            if hasattr(props, "last_error"):
                props.last_error = msg
            self.report({"ERROR"}, msg)
            return {"CANCELLED"}

        path = bpy.path.abspath(self.filepath)
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
        except OSError as exc:
            msg = f"Failed to write JSON: {exc}"
            if hasattr(props, "last_error"):
                props.last_error = msg
            self.report({"ERROR"}, msg)
            return {"CANCELLED"}

        self.report({"INFO"}, f"Exported JSON to {path}")
        return {"FINISHED"}

    def invoke(self, context, event):
        del event
        props = context.scene.garment_uv
        if not self.filepath:
            name = props.garment_id.strip() or "annotations"
            self.filepath = bpy.path.abspath(f"//{name}.json")
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
