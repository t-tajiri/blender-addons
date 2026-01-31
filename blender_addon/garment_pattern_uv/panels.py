import bpy
from bpy.types import Panel, UIList


class GARMENT_UV_UL_part_list(UIList):
    # パーツ一覧の UI 表示。
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        layout.prop(item, "name", text="", emboss=False)


class GARMENT_UV_UL_seam_list(UIList):
    # シーム一覧の UI 表示。
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row(align=True)
        row.prop(item, "is_selected", text="")
        row.prop(item, "name", text="", emboss=False)


class GARMENT_UV_PT_sidebar(Panel):
    # 3Dビューのサイドバーに表示する UI パネル。
    bl_label = "Garment UV"
    bl_idname = "GARMENT_UV_PT_sidebar"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Garment UV"

    def draw(self, context):
        layout = self.layout
        props = context.scene.garment_uv

        # 1着分の基本情報入力欄
        layout.label(text="Annotation")
        layout.prop(props, "garment_id")
        layout.prop(props, "garment_type")
        layout.prop(props, "design_reasoning")
        layout.label(text="この下はパーツ一覧です。追加・削除と詳細入力を行います。")

        box = layout.box()
        row = box.row()
        row.template_list(
            "GARMENT_UV_UL_part_list",
            "",
            props,
            "parts",
            props,
            "active_part_index",
            rows=4,
        )

        if 0 <= props.active_part_index < len(props.parts):
            part = props.parts[props.active_part_index]
            # シーム選択
            box.template_list(
                "GARMENT_UV_UL_seam_list",
                "",
                part,
                "seams",
                part,
                "active_seam_index",
                rows=4,
            )

            # 入力欄
            box.prop(part, "label")
            box.prop(part, "modeling_reasoning")
            box.prop(part, "uv_reasoning")


            # シーム
            seam = part.seams[part.active_seam_index]
            box.prop(seam, "seam_reasoning")
        else:
            box.label(text="Add a part to edit details.")

        layout.separator()
        layout.operator("garment_uv.export_json", icon="EXPORT")
        if props.last_error:
            layout.label(text=props.last_error, icon="ERROR")
