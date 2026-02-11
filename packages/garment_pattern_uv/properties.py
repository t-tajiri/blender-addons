import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import PropertyGroup

from .constants import _garment_type_items
from .mesh_sync import _depsgraph_sync_handler


def _on_active_seam_index_changed(self, _context):
    """When list selection changes, keep the selected seam in sync."""
    if 0 <= self.active_seam_index < len(self.seams):
        self.seams[self.active_seam_index].is_selected = True


def _on_seam_selected(self, context):
    """Checkbox update: keep active seam on last checked, allow multi-selection."""
    props = getattr(context, "scene", None)
    props = getattr(props, "garment_uv", None)
    if props is None:
        return

    for part_index, part in enumerate(props.parts):
        for seam_index, seam in enumerate(part.seams):
            if seam is self:
                if self.is_selected:
                    part.active_seam_index = seam_index
                    props.active_part_index = part_index
                else:
                    if part.active_seam_index == seam_index:
                        next_active = next(
                            (i for i, s in enumerate(part.seams) if s.is_selected),
                            -1,
                        )
                        part.active_seam_index = next_active
                return


class GarmentSeamItem(PropertyGroup):
    """シーム 1 本のアノテーション。"""

    name: StringProperty(name="Name")
    seam_reasoning: StringProperty(name="シーム理由")
    seam_reasoning_text: PointerProperty(type=bpy.types.Text, name="Seam Reasoning Text")
    is_selected: BoolProperty(name="Selected", default=False, update=_on_seam_selected)


class GarmentPartItem(PropertyGroup):
    """パーツ 1 件のアノテーション（シームを含む）。"""

    name: StringProperty(name="Name")
    label: StringProperty(name="ラベル")
    modeling_reasoning: StringProperty(name="形状理由")
    modeling_reasoning_text: PointerProperty(
        type=bpy.types.Text, name="Modeling Reasoning Text"
    )
    uv_reasoning: StringProperty(name="UV理由")
    uv_reasoning_text: PointerProperty(type=bpy.types.Text, name="UV Reasoning Text")
    seams: CollectionProperty(type=GarmentSeamItem)
    active_seam_index: IntProperty(default=-1, update=_on_active_seam_index_changed)


class GarmentAnnotationProperties(PropertyGroup):
    """アノテーション全体の情報（シーンに保持）。"""

    garment_id: StringProperty(name="Garment ID")
    garment_type: EnumProperty(
        name="Garment Type",
        items=_garment_type_items,
    )
    design_reasoning: StringProperty(name="形状理由")
    design_reasoning_text: PointerProperty(type=bpy.types.Text, name="Design Reasoning Text")
    parts: CollectionProperty(type=GarmentPartItem)
    active_part_index: IntProperty(default=-1)
    last_sync_signature: StringProperty(name="Last Sync Signature", default="")
    last_error: StringProperty(name="エラー")

    # UI foldouts (default: closed)
    show_annotation: BoolProperty(name="アノテーションを表示", default=False)
    show_parts: BoolProperty(name="パーツを表示", default=False)
    show_seams: BoolProperty(name="シームを表示", default=False)


def register():
    bpy.types.Scene.garment_uv = bpy.props.PointerProperty(
        type=GarmentAnnotationProperties
    )
    if _depsgraph_sync_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_depsgraph_sync_handler)


def unregister():
    del bpy.types.Scene.garment_uv
    if _depsgraph_sync_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_depsgraph_sync_handler)
