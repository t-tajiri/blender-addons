import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    IntProperty,
    StringProperty,
)
from bpy.types import PropertyGroup

from .constants import _garment_type_items
from .mesh_sync import _depsgraph_sync_handler


def _on_active_seam_index_changed(self, _context):
    """When list selection changes, ensure that seam is marked selected (non-exclusive)."""
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
                        # pick another selected seam in this part, or clear
                        next_active = next(
                            (i for i, s in enumerate(part.seams) if s.is_selected),
                            -1,
                        )
                        part.active_seam_index = next_active
                return

class GarmentSeamItem(PropertyGroup):
    # シーム1件分のアノテーション。
    name: StringProperty(name="Name")
    seam_reasoning: StringProperty(name="シームの説明")
    is_selected: BoolProperty(name="Selected", default=False, update=_on_seam_selected)


class GarmentPartItem(PropertyGroup):
    # パーツ1件分のアノテーション（シームの集合を持つ）。
    name: StringProperty(name="Name")
    label: StringProperty(name="Label")
    modeling_reasoning: StringProperty(name="形状にした理由")
    uv_reasoning: StringProperty(name="UVの配置理由")
    seams: CollectionProperty(type=GarmentSeamItem)
    active_seam_index: IntProperty(default=-1, update=_on_active_seam_index_changed)


class GarmentAnnotationProperties(PropertyGroup):
    # 1着分のアノテーション（シーンに保持）。
    garment_id: StringProperty(name="Garment ID")
    garment_type: EnumProperty(
        name="Garment Type",
        items=_garment_type_items,
    )
    design_reasoning: StringProperty(name="シルエットの設計理由")
    parts: CollectionProperty(type=GarmentPartItem)
    active_part_index: IntProperty(default=-1)
    last_sync_signature: StringProperty(name="Last Sync Signature", default="")


def register():
    # シーンにアノテーション用プロパティを追加する。
    bpy.types.Scene.garment_uv = bpy.props.PointerProperty(
        type=GarmentAnnotationProperties
    )
    if _depsgraph_sync_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_depsgraph_sync_handler)


def unregister():
    # シーンからアノテーション用プロパティを削除する。
    del bpy.types.Scene.garment_uv
    if _depsgraph_sync_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_depsgraph_sync_handler)
