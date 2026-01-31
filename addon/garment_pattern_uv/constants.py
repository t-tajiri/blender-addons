GARMENT_TYPE_OPTIONS = ("shirt", "jacket", "pants", "skirt", "one-piece")


def _nonempty(value):
    # 非空の文字列かどうかを判定する。
    return isinstance(value, str) and value.strip() != ""


def _garment_type_items(_self, _context):
    # EnumProperty の候補を返す。
    return [(item, item, "") for item in GARMENT_TYPE_OPTIONS]
