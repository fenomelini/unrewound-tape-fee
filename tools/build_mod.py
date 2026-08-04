#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import struct
import subprocess
import tempfile
from pathlib import Path


GAME_BUILD = "23896268"
ENGINE_VERSION = "5.4.4"
PACKAGE_TAG = bytes.fromhex("c1 83 2a 9e")
LOCRES_MAGIC = bytes.fromhex("0e147475674a03fc4a15909dc3377f1b")
LOCALIZATION_BASE_PAK_SHA256 = "dc5430e8bf9c6d610ced1f80665400295a909a7c0cc2810ed0318771491a2606"

SCANNER = Path("RetroRewind/Content/VideoStore/asset/prop/DropBox/Scanner_Dropbox")
CHECKOUT = Path("RetroRewind/Content/VideoStore/asset/prop/CheckOut/UI_Screen_Checkout_Fees")
FEE_TASK = Path("RetroRewind/Content/VideoStore/core/ai/Task/BTTask_Checkout-Fees")

SOURCE = {
    SCANNER.with_suffix(".uasset"): (19373, "e94fc5c3b97834f3fa2e93b4d2102576b2adf8023adb53d6b550e684ad924701"),
    SCANNER.with_suffix(".uexp"): (16977, "4356e732a4fe8402216932ed7ea0def1cc44c683f06d1895ff175ef161e7ba06"),
    CHECKOUT.with_suffix(".uasset"): (9950, "1dbcd8cb008550834460a434247968f6b22dffaf822f6444e0b0d8f8e9075073"),
    CHECKOUT.with_suffix(".uexp"): (9307, "de1ca3cb95868000c3ff91277c02d15a0f03904a69aec14899c5c3190a25f582"),
    FEE_TASK.with_suffix(".uasset"): (34995, "269416f1f8b1312dd14d86fc03a018576ae375bb8fd252edb293b83ebb512a70"),
    FEE_TASK.with_suffix(".uexp"): (79230, "7149b15743357a65cce54278d3955dc86095ece434422123ad477a5d779e1e66"),
}

SCANNER_OUTPUT = {
    "uasset": "d7950063fc518266c8af1945dd6e2193ac91d4b47b41ad1734de7378dd4a7932",
    "uexp": "a6974a94396147c62b7237e6a80eb8a1a50aa2b657d4b1ce04e9d91ee16bd391",
}
CHECKOUT_OUTPUT_UEXP = "56178f742bb08a573102249f7e2cd15f2d214a716bd94e271ad5be94ef061dc9"
FEE_TASK_OUTPUT = {
    "standalone": "ce0e9a87ec87f3d7d8316a660e3da7520b4a70fae49bf123e5a8768ae262f502",
    "employee-fee-policy": "4c0ed1a63cdf3cf88b07b05ebfb71d595aee69fa69a868cb1df33b00b1703c60",
}
FEE_TASK_STRUCTURAL = {
    "uasset": "760f08a168fc84883d91474e4e971583174e2c8816f379e99258a85af587ab0b",
    "uexp": "bfaa5fbea03bee43b1ba3836ed6a40cae180e59a8a1eb50863ae5733345cb6a6",
}

ANSWER_SITES = (
    (0xB684, bytes.fromhex("00 00 00 00"), 8),
    (0xB6AB, bytes.fromhex("00 00 00 00"), 7),
    (0xB6D2, bytes.fromhex("00 00 00 00"), 6),
    (0xB6F9, bytes.fromhex("cd cc 4c 3e"), 5),
    (0xB720, bytes.fromhex("00 00 00 00"), 4),
    (0xB747, bytes.fromhex("33 33 73 3f"), 3),
    (0xB76E, bytes.fromhex("00 00 00 00"), 2),
    (0xB795, bytes.fromhex("00 00 00 00"), 1),
    (0xB7BC, bytes.fromhex("00 00 00 00"), 0),
)
CHARGE_SITES = {
    "damage": (
        (0xC41B, bytes.fromhex("66 66 66 3f"), "normal"),
        (0xC59E, bytes.fromhex("48 e1 7a 3f"), "complaint-handler"),
    ),
    "late": (
        (0xC469, bytes.fromhex("33 33 73 3f"), "normal"),
        (0xC5EC, bytes.fromhex("00 00 80 3f"), "complaint-handler"),
    ),
    "rewind": (
        (0xC490, bytes.fromhex("00 00 00 00"), "normal"),
        (0xC613, bytes.fromhex("00 00 00 00"), "complaint-handler"),
    ),
}
ALWAYS = bytes.fromhex("00 00 80 3f")

LOCALIZATION_NAMESPACE = "UnrewoundTapeFeeUI"
LOCALIZATION_NAMESPACE_HASH = 0x640174CB
LOCALIZED_TEXTS = {
    "title": {
        "source": "Unrewound",
        "key": "UI_Screen_Checkout_Fees_ErrorType2_Title",
        "key_hash": 0x60D9DB6B,
        "source_hash": 0xD7809FF6,
        "offset": 0x0FE0,
    },
    "description": {
        "source": "Tape returned without rewinding",
        "key": "ErrorType2_DescKey",
        "key_hash": 0x11E896F2,
        "source_hash": 0x3396011D,
        "offset": 0x1386,
    },
}
TRANSLATIONS = {
    "de": ("Rückspulgebühr", "Die Kassette wurde nicht zurückgespult."),
    "en": ("Rewind Fee", "The tape was not rewound."),
    "es": ("Cargo por rebobinado", "La cinta no fue rebobinada."),
    "fr": ("Frais de rembobinage", "La cassette n'a pas été rembobinée."),
    "it": ("Penale di riavvolgimento", "La videocassetta non è stata riavvolta."),
    "ja": ("巻き戻し料金", "テープは巻き戻されていません。"),
    "pt": ("Taxa de rebobinagem", "A cassete não foi rebobinada."),
    "pt-BR": ("Taxa de rebobinamento", "A fita não foi rebobinada."),
    "ru": ("Плата за перемотку", "Кассета не была перемотана."),
    "zh": ("倒带费", "录像带未倒带。"),
    "zh-Hant": ("倒帶費", "錄影帶未倒帶。"),
}
DIALOGUE_TEXT = {
    "namespace": "",
    "namespace_hash": 0x19D0CB9C,
    "key": "57A6B73F4F14739C40A5AEBEFE917025",
    "key_hash": 0x7CCC344C,
    "source_hash": 0x73ECBE21,
}
DIALOGUE_TRANSLATIONS = {
    "de": "Hey. Der Film war so gut, dass ich weggepennt bin und vergessen hab, ihn zurückzuspulen. Bitte, Kumpel.",
    "en": "Yo. The movie was so good that I pass out and forget to rewind it. Please, bro.",
    "es": "Ey. La peli era tan buena que me quedé frito y se me olvidó rebobinarla. Porfa, tío.",
    "fr": "Yo. Le film était tellement bien que je me suis endormi et j'ai oublié de le rembobiner. S'il te plaît, mec.",
    "it": "Ehi. Il film era così bello che sono crollato e mi sono dimenticato di riavvolgerlo. Ti prego, amico.",
    "ja": "なあ。映画がよすぎて寝落ちしちゃって、巻き戻すのを忘れたんだ。頼むよ、兄ちゃん。",
    "pt": "Ei. O filme era tão bom que adormeci e esqueci-me de o rebobinar. Vá lá, meu.",
    "pt-BR": "E aí. O filme era tão bom que eu apaguei e esqueci de rebobinar. Por favor, mano.",
    "ru": "Йо. Фильм был таким классным, что меня вырубило, и совсем вылетело из головы, что его надо перемотать. Ну пожалуйста, бро.",
    "zh": "哟，这电影太好看了，我看着看着就睡着了，忘了倒带。拜托了，哥们。",
    "zh-Hant": "喲，這電影太好看了，我看著看著就睡著了，忘了倒帶。拜託啦，老兄。",
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_int(data, offset, width=4):
    return struct.unpack_from("<i" if width == 4 else "<q", data, offset)[0]


def write_int(data, offset, expected, replacement, width=4):
    actual = read_int(data, offset, width)
    if actual != expected:
        raise ValueError(
            f"unexpected integer at 0x{offset:X}: {actual}, expected {expected}"
        )
    struct.pack_into("<i" if width == 4 else "<q", data, offset, replacement)


def require_source(path, data):
    expected_size, expected_hash = SOURCE[path]
    actual_hash = sha256(data)
    if len(data) != expected_size or actual_hash != expected_hash:
        raise ValueError(
            f"unexpected source {path}: size={len(data)}, sha256={actual_hash}"
        )


def require_bytes(data, offset, expected, label):
    actual = data[offset:offset + len(expected)]
    if actual != expected:
        raise ValueError(
            f"{label}: unexpected bytes at 0x{offset:X}: {actual.hex(' ')}"
        )


def changed_offsets(before, after):
    if len(before) != len(after):
        raise ValueError("cannot compare changed offsets for different-sized data")
    return {index for index, pair in enumerate(zip(before, after)) if pair[0] != pair[1]}


def write_fstring(text, wide):
    if wide:
        encoded = text.encode("utf-16le") + b"\0\0"
        return struct.pack("<i", -(len(encoded) // 2)) + encoded
    encoded = text.encode("utf-8") + b"\0"
    return struct.pack("<i", len(encoded)) + encoded


def read_fstring(data, offset):
    (length,) = struct.unpack_from("<i", data, offset)
    offset += 4
    if length == 0:
        return "", False, offset
    if length < 0:
        size = -length * 2
        encoded = data[offset:offset + size]
        if len(encoded) != size or encoded[-2:] != b"\0\0":
            raise ValueError("invalid UTF-16 locres string")
        return encoded[:-2].decode("utf-16le"), True, offset + size
    encoded = data[offset:offset + length]
    if not length or len(encoded) != length or encoded[-1:] != b"\0":
        raise ValueError("invalid ANSI locres string")
    return encoded[:-1].decode("utf-8"), False, offset + length


def serialize_locres(resource):
    entries = bytearray()
    entry_count = sum(len(namespace["entries"]) for namespace in resource["namespaces"])
    entries.extend(struct.pack("<II", entry_count, len(resource["namespaces"])))
    for namespace in resource["namespaces"]:
        entries.extend(struct.pack("<I", namespace["hash"]))
        entries.extend(write_fstring(namespace["namespace"], namespace["wide"]))
        entries.extend(struct.pack("<I", len(namespace["entries"])))
        for entry in namespace["entries"]:
            entries.extend(struct.pack("<I", entry["hash"]))
            entries.extend(write_fstring(entry["key"], entry["wide"]))
            entries.extend(struct.pack("<Ii", entry["source_hash"], entry["string_index"]))

    strings = bytearray(struct.pack("<I", len(resource["strings"])))
    for item in resource["strings"]:
        strings.extend(write_fstring(item["text"], item["wide"]))
        strings.extend(struct.pack("<i", item["references"]))
    string_offset = 25 + len(entries)
    return LOCRES_MAGIC + b"\x03" + struct.pack("<q", string_offset) + entries + strings


def parse_locres(data):
    if data[:16] != LOCRES_MAGIC or data[16:17] != b"\x03":
        raise ValueError("unexpected locres format")
    (string_offset,) = struct.unpack_from("<q", data, 17)
    offset = 25
    entry_count, namespace_count = struct.unpack_from("<II", data, offset)
    offset += 8
    namespaces = []
    for _ in range(namespace_count):
        (namespace_hash,) = struct.unpack_from("<I", data, offset)
        offset += 4
        namespace, namespace_wide, offset = read_fstring(data, offset)
        (key_count,) = struct.unpack_from("<I", data, offset)
        offset += 4
        entries = []
        for _ in range(key_count):
            (key_hash,) = struct.unpack_from("<I", data, offset)
            offset += 4
            key, key_wide, offset = read_fstring(data, offset)
            source_hash, string_index = struct.unpack_from("<Ii", data, offset)
            offset += 8
            entries.append({
                "hash": key_hash,
                "key": key,
                "wide": key_wide,
                "source_hash": source_hash,
                "string_index": string_index,
            })
        namespaces.append({
            "hash": namespace_hash,
            "namespace": namespace,
            "wide": namespace_wide,
            "entries": entries,
        })
    if offset != string_offset:
        raise ValueError("locres entry table ended at an unexpected offset")

    offset = string_offset
    (string_count,) = struct.unpack_from("<I", data, offset)
    offset += 4
    strings = []
    for _ in range(string_count):
        text, wide, offset = read_fstring(data, offset)
        (references,) = struct.unpack_from("<i", data, offset)
        offset += 4
        strings.append({"text": text, "wide": wide, "references": references})
    if offset != len(data):
        raise ValueError("locres has trailing bytes")
    if sum(len(namespace["entries"]) for namespace in namespaces) != entry_count:
        raise ValueError("locres entry count mismatch")
    return {"namespaces": namespaces, "strings": strings}


def locres_entries(resource):
    result = {}
    for namespace in resource["namespaces"]:
        for entry in namespace["entries"]:
            index = entry["string_index"]
            if not 0 <= index < len(resource["strings"]):
                raise ValueError("invalid locres string index")
            identity = (namespace["namespace"], entry["key"])
            if identity in result:
                raise ValueError(f"duplicate locres identity: {identity}")
            result[identity] = (
                entry["source_hash"],
                resource["strings"][index]["text"],
            )
    return result


def build_localizations(repak, base_pak):
    if sha256(base_pak.read_bytes()) != LOCALIZATION_BASE_PAK_SHA256:
        raise ValueError("unexpected 18 Genres localization base PAK")
    outputs = {}
    for culture, translations in TRANSLATIONS.items():
        if culture == "en":
            continue
        relative = Path("RetroRewind/Content/Localization/Game") / culture / "Game.locres"
        source = subprocess.run(
            [str(repak), "get", str(base_pak), relative.as_posix()],
            check=True,
            stdout=subprocess.PIPE,
        ).stdout
        resource = parse_locres(source)
        if serialize_locres(resource) != source:
            raise ValueError(f"{culture} localization base did not round-trip")
        before = locres_entries(resource)
        if any(namespace["namespace"] == LOCALIZATION_NAMESPACE for namespace in resource["namespaces"]):
            raise ValueError(f"{culture} already contains the mod localization namespace")
        dialogue_identity = (DIALOGUE_TEXT["namespace"], DIALOGUE_TEXT["key"])
        if dialogue_identity in before:
            raise ValueError(f"{culture} already contains the rewind dialogue translation")

        string_indices = {}
        for index, item in enumerate(resource["strings"]):
            string_indices.setdefault(item["text"], index)
        entries = []
        for index, text in enumerate(LOCALIZED_TEXTS.values()):
            translation = translations[index]
            string_index = string_indices.get(translation)
            if string_index is None:
                string_index = len(resource["strings"])
                resource["strings"].append({
                    "text": translation,
                    "wide": any(ord(character) > 127 for character in translation),
                    "references": 0,
                })
                string_indices[translation] = string_index
            resource["strings"][string_index]["references"] += 1
            entries.append({
                "hash": text["key_hash"],
                "key": text["key"],
                "wide": False,
                "source_hash": text["source_hash"],
                "string_index": string_index,
            })
        resource["namespaces"].append({
            "hash": LOCALIZATION_NAMESPACE_HASH,
            "namespace": LOCALIZATION_NAMESPACE,
            "wide": False,
            "entries": entries,
        })
        dialogue_translation = DIALOGUE_TRANSLATIONS[culture]
        dialogue_string_index = string_indices.get(dialogue_translation)
        if dialogue_string_index is None:
            dialogue_string_index = len(resource["strings"])
            resource["strings"].append({
                "text": dialogue_translation,
                "wide": any(ord(character) > 127 for character in dialogue_translation),
                "references": 0,
            })
            string_indices[dialogue_translation] = dialogue_string_index
        resource["strings"][dialogue_string_index]["references"] += 1
        resource["namespaces"].append({
            "hash": DIALOGUE_TEXT["namespace_hash"],
            "namespace": DIALOGUE_TEXT["namespace"],
            "wide": False,
            "entries": [{
                "hash": DIALOGUE_TEXT["key_hash"],
                "key": DIALOGUE_TEXT["key"],
                "wide": False,
                "source_hash": DIALOGUE_TEXT["source_hash"],
                "string_index": dialogue_string_index,
            }],
        })
        data = serialize_locres(resource)
        parsed = parse_locres(data)
        if serialize_locres(parsed) != data:
            raise ValueError(f"{culture} merged locres did not round-trip")
        after = locres_entries(parsed)
        if len(after) != len(before) + 3:
            raise ValueError(f"{culture} merged locres entry count mismatch")
        for identity, value in before.items():
            if after.get(identity) != value:
                raise ValueError(f"{culture} base localization entry changed: {identity}")
        for index, text in enumerate(LOCALIZED_TEXTS.values()):
            expected = (text["source_hash"], translations[index])
            if after.get((LOCALIZATION_NAMESPACE, text["key"])) != expected:
                raise ValueError(f"{culture} rewind translation mismatch: {text['key']}")
        dialogue_expected = (
            DIALOGUE_TEXT["source_hash"],
            dialogue_translation,
        )
        if after.get(dialogue_identity) != dialogue_expected:
            raise ValueError(f"{culture} rewind dialogue translation mismatch")
        outputs[relative] = data
    return outputs


def bytecode_string(value):
    return b"\x1f" + value.encode("ascii") + b"\0"


def string_table_notset_expression():
    return (
        b"\x29\x04"
        + struct.pack("<i", -52)
        + bytecode_string("/Game/VideoStore/localization/interface/Interface.Interface")
        + bytecode_string("NOTSET")
    )


def localized_text_expression(source, key):
    return (
        b"\x29\x01"
        + bytecode_string(source)
        + bytecode_string(key)
        + bytecode_string(LOCALIZATION_NAMESPACE)
    )


def patch_scanner(source_uasset, source_uexp):
    require_source(SCANNER.with_suffix(".uasset"), source_uasset)
    require_source(SCANNER.with_suffix(".uexp"), source_uexp)
    require_bytes(source_uexp, len(source_uexp) - 4, PACKAGE_TAG, "scanner package tag")

    clone_fee = source_uexp[0x2EA7:0x2EDF]
    clone_add = source_uexp[0x2F4F:0x2FBF]
    if sha256(clone_fee) != "f6b184847ea3c084cb3255ee7da8d3de2fedfe43d8c0aafc19a1126225a10f20":
        raise ValueError("unexpected scanner Fees.Rewind expression")
    if sha256(clone_add) != "49846dd90cacc8b591e0cb576e8ae09fef395f8a6688925224aff13c59af5763":
        raise ValueError("unexpected scanner Add Fees to Membership expression")

    insert = bytearray(clone_fee + clone_add)
    require_bytes(insert, 0x33, bytes.fromhex("1d 00 00 00 00"), "scanner cloned rewind value")
    insert[0x34:0x38] = struct.pack("<i", 1)
    if sha256(insert) != "545e0856a34c5042251173e6583eefdea78829a83d99b859c24912b9bb072181":
        raise ValueError("unexpected scanner insert")

    require_bytes(
        source_uexp,
        0x2C8E,
        bytes.fromhex(
            "19 01 01 00 00 00 67 00 00 00 00 00 00 00 01 00 "
            "00 00 0f 00 00 00 00 00 00 00 00 00 00 00 45 7c"
        ),
        "scanner insertion point",
    )
    patched_uexp = bytearray(source_uexp)
    for offset, old, new in (
        (0x2621, 2116, 2224),
        (0x2625, 2996, 3164),
        (0x262A, 2113, 2221),
        (0x2A1C, 1471, 1579),
        (0x2A9E, 1770, 1878),
        (0x2C79, 1327, 1435),
        (0x2E22, 1750, 1858),
        (0x3001, 2049, 2157),
    ):
        write_int(patched_uexp, offset, old, new)
    patched_uexp = bytes(patched_uexp[:0x2C8E] + insert + patched_uexp[0x2C8E:])

    patched_uasset = bytearray(source_uasset)
    write_int(patched_uasset, 0x00E4, 36346, 36514, width=8)
    write_int(patched_uasset, 0x438D, 4131, 4299, width=8)
    following_exports = (
        (0x43F5, 32150), (0x4455, 32246), (0x44B5, 32490),
        (0x4515, 34826), (0x4575, 34967), (0x45D5, 36081),
        (0x4635, 36137), (0x4695, 36198), (0x46F5, 36212),
        (0x4755, 36226), (0x47B5, 36288), (0x4815, 36332),
    )
    for offset, old in following_exports:
        write_int(patched_uasset, offset, old, old + len(insert), width=8)
    patched_uasset = bytes(patched_uasset)

    if len(patched_uasset) != 19373 or len(patched_uexp) != 17145:
        raise ValueError("scanner patch produced unexpected package sizes")
    if sha256(patched_uasset) != SCANNER_OUTPUT["uasset"]:
        raise ValueError("scanner UASSET output hash mismatch")
    if sha256(patched_uexp) != SCANNER_OUTPUT["uexp"]:
        raise ValueError("scanner UEXP output hash mismatch")
    if patched_uexp[-4:] != PACKAGE_TAG:
        raise ValueError("scanner patch did not preserve package tag")
    if patched_uexp[:0x21C6] != source_uexp[:0x21C6]:
        raise ValueError("scanner patch changed an earlier export")
    if patched_uexp[0x3291:] != source_uexp[0x31E9:]:
        raise ValueError("scanner patch changed a later export")

    approved_uasset = set()
    for offset in (0x00E4, 0x438D, *(item[0] for item in following_exports)):
        approved_uasset.update(range(offset, offset + 8))
    if not changed_offsets(source_uasset, patched_uasset).issubset(approved_uasset):
        raise ValueError("scanner patch changed unapproved UASSET bytes")
    return patched_uasset, patched_uexp


def patch_checkout(source_uasset, source_uexp):
    require_source(CHECKOUT.with_suffix(".uasset"), source_uasset)
    require_source(CHECKOUT.with_suffix(".uexp"), source_uexp)
    source_text = string_table_notset_expression()
    if len(source_text) != 75 or source_uexp.count(source_text) != 2:
        raise ValueError("unexpected rewind placeholder text expressions")
    for label, text in LOCALIZED_TEXTS.items():
        require_bytes(source_uexp, text["offset"], source_text, f"rewind {label} placeholder")
    require_bytes(source_uexp, 0x168C, bytes.fromhex("37 00 00 00 00 00 00 f0 3f"), "rewind display price")
    patched = bytearray(source_uexp)
    approved = set()
    relocations = [
        (0x09D4, 2768, 2760),
        (0x0D8C, 2765, 2757),
        (0x10CC, 1477, 1473),
        (0x1472, 2163, 2155),
        (0x1743, 2612, 2604),
        (0x1CAE, 2617, 2609),
    ]
    relocations.extend(
        (0x10E3 + index * 0x17, 1348 + index * 15, 1344 + index * 15)
        for index in range(9)
    )
    relocations.extend(
        (0x1489 + index * 0x17, 2034 + index * 15, 2026 + index * 15)
        for index in range(9)
    )
    relocations.extend(
        (0x175A + index * 0x17, 2483 + index * 15, 2475 + index * 15)
        for index in range(9)
    )
    if len(relocations) != 33:
        raise ValueError("unexpected checkout logical relocation count")
    for offset, old, new in relocations:
        approved.update(range(offset, offset + 4))
        write_int(patched, offset, old, new)
    for text in LOCALIZED_TEXTS.values():
        replacement = localized_text_expression(text["source"], text["key"])
        if len(replacement) != len(source_text):
            raise ValueError("localized rewind text changed bytecode expression size")
        offset = text["offset"]
        approved.update(range(offset, offset + len(replacement)))
        patched[offset:offset + len(replacement)] = replacement
    approved.update(range(0x168D, 0x1695))
    patched[0x168D:0x1695] = struct.pack("<d", 2.0)
    patched = bytes(patched)
    if len(patched) != len(source_uexp):
        raise ValueError("checkout UI patch changed UEXP size")
    if read_int(patched, 0x09D4) != 2760 or read_int(patched, 0x09D8) != 3872:
        raise ValueError("checkout logical or serialized script size mismatch")
    if not changed_offsets(source_uexp, patched).issubset(approved):
        raise ValueError("checkout UI patch changed unexpected bytes")
    if sha256(patched) != CHECKOUT_OUTPUT_UEXP:
        raise ValueError("checkout UI output hash mismatch")
    return source_uasset, patched


def verify_fee_task_source(source_uasset, source_uexp):
    if len(source_uasset) != 34995 or sha256(source_uasset) != FEE_TASK_STRUCTURAL["uasset"]:
        raise ValueError("unexpected structurally patched fee task UASSET")
    if len(source_uexp) != 79560 or sha256(source_uexp) != FEE_TASK_STRUCTURAL["uexp"]:
        raise ValueError("unexpected structurally patched fee task UEXP")
    for offset, expected, fee_error in ANSWER_SITES:
        require_bytes(source_uexp, offset - 1, b"\x1e", f"answer fee type {fee_error} opcode")
        require_bytes(source_uexp, offset, expected, f"answer fee type {fee_error}")
    for fee_type, sites in CHARGE_SITES.items():
        for offset, expected, employee in sites:
            require_bytes(source_uexp, offset - 1, b"\x1e", f"{fee_type}/{employee} opcode")
            require_bytes(source_uexp, offset, expected, f"{fee_type}/{employee}")


def patch_fee_task(source_uasset, source_uexp, variant):
    verify_fee_task_source(source_uasset, source_uexp)
    if variant not in FEE_TASK_OUTPUT:
        raise ValueError(f"unknown fee task variant: {variant}")

    patched = bytearray(source_uexp)
    approved = set()
    changes = []

    answer_targets = ANSWER_SITES if variant == "employee-fee-policy" else (
        next(site for site in ANSWER_SITES if site[2] == 2),
    )
    charge_types = ("damage", "late", "rewind") if variant == "employee-fee-policy" else ("rewind",)
    for offset, original, fee_error in answer_targets:
        approved.update(range(offset, offset + 4))
        patched[offset:offset + 4] = ALWAYS
        if original != ALWAYS:
            changes.append({"decision": "answer", "fee_error": fee_error, "offset": offset})
    for fee_type in charge_types:
        for offset, original, employee in CHARGE_SITES[fee_type]:
            approved.update(range(offset, offset + 4))
            patched[offset:offset + 4] = ALWAYS
            if original != ALWAYS:
                changes.append({
                    "decision": "charge",
                    "fee_type": fee_type,
                    "employee": employee,
                    "offset": offset,
                })
    patched = bytes(patched)

    if len(patched) != len(source_uexp):
        raise ValueError("fee task patch changed UEXP size")
    if not changed_offsets(source_uexp, patched).issubset(approved):
        raise ValueError("fee task patch changed unapproved bytes")
    if sha256(patched) != FEE_TASK_OUTPUT[variant]:
        raise ValueError(f"{variant} fee task output hash mismatch")
    return source_uasset, patched, changes


def extract_sources(repak, game_pak):
    sources = {}
    for path in SOURCE:
        result = subprocess.run(
            [str(repak), "get", str(game_pak), path.as_posix()],
            check=True,
            stdout=subprocess.PIPE,
        )
        require_source(path, result.stdout)
        sources[path] = result.stdout
    return sources


def build_fee_task_structure(dotnet, patcher, usmap, source_uasset, source_uexp):
    with tempfile.TemporaryDirectory(prefix="unrewound-fee-task-structure-") as directory:
        root = Path(directory)
        source = root / "source/BTTask_Checkout-Fees.uasset"
        output = root / "output/BTTask_Checkout-Fees.uasset"
        source.parent.mkdir(parents=True)
        source.write_bytes(source_uasset)
        source.with_suffix(".uexp").write_bytes(source_uexp)
        subprocess.run(
            [
                str(dotnet),
                "run",
                "--project",
                str(patcher),
                "--",
                str(source),
                str(usmap),
                str(output),
            ],
            check=True,
        )
        patched_uasset = output.read_bytes()
        patched_uexp = output.with_suffix(".uexp").read_bytes()
    verify_fee_task_source(patched_uasset, patched_uexp)
    return patched_uasset, patched_uexp


def write_pair(root, relative, uasset, uexp):
    output = root / relative
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix(".uasset").write_bytes(uasset)
    output.with_suffix(".uexp").write_bytes(uexp)


def build_variant(repak, dist, fee_task, common, localizations, variant, filename):
    fee_uasset, fee_uexp, changes = patch_fee_task(
        fee_task[0],
        fee_task[1],
        variant,
    )
    with tempfile.TemporaryDirectory(prefix=f"unrewound-tape-fee-{variant}-") as directory:
        staging = Path(directory)
        write_pair(staging, SCANNER, *common[SCANNER])
        write_pair(staging, CHECKOUT, *common[CHECKOUT])
        write_pair(staging, FEE_TASK, fee_uasset, fee_uexp)
        for relative, data in localizations.items():
            output = staging / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(data)
        pak = dist / filename
        subprocess.run(
            [str(repak), "pack", "--version", "V11", "-q", str(staging), str(pak)],
            check=True,
        )

    expected_members = {
        path.with_suffix(suffix).as_posix()
        for path in (SCANNER, CHECKOUT, FEE_TASK)
        for suffix in (".uasset", ".uexp")
    }
    expected_members.update(path.as_posix() for path in localizations)
    listed = subprocess.run(
        [str(repak), "list", str(pak)],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.splitlines()
    if set(listed) != expected_members or len(listed) != len(expected_members):
        raise ValueError(f"unexpected PAK membership for {filename}: {listed}")

    return {
        "variant": variant,
        "pak": filename,
        "pak_sha256": sha256(pak.read_bytes()),
        "members": sorted(expected_members),
        "fee_task_changes": changes,
        "output_hashes": {
            SCANNER.with_suffix(".uasset").as_posix(): sha256(common[SCANNER][0]),
            SCANNER.with_suffix(".uexp").as_posix(): sha256(common[SCANNER][1]),
            CHECKOUT.with_suffix(".uasset").as_posix(): sha256(common[CHECKOUT][0]),
            CHECKOUT.with_suffix(".uexp").as_posix(): sha256(common[CHECKOUT][1]),
            FEE_TASK.with_suffix(".uasset").as_posix(): sha256(fee_uasset),
            FEE_TASK.with_suffix(".uexp").as_posix(): sha256(fee_uexp),
            **{path.as_posix(): sha256(data) for path, data in localizations.items()},
        },
    }


def main():
    project_root = Path(__file__).resolve().parents[1]
    workspace_root = project_root.parent
    default_game = Path.home() / ".local/share/Steam/steamapps/common/RetroRewind"
    parser = argparse.ArgumentParser(description="Build deterministic Unrewound Tape Fee PAK variants")
    parser.add_argument(
        "--game-pak",
        type=Path,
        default=Path(os.environ.get(
            "RETRO_REWIND_PAK",
            default_game / "RetroRewind/Content/Paks/RetroRewind-Windows.pak",
        )),
    )
    parser.add_argument(
        "--repak",
        type=Path,
        default=workspace_root / "fast-customer-turns/tools/repak/repak_cli-x86_64-unknown-linux-gnu/repak",
    )
    parser.add_argument(
        "--dotnet",
        type=Path,
        default=workspace_root / "fast-customer-turns/tools/dotnet/dotnet",
    )
    parser.add_argument(
        "--usmap",
        type=Path,
        default=(
            default_game
            / "RetroRewind/Binaries/Win64/ue4ss"
            / "RetroRewind-5.4.4-35576357+++UE5+Release-5.4-0196ef29.usmap"
        ),
    )
    parser.add_argument(
        "--localization-base-pak",
        type=Path,
        default=(
            workspace_root
            / "18-genres-localization-fix/dist/zzzzzzzz_18Genres_L10N_Fix_P.pak"
        ),
    )
    parser.add_argument("--dist", type=Path, default=project_root / "dist")
    args = parser.parse_args()

    if not args.game_pak.is_file():
        raise FileNotFoundError(f"game PAK not found: {args.game_pak}")
    if not args.repak.is_file():
        raise FileNotFoundError(f"repak not found: {args.repak}")
    if not args.dotnet.is_file():
        raise FileNotFoundError(f"dotnet not found: {args.dotnet}")
    if not args.usmap.is_file():
        raise FileNotFoundError(f"mappings not found: {args.usmap}")
    if not args.localization_base_pak.is_file():
        raise FileNotFoundError(
            f"localization base PAK not found: {args.localization_base_pak}"
        )

    sources = extract_sources(args.repak, args.game_pak)
    fee_task = build_fee_task_structure(
        args.dotnet,
        project_root / "tools/FeeTaskPatcher/FeeTaskPatcher.csproj",
        args.usmap,
        sources[FEE_TASK.with_suffix(".uasset")],
        sources[FEE_TASK.with_suffix(".uexp")],
    )
    common = {
        SCANNER: patch_scanner(
            sources[SCANNER.with_suffix(".uasset")],
            sources[SCANNER.with_suffix(".uexp")],
        ),
        CHECKOUT: patch_checkout(
            sources[CHECKOUT.with_suffix(".uasset")],
            sources[CHECKOUT.with_suffix(".uexp")],
        ),
    }
    localizations = build_localizations(args.repak, args.localization_base_pak)
    args.dist.mkdir(parents=True, exist_ok=True)
    variants = (
        ("standalone", "zzzzzzzz_UnrewoundTapeFee_P.pak"),
        ("employee-fee-policy", "zzzzzzzz_UnrewoundTapeFee_EmployeeFeePolicy_P.pak"),
    )
    manifest = {
        "game_build": GAME_BUILD,
        "engine": ENGINE_VERSION,
        "source_pak": args.game_pak.name,
        "source_hashes": {path.as_posix(): expected[1] for path, expected in SOURCE.items()},
        "variants": [
            build_variant(
                args.repak,
                args.dist,
                fee_task,
                common,
                localizations,
                variant,
                filename,
            )
            for variant, filename in variants
        ],
    }
    manifest_path = args.dist / "UnrewoundTapeFee.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="ascii")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
