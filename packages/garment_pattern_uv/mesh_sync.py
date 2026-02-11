import bpy

from .constants import _nonempty
from .reasoning_text import get_reasoning_value

_SYNC_GUARD = False


def _part_key(part):
    return part.name or "unnamed_part"


def _seam_key(part, seam):
    return f"{_part_key(part)}.{seam.name or 'unnamed_seam'}"


def _valid_text(text):
    return isinstance(text, bpy.types.Text) and bpy.data.texts.get(text.name) is not None


def _snapshot_props(props):
    parts = {}
    seam_to_part = {}
    for part in props.parts:
        seam_data = {}
        for seam in part.seams:
            seam_data[seam.name] = {
                "seam_reasoning": get_reasoning_value(
                    seam,
                    "seam_reasoning_text",
                    "seam_reasoning",
                    "seam",
                    _seam_key(part, seam),
                    "seam_reasoning",
                ),
                "seam_reasoning_text": seam.seam_reasoning_text
                if _valid_text(seam.seam_reasoning_text)
                else None,
            }
            seam_to_part[seam.name] = part.name
        parts[part.name] = {
            "label": part.label,
            "modeling_reasoning": get_reasoning_value(
                part,
                "modeling_reasoning_text",
                "modeling_reasoning",
                "part",
                _part_key(part),
                "modeling_reasoning",
            ),
            "modeling_reasoning_text": part.modeling_reasoning_text
            if _valid_text(part.modeling_reasoning_text)
            else None,
            "uv_reasoning": get_reasoning_value(
                part,
                "uv_reasoning_text",
                "uv_reasoning",
                "part",
                _part_key(part),
                "uv_reasoning",
            ),
            "uv_reasoning_text": part.uv_reasoning_text
            if _valid_text(part.uv_reasoning_text)
            else None,
            "seams": seam_data,
        }
    return parts, seam_to_part


def _apply_single_rename(removed, added, rename_fn):
    if len(removed) == 1 and len(added) == 1:
        old_name = next(iter(removed))
        new_name = next(iter(added))
        rename_fn(old_name, new_name)


def _vertices_by_group(obj):
    group_index_to_name = {group.index: group.name for group in obj.vertex_groups}
    vertices_by_group = {group.name: set() for group in obj.vertex_groups}
    for vertex in obj.data.vertices:
        for group in vertex.groups:
            if group.weight <= 0:
                continue
            name = group_index_to_name.get(group.group)
            if name is not None:
                vertices_by_group[name].add(vertex.index)
    return vertices_by_group


def _split_group_names(obj):
    seam_groups = []
    part_groups = []
    for group in obj.vertex_groups:
        normalized = group.name.strip().lower()
        if normalized.startswith("seam_"):
            seam_groups.append(group.name)
        elif normalized.startswith("part_"):
            part_groups.append(group.name)
    if seam_groups:
        part_groups = [name for name in part_groups if name not in seam_groups]
    return part_groups, seam_groups


def _seams_for_export(obj, part_names, seam_names, parts_snapshot):
    vertices_by_group = _vertices_by_group(obj)
    seams_by_part = {name: set() for name in part_names}
    for seam_name in seam_names:
        seam_vertices = vertices_by_group.get(seam_name, set())
        for part_name in part_names:
            if seam_vertices & vertices_by_group.get(part_name, set()):
                seams_by_part[part_name].add(seam_name)
    for part_name in part_names:
        part_data = parts_snapshot.get(part_name, {})
        for seam_name, seam_data in part_data.get("seams", {}).items():
            if seam_name in seam_names and _nonempty(
                seam_data.get("seam_reasoning", "")
            ):
                seams_by_part[part_name].add(seam_name)
    return {
        part_name: [name for name in seam_names if name in seams]
        for part_name, seams in seams_by_part.items()
    }


def _seams_for_ui(part_names, seam_names):
    return {part_name: list(seam_names) for part_name in part_names}


def _sync_from_vertex_groups(props, obj):
    if obj is None or obj.type != "MESH":
        return

    part_names, seam_names = _split_group_names(obj)
    signature = f"{obj.name}|parts:{'|'.join(part_names)}|seams:{','.join(seam_names)}"
    if props.last_sync_signature == signature:
        has_invalid_part = any(
            not part.name.strip().lower().startswith("part_") for part in props.parts
        )
        if not has_invalid_part:
            return

    parts, _ = _snapshot_props(props)
    seams_by_part = _seams_for_ui(part_names, seam_names)

    existing_part_names = set(parts.keys())
    current_part_names = set(part_names)
    removed_parts = existing_part_names - current_part_names
    added_parts = current_part_names - existing_part_names

    def _rename_part(old_name, new_name):
        if old_name not in parts:
            return
        parts[new_name] = parts.pop(old_name)

    _apply_single_rename(removed_parts, added_parts, _rename_part)

    if not part_names:
        props.parts.clear()
        props.active_part_index = -1
        props.last_sync_signature = signature
        return

    for part_name in part_names:
        if part_name not in parts:
            parts[part_name] = {
                "label": "",
                "modeling_reasoning": "",
                "modeling_reasoning_text": None,
                "uv_reasoning": "",
                "uv_reasoning_text": None,
                "seams": {},
            }

    props.parts.clear()
    for part_name in part_names:
        part_data = parts.get(part_name, {})
        part = props.parts.add()
        part.name = part_name
        part.label = part_data.get("label", "")
        part.modeling_reasoning = part_data.get("modeling_reasoning", "")
        part.modeling_reasoning_text = part_data.get("modeling_reasoning_text")
        part.uv_reasoning = part_data.get("uv_reasoning", "")
        part.uv_reasoning_text = part_data.get("uv_reasoning_text")
        part.seams.clear()

        for seam_name in seams_by_part.get(part_name, []):
            seam = part.seams.add()
            seam.name = seam_name
            seam_data = part_data.get("seams", {}).get(seam_name, {})
            seam.seam_reasoning = seam_data.get("seam_reasoning", "")
            seam.seam_reasoning_text = seam_data.get("seam_reasoning_text")
        part.active_seam_index = 0 if part.seams else -1

    props.active_part_index = 0 if props.parts else -1
    props.last_sync_signature = signature


def _depsgraph_sync_handler(_scene, depsgraph):
    del depsgraph
    global _SYNC_GUARD
    if _SYNC_GUARD:
        return
    context = bpy.context
    if context is None or context.scene is None:
        return
    obj = context.object
    if obj is None or obj.type != "MESH":
        return
    if obj.mode == "EDIT":
        obj.update_from_editmode()
    props = context.scene.garment_uv
    _SYNC_GUARD = True
    try:
        _sync_from_vertex_groups(props, obj)
    finally:
        _SYNC_GUARD = False
