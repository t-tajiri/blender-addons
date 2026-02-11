from .constants import GARMENT_TYPE_OPTIONS
from .mesh_sync import _seams_for_export, _snapshot_props, _split_group_names
from .reasoning_text import get_reasoning_value, set_reasoning_value


def _annotation_key(_props):
    return "scene"


def _part_key(part):
    return part.name or "unnamed_part"


def _seam_key(part, seam):
    return f"{_part_key(part)}.{seam.name or 'unnamed_seam'}"


def _props_to_dict(props):
    data = {
        "garment_id": props.garment_id,
        "garment_type": props.garment_type,
        "design_reasoning": get_reasoning_value(
            props,
            "design_reasoning_text",
            "design_reasoning",
            "annotation",
            _annotation_key(props),
            "design_reasoning",
        ),
        "parts": [],
    }
    for part in props.parts:
        part_data = {
            "name": part.name,
            "label": part.label,
            "modeling_reasoning": get_reasoning_value(
                part,
                "modeling_reasoning_text",
                "modeling_reasoning",
                "part",
                _part_key(part),
                "modeling_reasoning",
            ),
            "uv_reasoning": get_reasoning_value(
                part,
                "uv_reasoning_text",
                "uv_reasoning",
                "part",
                _part_key(part),
                "uv_reasoning",
            ),
            "seams": [],
        }
        for seam in part.seams:
            part_data["seams"].append(
                {
                    "name": seam.name,
                    "seam_reasoning": get_reasoning_value(
                        seam,
                        "seam_reasoning_text",
                        "seam_reasoning",
                        "seam",
                        _seam_key(part, seam),
                        "seam_reasoning",
                    ),
                }
            )
        data["parts"].append(part_data)
    return data


def _props_to_dict_filtered(props, obj):
    data = _props_to_dict(props)
    if obj is None or obj.type != "MESH":
        return data
    part_names, seam_names = _split_group_names(obj)
    seams_by_part = _seams_for_export(
        obj, part_names, seam_names, _snapshot_props(props)[0]
    )
    filtered_parts = []
    for part in data["parts"]:
        part_name = part.get("name", "")
        allowed_seams = set(seams_by_part.get(part_name, []))
        part["seams"] = [
            seam for seam in part["seams"] if seam.get("name") in allowed_seams
        ]
        filtered_parts.append(part)
    data["parts"] = filtered_parts
    return data


def _dict_to_props(data, props):
    garment_id_value = data.get("garment_id", "")
    props.garment_id = garment_id_value if isinstance(garment_id_value, str) else ""

    garment_type_value = data.get("garment_type", "")
    if not isinstance(garment_type_value, str):
        garment_type_value = ""
    if garment_type_value in GARMENT_TYPE_OPTIONS:
        props.garment_type = garment_type_value
    else:
        props.garment_type = GARMENT_TYPE_OPTIONS[0]

    design_reasoning_value = data.get("design_reasoning", "")
    if not isinstance(design_reasoning_value, str):
        design_reasoning_value = ""
    props.design_reasoning = design_reasoning_value
    set_reasoning_value(
        props,
        "design_reasoning_text",
        "design_reasoning",
        "annotation",
        _annotation_key(props),
        "design_reasoning",
        design_reasoning_value,
    )

    props.parts.clear()
    for part_data in data.get("parts") or []:
        if not isinstance(part_data, dict):
            continue
        part = props.parts.add()
        part_name_value = part_data.get("name", "")
        part.name = part_name_value if isinstance(part_name_value, str) else ""
        label_value = part_data.get("label", "")
        part.label = label_value if isinstance(label_value, str) else ""

        modeling_value = part_data.get("modeling_reasoning", "")
        if not isinstance(modeling_value, str):
            modeling_value = ""
        part.modeling_reasoning = modeling_value
        set_reasoning_value(
            part,
            "modeling_reasoning_text",
            "modeling_reasoning",
            "part",
            _part_key(part),
            "modeling_reasoning",
            modeling_value,
        )

        uv_value = part_data.get("uv_reasoning", "")
        if not isinstance(uv_value, str):
            uv_value = ""
        part.uv_reasoning = uv_value
        set_reasoning_value(
            part,
            "uv_reasoning_text",
            "uv_reasoning",
            "part",
            _part_key(part),
            "uv_reasoning",
            uv_value,
        )

        part.seams.clear()
        for seam_data in part_data.get("seams") or []:
            if not isinstance(seam_data, dict):
                continue
            seam = part.seams.add()
            seam_name_value = seam_data.get("name", "")
            seam.name = seam_name_value if isinstance(seam_name_value, str) else ""
            seam_value = seam_data.get("seam_reasoning", "")
            if not isinstance(seam_value, str):
                seam_value = ""
            seam.seam_reasoning = seam_value
            set_reasoning_value(
                seam,
                "seam_reasoning_text",
                "seam_reasoning",
                "seam",
                _seam_key(part, seam),
                "seam_reasoning",
                seam_value,
            )
        part.active_seam_index = 0 if part.seams else -1
    props.active_part_index = 0 if props.parts else -1


def _validate_data_dict(data):
    errors = []
    if not isinstance(data, dict):
        return ["ルートはオブジェクトである必要があります。"]

    if "garment_id" in data and not isinstance(data.get("garment_id"), str):
        errors.append("garment_id は文字列である必要があります。")
    if "garment_type" in data and not isinstance(data.get("garment_type"), str):
        errors.append("garment_type は文字列である必要があります。")
    if "design_reasoning" in data and not isinstance(data.get("design_reasoning"), str):
        errors.append("design_reasoning は文字列である必要があります。")

    if "parts" in data and not isinstance(data.get("parts"), list):
        errors.append("parts は配列である必要があります。")
        return errors

    parts = data.get("parts", [])
    for index, part in enumerate(parts):
        if not isinstance(part, dict):
            errors.append(f"parts[{index}] はオブジェクトである必要があります。")
            continue

        for key in ("name", "label", "modeling_reasoning", "uv_reasoning"):
            if key in part and not isinstance(part.get(key), str):
                errors.append(f"parts[{index}].{key} は文字列である必要があります。")

        if "seams" in part and not isinstance(part.get("seams"), list):
            errors.append(f"parts[{index}].seams は配列である必要があります。")
            continue

        for seam_index, seam in enumerate(part.get("seams", [])):
            if not isinstance(seam, dict):
                errors.append(
                    f"parts[{index}].seams[{seam_index}] はオブジェクトである必要があります。"
                )
                continue
            for key in ("name", "seam_reasoning"):
                if key in seam and not isinstance(seam.get(key), str):
                    errors.append(
                        f"parts[{index}].seams[{seam_index}].{key} は文字列である必要があります。"
                    )
    return errors


def _validate_props(props, obj):
    errors = []
    warnings = []

    data = _props_to_dict(props)
    errors.extend(_validate_data_dict(data))

    if obj is None:
        warnings.append("No active object; skipped mesh validation.")
        return errors, warnings

    if obj.type != "MESH":
        errors.append("アクティブなオブジェクトがメッシュではありません。")
        return errors, warnings

    mesh = obj.data
    if "UVMap" not in mesh.uv_layers:
        errors.append("アクティブなメッシュに UVMap がありません。")

    part_group_names, seam_group_names = _split_group_names(obj)
    vg_names = set(part_group_names)
    part_names = {part.name for part in props.parts}

    missing_parts = sorted(name for name in part_names if name not in vg_names)
    extra_parts = sorted(name for name in vg_names if name not in part_names)

    if missing_parts:
        errors.append(f"欠落しているパートの頂点グループ: {', '.join(missing_parts)}")
    if extra_parts:
        warnings.append(f"Vertex groups not in JSON (parts): {', '.join(extra_parts)}")

    parts_snapshot, _ = _snapshot_props(props)
    seams_by_part = _seams_for_export(
        obj, part_group_names, seam_group_names, parts_snapshot
    )
    props_seams = {
        part.name: {seam.name for seam in part.seams} for part in props.parts
    }
    for part_name, expected_seams in seams_by_part.items():
        actual_seams = props_seams.get(part_name, set())
        missing_seams = sorted(set(expected_seams) - actual_seams)
        extra_seams = sorted(actual_seams - set(expected_seams))
        if missing_seams:
            warnings.append(f"Missing seams for {part_name}: {', '.join(missing_seams)}")
        if extra_seams:
            warnings.append(f"Extra seams for {part_name}: {', '.join(extra_seams)}")

    return errors, warnings


def _format_validation_summary(errors, warnings):
    if errors:
        summary = f"Errors: {len(errors)}"
    else:
        summary = "OK"
    if warnings:
        summary = f"{summary}, Warnings: {len(warnings)}"
    return summary
