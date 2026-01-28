import json
import os

import bpy
from bpy.props import StringProperty
from bpy.types import Operator

from .data_io import _props_to_dict_filtered, _validate_data_dict


class GARMENT_UV_OT_export_json(Operator):
    # アノテーションをJSONとして書き出す。
    bl_idname = "garment_uv.export_json"
    bl_label = "Export JSON"

    filepath: StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        props = context.scene.garment_uv
        data = _props_to_dict_filtered(props, context.object)
        errors = _validate_data_dict(data)
        if errors:
            self.report({"ERROR"}, errors[0])
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
            self.report({"ERROR"}, f"Failed to write JSON: {exc}")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Exported JSON to {path}")
        return {"FINISHED"}

    def invoke(self, context, event):
        props = context.scene.garment_uv
        if not self.filepath:
            name = props.garment_id.strip() or "annotations"
            self.filepath = bpy.path.abspath(f"//{name}.json")
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}
