import bpy
from bpy.types import Panel, UIList

class GARMENT_UV_UL_part_list(UIList):
    """パーツ一覧の UIList。"""

    def draw_item(
        self, _context, layout, _data, item, _icon, _active_data, _active_propname
    ):
        layout.prop(item, "name", text="", emboss=False)


class GARMENT_UV_UL_seam_list(UIList):
    """シーム一覧の UIList。"""

    def draw_item(
        self, _context, layout, data, item, _icon, _active_data, _active_propname
    ):
        row = layout.row()
        row.alignment = "LEFT"
        row.prop(item, "is_selected", text="")

        name_row = row.row()
        name_row.alignment = "LEFT"
        op = name_row.operator(
            "garment_uv.toggle_seam_selection",
            text=item.name,
            emboss=False,
            depress=item.is_selected,
        )
        op.part_name = getattr(data, "name", "")
        op.seam_name = item.name


class GARMENT_UV_PT_sidebar(Panel):
    """3Dビューのサイドバーに表示する UI パネル。"""

    bl_label = "Garment UV"
    bl_idname = "GARMENT_UV_PT_sidebar"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Garment UV"

    def _foldout(self, box, props, flag_name: str, label: str) -> bool:
        row = box.row()
        icon = "TRIA_DOWN" if getattr(props, flag_name) else "TRIA_RIGHT"
        row.prop(props, flag_name, text=label, icon=icon, emboss=False)
        return getattr(props, flag_name)

    def draw(self, context):
        layout = self.layout
        props = context.scene.garment_uv

        box = layout.box()
        if self._foldout(box, props, "show_annotation", "アノテーション"):
            col = box.column(align=True)
            col.prop(props, "garment_id")
            col.prop(props, "garment_type")
            col.prop(props, "design_reasoning", text="形状理由")

        box = layout.box()
        if self._foldout(box, props, "show_parts", "パーツ"):
            col = box.column()
            col.label(text="パーツ一覧")
            col.template_list(
                "GARMENT_UV_UL_part_list",
                "",
                props,
                "parts",
                props,
                "active_part_index",
                rows=6,
            )

            if 0 <= props.active_part_index < len(props.parts):
                part = props.parts[props.active_part_index]
                detail_box = col.box()
                detail_box.label(text="選択中パーツ詳細")

                detail_box.prop(part, "label")
                detail_box.prop(part, "uv_reasoning", text="形状理由")
                detail_box.prop(part, "modeling_reasoning", text="UV理由")
            else:
                col.label(text="パーツを追加して選択してください。")

        box = layout.box()
        if self._foldout(box, props, "show_seams", "シーム"):
            if 0 <= props.active_part_index < len(props.parts):
                part = props.parts[props.active_part_index]
                seam_col = box.column()
                seam_col.label(text="シーム一覧")
                seam_col.template_list(
                    "GARMENT_UV_UL_seam_list",
                    "",
                    part,
                    "seams",
                    part,
                    "active_seam_index",
                    rows=6,
                )

                if part.seams and 0 <= part.active_seam_index < len(part.seams):
                    seam = part.seams[part.active_seam_index]
                    seam_col.prop(seam, "seam_reasoning", text="シーム理由")
                else:
                    seam_col.label(text="シームを選択してください。")
            else:
                box.label(text="パーツを選択するとシームを編集できます。")

        export_box = layout.box()
        export_box.label(text="エクスポート")
        export_box.operator("garment_uv.export_json", icon="EXPORT")
        if props.last_error:
            export_box.label(text=props.last_error, icon="ERROR")
