from .constants import GARMENT_TYPE_OPTIONS, _nonempty
from .mesh_sync import _seams_for_export, _snapshot_props, _split_group_names


def _props_to_dict(props):
    # Blender の PropertyGroup を JSON 用の辞書へ変換する
    data = {
        "garment_id": props.garment_id,
        "garment_type": props.garment_type,
        "design_reasoning": props.design_reasoning,
        "parts": [],
    }
    for part in props.parts:
        part_data = {
            "name": part.name,
            "label": part.label,
            "modeling_reasoning": part.modeling_reasoning,
            "uv_reasoning": part.uv_reasoning,
            "seams": [],
        }
        for seam in part.seams:
            part_data["seams"].append(
                {
                    "name": seam.name,
                    "seam_reasoning": seam.seam_reasoning,
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
    # JSON の辞書から Blender の PropertyGroup に値を流し込む
    props.garment_id = data.get("garment_id", "")
    garment_type_value = data.get("garment_type", "")
    if garment_type_value in GARMENT_TYPE_OPTIONS:
        props.garment_type = garment_type_value
    else:
        props.garment_type = GARMENT_TYPE_OPTIONS[0]
    props.design_reasoning = data.get("design_reasoning", "")

    props.parts.clear()
    for part_data in data.get("parts", []):
        part = props.parts.add()
        part.name = part_data.get("name", "")
        part.label = part_data.get("label", "")
        part.modeling_reasoning = part_data.get("modeling_reasoning", "")
        part.uv_reasoning = part_data.get("uv_reasoning", "")
        part.seams.clear()
        for seam_data in part_data.get("seams", []):
            seam = part.seams.add()
            seam.name = seam_data.get("name", "")
            seam.seam_reasoning = seam_data.get("seam_reasoning", "")
        part.active_seam_index = 0 if part.seams else -1
    props.active_part_index = 0 if props.parts else -1


def _validate_data_dict(data):
    # JSON の辞書が必要なキー・型・内容を満たしているか検証する
    errors = []
    if not isinstance(data, dict):
        return ["ルートはオブジェクトである必要があります。"]

    garment_id = data.get("garment_id")
    garment_type = data.get("garment_type")
    design_reasoning = data.get("design_reasoning")

    if not _nonempty(garment_id):
        errors.append("Garment ID は必須です。")
    if not _nonempty(garment_type):
        errors.append("Garment Type は必須です。")
    elif garment_type not in GARMENT_TYPE_OPTIONS:
        errors.append(
            "Garment Type は次のいずれかでなければなりません: " + ", ".join(GARMENT_TYPE_OPTIONS) + "。"
        )
    if not _nonempty(design_reasoning):
        errors.append("シルエットの設計理由 は必須です。")

    parts = data.get("parts")
    if not isinstance(parts, list) or len(parts) < 1:
        errors.append("Parts は 1 つ以上の要素を持つ配列である必要があります。")
        return errors

    seen_part_names = set()
    for index, part in enumerate(parts):
        if not isinstance(part, dict):
            errors.append(f"Parts[{index}] はオブジェクトである必要があります。")
            continue

        name = part.get("name")
        label = part.get("label")
        modeling_reasoning = part.get("modeling_reasoning")
        uv_reasoning = part.get("uv_reasoning")
        seams = part.get("seams")

        if not _nonempty(name):
            errors.append(f"Name は必須です。")
        elif name in seen_part_names:
            errors.append(f"部位名が重複しています: {name}。")
        else:
            seen_part_names.add(name)

        if not _nonempty(label):
            errors.append("Label は必須です。")
        if not _nonempty(modeling_reasoning):
            errors.append("形状にした理由 は必須です。")
        if not _nonempty(uv_reasoning):
            errors.append("UVの配置理由 は必須です。")
        if not isinstance(seams, list) or len(seams) < 1:
            errors.append("Seams は 1 つ以上の要素を持つ配列である必要があります。")
            continue

        for seam_index, seam in enumerate(seams):
            if not isinstance(seam, dict):
                errors.append(
                    f"Seams[{seam_index}] はオブジェクトである必要があります。"
                )
                continue

            seam_name = seam.get("name")
            seam_reasoning = seam.get("seam_reasoning")

            if not _nonempty(seam_name):
                errors.append("Name は必須です。")
            if not _nonempty(seam_reasoning):
                errors.append("Seam Reasoning は必須です。")

    return errors


def _validate_props(props, obj):
    # PropertyGroup とシーン中のメッシュ状態を突き合わせて検証する
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
            warnings.append(
                f"Missing seams for {part_name}: {', '.join(missing_seams)}"
            )
        if extra_seams:
            warnings.append(
                f"Extra seams for {part_name}: {', '.join(extra_seams)}"
            )

    return errors, warnings


def _format_validation_summary(errors, warnings):
    # UI 表示用に検証結果の概要を整形する
    if errors:
        summary = f"Errors: {len(errors)}"
    else:
        summary = "OK"
    if warnings:
        summary = f"{summary}, Warnings: {len(warnings)}"
    return summary
