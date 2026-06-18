#!/usr/bin/env python3
"""Generate a FlexNoC Req-network flit monitor package from RTL and Req.md.

The script is intentionally conservative.  It supports the FlexNoC generated RTL
style used by the current projects and stops when it cannot derive the required
header packing or topology facts from source artifacts.
"""

from __future__ import annotations

import argparse
import dataclasses
import re
import shutil
import sys
import tarfile
from collections import defaultdict, OrderedDict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


class Fatal(RuntimeError):
    pass


@dataclasses.dataclass(frozen=True)
class Endpoint:
    inst: str
    port: str

    @classmethod
    def parse(cls, text: str) -> "Endpoint":
        text = text.strip()
        if "." not in text:
            raise Fatal(f"Record endpoint is not instance.port: {text}")
        inst, port = text.rsplit(".", 1)
        if not inst or not port:
            raise Fatal(f"Record endpoint is not instance.port: {text}")
        return cls(inst, port)

    @property
    def path(self) -> str:
        return f"{self.inst}.{self.port}"


@dataclasses.dataclass
class ReqNetwork:
    masters: List[Endpoint]
    slaves: List[Endpoint]
    slave_links: Dict[Tuple[str, str], Endpoint]
    switch_inputs: Dict[str, List[str]]
    switch_outputs: Dict[str, List[str]]
    switch_targets: Dict[Tuple[str, str], List[str]]


@dataclasses.dataclass
class HeaderLayout:
    data_width: int
    routeid_msb: int
    routeid_lsb: int
    opc_msb: int
    opc_lsb: int
    user_msb: int
    user_lsb: int
    routeid_width: int
    pathid_hi: int
    pathid_lo: int
    seqid_hi: int
    seqid_lo: int
    user_width: int
    gen_user_payload_lsb: int


@dataclasses.dataclass(frozen=True)
class Terminal:
    name: str
    index: int
    col: int
    row: int


@dataclasses.dataclass
class Topology:
    terminals: Dict[int, Terminal]
    direct_outputs: Dict[str, Dict[int, str]]
    switch_coords: Dict[str, Tuple[int, int]]
    inter_outputs: Dict[str, Dict[str, Tuple[int, int, int, int]]]
    pathid_ranges: List[Tuple[int, int]]
    target_maps: Dict[str, Dict[int, str]]
    target_literals: Dict[Tuple[str, str], str]
    target_suffixes: Dict[str, str]
    target_idx_width: int
    warnings: List[str]


def sanitize_ident(text: str) -> str:
    out = re.sub(r"[^A-Za-z0-9_]", "_", text)
    if not out:
        raise Fatal("empty identifier after sanitizing")
    if out[0].isdigit():
        out = "_" + out
    return out


def uniq_keep_order(items: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def strip_main(inst: str) -> str:
    return inst[:-5] if inst.endswith("_main") else inst


def endpoint_port_name(ep: Endpoint, switch: bool = False) -> str:
    base = ep.inst if switch else strip_main(ep.inst)
    return sanitize_ident(f"{base}_{ep.port}")


def switch_suffix(switch: str) -> str:
    nums = re.findall(r"\d+", switch)
    return nums[-1] if nums else sanitize_ident(switch)


def build_switch_suffixes(switches: Iterable[str]) -> Dict[str, str]:
    switch_list = list(switches)
    nums_by_switch = {sw: re.findall(r"\d+", sw) for sw in switch_list}
    max_depth = max((len(nums) for nums in nums_by_switch.values()), default=0)
    for depth in range(1, max_depth + 1):
        suffixes: Dict[str, str] = {}
        used: Set[str] = set()
        ok = True
        for sw, nums in nums_by_switch.items():
            suffix = "_".join(nums[-depth:]) if len(nums) >= depth else sanitize_ident(sw)
            if suffix in used:
                ok = False
                break
            used.add(suffix)
            suffixes[sw] = suffix
        if ok:
            return suffixes
    return {sw: sanitize_ident(sw) for sw in switch_list}


def parse_req_md(path: Path) -> ReqNetwork:
    section: Optional[str] = None
    masters: List[Endpoint] = []
    slaves: List[Endpoint] = []
    slave_links: Dict[Tuple[str, str], Endpoint] = OrderedDict()
    switch_inputs: Dict[str, List[str]] = OrderedDict()
    switch_outputs: Dict[str, List[str]] = OrderedDict()
    switch_targets: Dict[Tuple[str, str], List[str]] = OrderedDict()

    record_re = re.compile(r"`([^`]+?)\s*->\s*([^`]+?)`")
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m_sec = re.match(r"\s*##\s*\(([a-z])\)", line)
        if m_sec:
            section = m_sec.group(1)
            continue
        m = record_re.search(line)
        if not m:
            continue
        lhs = Endpoint.parse(m.group(1))
        rhs = Endpoint.parse(m.group(2))
        if section == "a":
            masters.append(lhs)
        elif section == "b":
            slaves.append(rhs)
            slave_links[(lhs.inst, lhs.port)] = rhs
        elif section == "d":
            switch_inputs.setdefault(lhs.inst, [])
            switch_outputs.setdefault(lhs.inst, [])
            if lhs.port not in switch_inputs[lhs.inst]:
                switch_inputs[lhs.inst].append(lhs.port)
            if rhs.port not in switch_outputs[lhs.inst]:
                switch_outputs[lhs.inst].append(rhs.port)
            key = (lhs.inst, lhs.port)
            switch_targets.setdefault(key, [])
            if rhs.port not in switch_targets[key]:
                switch_targets[key].append(rhs.port)

    if not masters:
        raise Fatal("Req.md section (a) has no Record entries for master NIU flit ports")
    if not slaves:
        raise Fatal("Req.md section (b) has no Record entries for slave NIU flit ports")
    if not switch_inputs:
        raise Fatal("Req.md section (d) has no switch reachability Record entries")

    return ReqNetwork(
        masters=dedup_endpoints(masters),
        slaves=dedup_endpoints(slaves),
        slave_links=slave_links,
        switch_inputs=switch_inputs,
        switch_outputs=switch_outputs,
        switch_targets=switch_targets,
    )


def dedup_endpoints(items: List[Endpoint]) -> List[Endpoint]:
    seen: Set[Endpoint] = set()
    out: List[Endpoint] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def read_rtl_text(rtl_root: Path, top_file: Path) -> Tuple[str, List[Path]]:
    files: List[Path] = []
    if rtl_root.is_file():
        files.append(rtl_root)
    else:
        for ext in ("*.v", "*.sv", "*.vh"):
            files.extend(sorted(rtl_root.rglob(ext)))
    if top_file not in files and top_file.exists():
        files.insert(0, top_file)
    if not files:
        raise Fatal(f"no RTL files found under {rtl_root}")
    chunks = []
    for f in files:
        try:
            chunks.append(f.read_text(encoding="utf-8", errors="replace"))
        except OSError as exc:
            raise Fatal(f"failed to read RTL file {f}: {exc}") from exc
    return "\n".join(chunks), files


def parse_width(width_text: Optional[str]) -> int:
    if not width_text:
        return 1
    m = re.search(r"\[\s*(\d+)\s*:\s*(\d+)\s*\]", width_text)
    if not m:
        return 1
    a, b = int(m.group(1)), int(m.group(2))
    return abs(a - b) + 1


def parse_range(width_text: Optional[str]) -> Tuple[int, int]:
    if not width_text:
        return (0, 0)
    m = re.search(r"\[\s*(\d+)\s*:\s*(\d+)\s*\]", width_text)
    if not m:
        return (0, 0)
    return int(m.group(1)), int(m.group(2))


def split_concat(expr: str) -> List[str]:
    parts: List[str] = []
    cur: List[str] = []
    depth = 0
    for ch in expr:
        if ch == "{":
            depth += 1
            cur.append(ch)
        elif ch == "}":
            depth -= 1
            cur.append(ch)
        elif ch == "," and depth == 0:
            part = "".join(cur).strip()
            if part:
                parts.append(part)
            cur = []
        else:
            cur.append(ch)
    part = "".join(cur).strip()
    if part:
        parts.append(part)
    return parts


def const_width(expr: str) -> Optional[int]:
    m = re.fullmatch(r"\s*(\d+)\s*'[sS]?[bBdDhHoO][0-9a-fA-F_xXzZ]+\s*", expr)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"\s*(\d+)\s*'?\s*[dD]?\s*", expr)
    if m:
        return None
    return None


def build_decl_widths(module_text: str) -> Dict[str, int]:
    widths: Dict[str, int] = {}
    decl_re = re.compile(
        r"\b(?:input|output|wire|reg)\s+(?:signed\s+)?(\[[^\]]+\])?\s*([^;]+);",
        re.S,
    )
    for m in decl_re.finditer(module_text):
        width = parse_width(m.group(1))
        names_blob = m.group(2)
        for raw in names_blob.split(","):
            name = raw.strip()
            name = re.sub(r"=.*", "", name).strip()
            name = re.sub(r"\[[^\]]+\]", "", name).strip()
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", name):
                widths[name] = width
    return widths


def expr_width(expr: str, widths: Dict[str, int]) -> int:
    expr = expr.strip()
    cwidth = const_width(expr)
    if cwidth is not None:
        return cwidth
    m = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_$]*)(?:\s*\[\s*(\d+)\s*:\s*(\d+)\s*\])?", expr)
    if m:
        if m.group(2) is not None:
            return abs(int(m.group(2)) - int(m.group(3))) + 1
        name = m.group(1)
        if name in widths:
            return widths[name]
    raise Fatal(f"cannot derive expression width for: {expr}")


def iter_modules(text: str) -> Iterable[Tuple[str, str]]:
    mod_re = re.compile(r"\bmodule\s+([A-Za-z_][A-Za-z0-9_$]*)\b(.*?)\bendmodule\b", re.S)
    for m in mod_re.finditer(text):
        yield m.group(1), m.group(0)


def find_assign(module_text: str, lhs: str) -> Optional[str]:
    m = re.search(rf"\bassign\s+{re.escape(lhs)}\s*=\s*(.*?);", module_text, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else None


def concat_field_ranges(parts: List[str], widths: Dict[str, int]) -> Dict[str, Tuple[int, int]]:
    total = sum(expr_width(part, widths) for part in parts)
    cursor = total - 1
    ranges: Dict[str, Tuple[int, int]] = {}
    for part in parts:
        width = expr_width(part, widths)
        name = part.strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", name):
            ranges[name] = (cursor, cursor - width + 1)
        cursor -= width
    return ranges


def extract_header_layout(text: str, axuser_bits: Tuple[int, int]) -> HeaderLayout:
    candidates: List[Tuple[str, str]] = []
    for name, body in iter_modules(text):
        route_expr = find_assign(body, "RouteId")
        txhdr_expr = find_assign(body, "TxHdr")
        txdata_expr = find_assign(body, "Tx_Data")
        if not route_expr or not txhdr_expr or not txdata_expr:
            continue
        if "GenRx_Req_SeqId" not in route_expr:
            continue
        if "Hdr_RouteId" not in txhdr_expr or "Hdr_User" not in txhdr_expr or "Hdr_Opc" not in txhdr_expr:
            continue
        if "TxHdr" not in txdata_expr:
            continue
        candidates.append((name, body))

    if not candidates:
        raise Fatal("cannot find Req serializer module with RouteId/TxHdr/Tx_Data packing")
    name, body = candidates[0]
    widths = build_decl_widths(body)

    txhdr_parts = split_concat(find_assign(body, "TxHdr").strip("{} "))
    hdr_ranges = concat_field_ranges(txhdr_parts, widths)
    txdata_expr = find_assign(body, "Tx_Data")
    txdata_parts = split_concat(txdata_expr.strip("{} "))
    if not txdata_parts or txdata_parts[0].strip() != "TxHdr":
        raise Fatal(f"{name}: unsupported Tx_Data packing; expected TxHdr as MSB field")
    txhdr_low_width = sum(expr_width(part, widths) for part in txdata_parts[1:])

    routeid_msb_h, routeid_lsb_h = hdr_ranges["Hdr_RouteId"]
    opc_msb_h, opc_lsb_h = hdr_ranges["Hdr_Opc"]
    user_msb_h, user_lsb_h = hdr_ranges["Hdr_User"]
    routeid_msb = txhdr_low_width + routeid_msb_h
    routeid_lsb = txhdr_low_width + routeid_lsb_h
    opc_msb = txhdr_low_width + opc_msb_h
    opc_lsb = txhdr_low_width + opc_lsb_h
    user_msb = txhdr_low_width + user_msb_h
    user_lsb = txhdr_low_width + user_lsb_h

    route_parts = split_concat(find_assign(body, "RouteId").strip("{} "))
    route_ranges = concat_field_ranges(route_parts, widths)
    if "GenRx_Req_SeqId" not in route_ranges:
        raise Fatal(f"{name}: RouteId does not contain GenRx_Req_SeqId")
    seq_hi, seq_lo = route_ranges["GenRx_Req_SeqId"]
    if "CmdRx_ApertureId" not in route_ranges:
        raise Fatal(f"{name}: RouteId does not contain CmdRx_ApertureId")
    aperture_hi, aperture_lo = route_ranges["CmdRx_ApertureId"]

    aperture_width = aperture_hi - aperture_lo + 1
    # FlexNoC Req aperture usually packs {Aper_PathId, Aper_SubMappingId}.
    # Derive path by excluding the 2-bit submapping tail after verifying width.
    if aperture_width < 3:
        raise Fatal(f"{name}: CmdRx_ApertureId width {aperture_width} is too small")
    submapping_width = 2
    path_lo = aperture_lo + submapping_width
    path_hi = aperture_hi

    user_width = widths.get("Hdr_User", user_msb - user_lsb + 1)
    ax_hi, ax_lo = max(axuser_bits), min(axuser_bits)
    # In the observed FlexNoC generated generic request, the original AXI USER
    # payload is packed into the high 16 bits of the 25-bit Gen_Req_User.
    gen_payload_lsb = user_width - 16
    if gen_payload_lsb < 0:
        raise Fatal(f"{name}: Hdr_User width {user_width} cannot contain AXI USER[15:0]")
    if gen_payload_lsb + ax_hi >= user_width:
        raise Fatal(
            f"{name}: AxUser[{ax_hi}:{ax_lo}] cannot be mapped into Hdr_User[{user_width-1}:0]"
        )

    data_width = widths.get("Tx_Data")
    if not data_width:
        m_data = re.search(r"\boutput\s+(\[[^\]]+\])\s+Tx_Data\b", body)
        data_width = parse_width(m_data.group(1) if m_data else None)

    return HeaderLayout(
        data_width=data_width,
        routeid_msb=routeid_msb,
        routeid_lsb=routeid_lsb,
        opc_msb=opc_msb,
        opc_lsb=opc_lsb,
        user_msb=user_msb,
        user_lsb=user_lsb,
        routeid_width=routeid_msb_h - routeid_lsb_h + 1,
        pathid_hi=path_hi,
        pathid_lo=path_lo,
        seqid_hi=seq_hi,
        seqid_lo=seq_lo,
        user_width=user_width,
        gen_user_payload_lsb=gen_payload_lsb,
    )


def parse_sv_const(expr: str) -> Optional[int]:
    m = re.search(r"(\d+)\s*'[sS]?([bBdDhHoO])([0-9a-fA-F_xXzZ]+)", expr)
    if not m:
        return None
    base_ch = m.group(2).lower()
    digits = m.group(3).replace("_", "")
    if any(ch in digits.lower() for ch in "xz"):
        return None
    base = {"b": 2, "d": 10, "h": 16, "o": 8}[base_ch]
    return int(digits, base)


def extract_pathid_ranges(text: str) -> List[Tuple[int, int]]:
    values: Set[int] = set()
    for m in re.finditer(r"Aper_PathId\s*=\s*([^;]+);", text):
        val = parse_sv_const(m.group(1))
        if val is not None:
            values.add(val)
    if not values:
        raise Fatal("cannot find Aper_PathId constants in RTL")

    ranges: List[Tuple[int, int]] = []
    sorted_values = sorted(values)
    value_set = set(sorted_values)
    for start in sorted_values:
        if start & 0xF != 0x5:
            continue
        if start - 1 in value_set:
            continue
        end = start
        while end + 1 in value_set:
            end += 1
        if end > start:
            ranges.append((start, end))
    if not ranges:
        raise Fatal("cannot infer contiguous MEM target PathId ranges from RTL")
    return ranges


def parse_terminal(ep: Endpoint) -> Optional[Terminal]:
    base = strip_main(ep.inst)
    m = re.match(r"([A-Za-z]+)(\d+)_([0-9]+)_([0-9]+)_", base)
    if not m:
        return None
    return Terminal(
        name=f"{m.group(1)}{m.group(2)}",
        index=int(m.group(2)),
        col=int(m.group(3)),
        row=int(m.group(4)),
    )


def parse_switch_coord(switch: str) -> Optional[Tuple[int, int]]:
    m = re.match(r"switch_([0-9]+)_([0-9]+)_req_main$", switch)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def parse_inter_output(port: str) -> Optional[Tuple[int, int, int, int]]:
    m = re.match(r"to_link_([0-9]+)_([0-9]+)_to_([0-9]+)_([0-9]+)_.*_req$", port)
    if not m:
        return None
    return tuple(int(x) for x in m.groups())  # type: ignore[return-value]


def build_topology(req: ReqNetwork, rtl_text: str) -> Topology:
    warnings: List[str] = []
    terminals_by_idx: Dict[int, Terminal] = {}
    for ep in req.slaves:
        term = parse_terminal(ep)
        if term is not None:
            terminals_by_idx[term.index] = term
    if not terminals_by_idx:
        warnings.append("cannot infer target terminal indices from slave NIU instance names; switch targets may decode to UNKNOWN")

    try:
        pathid_ranges = extract_pathid_ranges(rtl_text)
    except Fatal as exc:
        warnings.append(f"{exc}; switch targets may decode to UNKNOWN")
        pathid_ranges = []

    switch_coords: Dict[str, Tuple[int, int]] = {}
    for sw in req.switch_inputs:
        coord = parse_switch_coord(sw)
        if coord is None:
            raise Fatal(f"cannot infer switch coordinate from instance name: {sw}")
        switch_coords[sw] = coord

    # Use section (b) only as optional path evidence for local switch outputs.
    # It never adds target enum values; enums remain strictly from section (d).
    direct_outputs: Dict[str, Dict[int, str]] = defaultdict(dict)
    for sw, outputs in req.switch_outputs.items():
        for out in outputs:
            slave_ep = req.slave_links.get((sw, out))
            if slave_ep is None:
                continue
            term = parse_terminal(slave_ep)
            if term is not None:
                direct_outputs[sw][term.index] = out

    inter_outputs: Dict[str, Dict[str, Tuple[int, int, int, int]]] = defaultdict(dict)
    for sw, outputs in req.switch_outputs.items():
        for out in outputs:
            parsed = parse_inter_output(out)
            if parsed is not None:
                inter_outputs[sw][out] = parsed

    target_maps: Dict[str, Dict[int, str]] = {}
    for sw, coord in switch_coords.items():
        target_maps[sw] = {}
        sw_col, sw_row = coord
        for idx, term in terminals_by_idx.items():
            if idx in direct_outputs.get(sw, {}):
                target_maps[sw][idx] = direct_outputs[sw][idx]
                continue
            best: Optional[Tuple[int, str]] = None
            for out, (src_col, src_row, dst_col, dst_row) in inter_outputs.get(sw, {}).items():
                # Prefer the virtual column that matches the target side and a
                # one-hop row move toward the target.
                row_moves_toward = (term.row > sw_row and dst_row > src_row) or (
                    term.row < sw_row and dst_row < src_row
                )
                if not row_moves_toward:
                    continue
                score = 0
                if src_col == term.col:
                    score += 4
                if dst_col == term.col:
                    score += 2
                if abs(dst_row - term.row) < abs(sw_row - term.row):
                    score += 1
                if best is None or score > best[0]:
                    best = (score, out)
            if best is not None:
                target_maps[sw][idx] = best[1]

    target_suffixes = build_switch_suffixes(req.switch_outputs.keys())
    target_literals: Dict[Tuple[str, str], str] = {}
    global_counts: Dict[str, int] = defaultdict(int)
    for sw, outs in req.switch_outputs.items():
        for out in outs:
            global_counts[sanitize_ident(out)] += 1
    for sw, outs in req.switch_outputs.items():
        for out in outs:
            lit = sanitize_ident(out)
            if global_counts[lit] > 1:
                lit = f"{lit}_{switch_suffix(sw)}"
            target_literals[(sw, out)] = lit

    max_index = 0
    if terminals_by_idx:
        max_index = max(max_index, max(terminals_by_idx))
    for start, end in pathid_ranges:
        max_index = max(max_index, end - start)
    target_idx_width = max(5, (max_index + 1).bit_length() + 1)

    return Topology(
        terminals=terminals_by_idx,
        direct_outputs=dict(direct_outputs),
        switch_coords=switch_coords,
        inter_outputs=dict(inter_outputs),
        pathid_ranges=pathid_ranges,
        target_maps=target_maps,
        target_literals=target_literals,
        target_suffixes=target_suffixes,
        target_idx_width=target_idx_width,
        warnings=warnings,
    )


def validate_endpoints(req: ReqNetwork, rtl_text: str) -> None:
    missing: List[str] = []
    endpoints: List[Endpoint] = []
    endpoints.extend(req.masters)
    endpoints.extend(req.slaves)
    for sw, ports in req.switch_inputs.items():
        endpoints.extend(Endpoint(sw, p) for p in ports)
    for sw, ports in req.switch_outputs.items():
        endpoints.extend(Endpoint(sw, p) for p in ports)
    for ep in dedup_endpoints(endpoints):
        if ep.inst not in rtl_text:
            missing.append(f"{ep.inst} (instance)")
            continue
        if f".{ep.port}_Data" not in rtl_text and f".{ep.port}_Vld" not in rtl_text:
            missing.append(f"{ep.path}_Data/_Vld")
    if missing:
        raise Fatal("RTL/Req.md mismatch; missing endpoints:\n  " + "\n  ".join(missing[:50]))


def state_enum(master_names: Sequence[str]) -> str:
    names: List[str] = ["I"]
    for family in ("F", "FH", "FT", "FHT", "S", "SH", "ST", "SHT", "B"):
        for idx, _ in enumerate(master_names):
            names.append(f"{family}{idx}R")
            names.append(f"{family}{idx}W")
    width = max(1, (len(names) - 1).bit_length())
    lines = [f"typedef enum logic [{width - 1}:0] {{"]
    for i, name in enumerate(names):
        comma = "," if i != len(names) - 1 else ""
        lines.append(f"    {name:<7} = {width}'d{i}{comma}")
    lines.append(f"}} __STATE_TYPE__;")
    return "\n".join(lines), width


def emit_flit_if_monitor(top_module: str, layout: HeaderLayout, state_type: str, state_width: int, master_count: int) -> str:
    prefix = f"{top_module}_flit"
    lines: List[str] = []
    lines.append(f"module {top_module}_flit_if_monitor #(")
    lines.append(f"    parameter DATA_WIDTH      = {layout.data_width},")
    lines.append(f"    parameter ROUTEID_MSB     = {layout.routeid_msb},")
    lines.append(f"    parameter ROUTEID_LSB     = {layout.routeid_lsb},")
    lines.append(f"    parameter OPC_MSB         = {layout.opc_msb},")
    lines.append(f"    parameter OPC_LSB         = {layout.opc_lsb},")
    lines.append(f"    parameter USER_MSB        = {layout.user_msb},")
    lines.append(f"    parameter USER_LSB        = {layout.user_lsb},")
    lines.append("    parameter USER_MASTER_MSB = 15,")
    lines.append("    parameter USER_MASTER_LSB = 14")
    lines.append(") (")
    lines.append("    input                   clk,")
    lines.append("    input                   rst_n,")
    lines.append("    input  [DATA_WIDTH-1:0] data,")
    lines.append("    input                   head,")
    lines.append("    input                   tail,")
    lines.append("    input                   vld,")
    lines.append("    input                   rdy,")
    lines.append(f"    output {state_type} state,")
    lines.append("    output [1:0]            master,")
    lines.append(f"    output [{layout.routeid_width - 1}:0] routeid,")
    lines.append(f"    output [{layout.pathid_hi - layout.pathid_lo}:0] pathid,")
    lines.append(f"    output [{layout.seqid_hi - layout.seqid_lo}:0] seqid,")
    lines.append(f"    output [{layout.user_width - 1}:0] user,")
    lines.append("    output                  in_packet")
    lines.append(");")
    lines.append("    reg        in_packet_q;")
    lines.append("    reg [1:0]  saved_master_q;")
    lines.append(f"    reg [{layout.routeid_width - 1}:0] saved_routeid_q;")
    lines.append(f"    reg [{layout.user_width - 1}:0] saved_user_q;")
    lines.append("    reg        saved_is_write_q;")
    lines.append("")
    lines.append(f"    wire [{layout.routeid_width - 1}:0] head_routeid = data[ROUTEID_MSB:ROUTEID_LSB];")
    lines.append("    wire [3:0]  head_opc     = data[OPC_MSB:OPC_LSB];")
    lines.append(f"    wire [{layout.user_width - 1}:0] head_user    = data[USER_MSB:USER_LSB];")
    lines.append("    wire [1:0]  head_master  = head_user[USER_MASTER_MSB:USER_MASTER_LSB];")
    lines.append("    wire        head_is_write = head_opc[2];")
    lines.append("    wire        fire         = vld & rdy;")
    lines.append("")
    lines.append("    wire [1:0] active_master = (vld & head) ? head_master : saved_master_q;")
    lines.append(f"    wire [{layout.routeid_width - 1}:0] active_routeid = (vld & head) ? head_routeid : saved_routeid_q;")
    lines.append(f"    wire [{layout.user_width - 1}:0] active_user = (vld & head) ? head_user : saved_user_q;")
    lines.append("    wire active_is_write = (vld & head) ? head_is_write : saved_is_write_q;")
    lines.append("")

    def func_body(fname: str, family: str) -> List[str]:
        out = [
            f"    function automatic {state_type} {fname};",
            "        input [1:0] m;",
            "        input       is_write;",
            "        begin",
            "            case (m)",
        ]
        for i in range(master_count - 1):
            out.append(f"                2'd{i}: {fname} = is_write ? {family}{i}W : {family}{i}R;")
        out.append(f"                default: {fname} = is_write ? {family}{master_count - 1}W : {family}{master_count - 1}R;")
        out.extend(["            endcase", "        end", "    endfunction", ""])
        return out

    for fname, fam in (
        ("fire_body_state", "F"),
        ("fire_head_state", "FH"),
        ("fire_tail_state", "FT"),
        ("fire_head_tail_state", "FHT"),
        ("stall_body_state", "S"),
        ("stall_head_state", "SH"),
        ("stall_tail_state", "ST"),
        ("stall_head_tail_state", "SHT"),
        ("bubble_state", "B"),
    ):
        lines.extend(func_body(fname, fam))

    lines.append(f"    function automatic {state_type} fire_state;")
    lines.append("        input [1:0] m; input is_write; input h; input t;")
    lines.append("        begin")
    lines.append("            if (h & t) fire_state = fire_head_tail_state(m, is_write);")
    lines.append("            else if (h) fire_state = fire_head_state(m, is_write);")
    lines.append("            else if (t) fire_state = fire_tail_state(m, is_write);")
    lines.append("            else fire_state = fire_body_state(m, is_write);")
    lines.append("        end")
    lines.append("    endfunction")
    lines.append("")
    lines.append(f"    function automatic {state_type} stall_state;")
    lines.append("        input [1:0] m; input is_write; input h; input t;")
    lines.append("        begin")
    lines.append("            if (h & t) stall_state = stall_head_tail_state(m, is_write);")
    lines.append("            else if (h) stall_state = stall_head_state(m, is_write);")
    lines.append("            else if (t) stall_state = stall_tail_state(m, is_write);")
    lines.append("            else stall_state = stall_body_state(m, is_write);")
    lines.append("        end")
    lines.append("    endfunction")
    lines.append("")
    lines.append("    assign in_packet = in_packet_q;")
    lines.append("    assign master    = (vld | in_packet_q) ? active_master : 2'b0;")
    lines.append(f"    assign routeid   = (vld | in_packet_q) ? active_routeid : {layout.routeid_width}'b0;")
    lines.append(f"    assign pathid    = (vld | in_packet_q) ? active_routeid[{layout.pathid_hi}:{layout.pathid_lo}] : {layout.pathid_hi - layout.pathid_lo + 1}'b0;")
    lines.append(f"    assign seqid     = (vld | in_packet_q) ? active_routeid[{layout.seqid_hi}:{layout.seqid_lo}] : {layout.seqid_hi - layout.seqid_lo + 1}'b0;")
    lines.append(f"    assign user      = (vld | in_packet_q) ? active_user : {layout.user_width}'b0;")
    lines.append("")
    lines.append("    assign state =")
    lines.append("        fire        ? fire_state(active_master, active_is_write, head, tail) :")
    lines.append("        vld         ? stall_state(active_master, active_is_write, head, tail) :")
    lines.append("        in_packet_q ? bubble_state(active_master, active_is_write) :")
    lines.append("        I;")
    lines.append("")
    lines.append("    always @(posedge clk or negedge rst_n) begin")
    lines.append("        if (!rst_n) begin")
    lines.append("            in_packet_q <= 1'b0;")
    lines.append("            saved_master_q <= 2'b0;")
    lines.append(f"            saved_routeid_q <= {layout.routeid_width}'b0;")
    lines.append(f"            saved_user_q <= {layout.user_width}'b0;")
    lines.append("            saved_is_write_q <= 1'b0;")
    lines.append("        end else begin")
    lines.append("            if (vld & head) begin")
    lines.append("                saved_master_q <= head_master;")
    lines.append("                saved_routeid_q <= head_routeid;")
    lines.append("                saved_user_q <= head_user;")
    lines.append("                saved_is_write_q <= head_is_write;")
    lines.append("            end")
    lines.append("            if (fire) begin")
    lines.append("                if (head & !tail) begin")
    lines.append("                    in_packet_q <= 1'b1;")
    lines.append("                end else if (tail) begin")
    lines.append("                    in_packet_q <= 1'b0;")
    lines.append("                    saved_master_q <= 2'b0;")
    lines.append(f"                    saved_routeid_q <= {layout.routeid_width}'b0;")
    lines.append(f"                    saved_user_q <= {layout.user_width}'b0;")
    lines.append("                    saved_is_write_q <= 1'b0;")
    lines.append("                end")
    lines.append("            end")
    lines.append("        end")
    lines.append("    end")
    lines.append("endmodule")
    return "\n".join(lines)


def emit_mon_if_instance(top_module: str, name: str, layout: HeaderLayout) -> str:
    return f"""
    {top_module}_flit_if_monitor #(
        .DATA_WIDTH(DATA_WIDTH),
        .ROUTEID_MSB(ROUTEID_MSB),
        .ROUTEID_LSB(ROUTEID_LSB),
        .OPC_MSB(OPC_MSB),
        .OPC_LSB(OPC_LSB),
        .USER_MSB(USER_MSB),
        .USER_LSB(USER_LSB),
        .USER_MASTER_MSB(USER_MASTER_MSB),
        .USER_MASTER_LSB(USER_MASTER_LSB)
    ) u_mon_{name} (
        .clk(clk),
        .rst_n(rst_n),
        .data({name}_data),
        .head({name}_head),
        .tail({name}_tail),
        .vld({name}_vld),
        .rdy({name}_rdy),
        .state(mon_{name}_state),
        .master(mon_{name}_master),
        .routeid(mon_{name}_routeid),
        .pathid(mon_{name}_pathid),
        .seqid(mon_{name}_seqid),
        .user(mon_{name}_user),
        .in_packet(mon_{name}_in_packet)
    );
""".rstrip()


def emit_niu_decl_and_inst(top_module: str, name: str, layout: HeaderLayout, state_type: str) -> str:
    lines = []
    lines.append(f"    {state_type} mon_{name}_state;")
    lines.append(f"    wire [{layout.seqid_hi - layout.seqid_lo}:0] mon_{name}_seqid;")
    lines.append(f"    wire [1:0] mon_{name}_master;")
    lines.append(f"    wire [{layout.routeid_width - 1}:0] mon_{name}_routeid;")
    lines.append(f"    wire [{layout.pathid_hi - layout.pathid_lo}:0] mon_{name}_pathid;")
    lines.append(f"    wire [{layout.user_width - 1}:0] mon_{name}_user;")
    lines.append(f"    wire mon_{name}_in_packet;")
    lines.append(emit_mon_if_instance(top_module, name, layout))
    return "\n".join(lines)


def emit_target_enums(top_module: str, req: ReqNetwork, topo: Topology) -> str:
    chunks: List[str] = []
    for sw, outputs in req.switch_outputs.items():
        if len(outputs) > 14:
            raise Fatal(
                f"{sw} has {len(outputs)} switch outputs in Req.md; "
                "the v1 target enum supports at most 14 real targets plus NONE/UNKNOWN"
            )
        suffix = topo.target_suffixes[sw]
        enum_type = f"{top_module}_{sanitize_ident(sw)}_target_e"
        chunks.append(f"typedef enum logic [3:0] {{")
        chunks.append(f"    NONE_{suffix} = 4'd0,")
        value = 1
        for out in outputs:
            lit = topo.target_literals[(sw, out)]
            chunks.append(f"    {lit:<48} = 4'd{value},")
            value += 1
            if value >= 15:
                break
        chunks.append(f"    UNKNOWN_{suffix} = 4'd15")
        chunks.append(f"}} {enum_type};")
        chunks.append("")
    return "\n".join(chunks).rstrip()


def emit_pathid_decode(top_module: str, layout: HeaderLayout, topo: Topology) -> str:
    idx_width = topo.target_idx_width
    idx_mask = (1 << idx_width) - 1
    lines = []
    lines.append(f"module {top_module}_pathid_decode (")
    lines.append(f"    input  [{layout.pathid_hi - layout.pathid_lo}:0] pathid,")
    lines.append(f"    output [{idx_width - 1}:0] target_idx,")
    lines.append("    output        target_hit")
    lines.append(");")
    lines.append(f"    reg [{idx_width - 1}:0] idx_r;")
    lines.append("    always @* begin")
    lines.append(f"        idx_r = {idx_width}'d{(1 << idx_width) - 1};")
    for start, end in topo.pathid_ranges:
        if end - start + 1 > (1 << idx_width):
            raise Fatal(f"PathId range {start:03x}-{end:03x} is wider than decoder index width")
        start_low = start & idx_mask
        lines.append(
            f"        if ((pathid >= 12'h{start:03x}) && (pathid <= 12'h{end:03x})) "
            f"idx_r = pathid[{idx_width - 1}:0] - {idx_width}'h{start_low:x};"
        )
    lines.append("    end")
    lines.append(f"    assign target_hit = idx_r != {idx_width}'d{(1 << idx_width) - 1};")
    lines.append("    assign target_idx = idx_r;")
    lines.append("endmodule")
    return "\n".join(lines)


def emit_switch_module(top_module: str, sw: str, inputs: List[str], outputs: List[str], req: ReqNetwork, topo: Topology, layout: HeaderLayout, state_type: str) -> str:
    sw_id = sanitize_ident(sw)
    enum_type = f"{top_module}_{sw_id}_target_e"
    suffix = topo.target_suffixes[sw]
    module_name = f"{top_module}_{sw_id}_monitor"
    all_ports = [(p, "input") for p in inputs] + [(p, "output") for p in outputs]
    lines: List[str] = []
    lines.append(f"module {module_name} #(")
    lines.append(f"    parameter DATA_WIDTH      = {layout.data_width},")
    lines.append(f"    parameter ROUTEID_MSB     = {layout.routeid_msb},")
    lines.append(f"    parameter ROUTEID_LSB     = {layout.routeid_lsb},")
    lines.append(f"    parameter OPC_MSB         = {layout.opc_msb},")
    lines.append(f"    parameter OPC_LSB         = {layout.opc_lsb},")
    lines.append(f"    parameter USER_MSB        = {layout.user_msb},")
    lines.append(f"    parameter USER_LSB        = {layout.user_lsb},")
    lines.append("    parameter USER_MASTER_MSB = 15,")
    lines.append("    parameter USER_MASTER_LSB = 14")
    lines.append(") (")
    lines.append("    input clk,")
    lines.append("    input rst_n")
    for port, _kind in all_ports:
        lines.append(f"    `NOC_FLIT_PORT({port})")
    lines.append(");")
    lines.append("")
    for port, kind in all_ports:
        lines.append(f"    {state_type} {port}_state;")
        lines.append(f"    wire [{layout.seqid_hi - layout.seqid_lo}:0] {port}_seqid;")
        lines.append(f"    wire [1:0] {port}_master;")
        lines.append(f"    wire [{layout.routeid_width - 1}:0] {port}_routeid;")
        lines.append(f"    wire [{layout.pathid_hi - layout.pathid_lo}:0] {port}_pathid;")
        lines.append(f"    wire [{layout.user_width - 1}:0] {port}_user;")
        lines.append(f"    wire {port}_in_packet;")
        if kind == "input":
            lines.append(f"    {enum_type} {port}_target;")
        lines.append(emit_switch_if_instance(top_module, port, kind == "input", sw, req, topo, layout, enum_type, suffix))
        lines.append("")
    lines.append("endmodule")
    return "\n".join(lines)


def emit_switch_if_instance(top_module: str, port: str, has_target: bool, sw: str, req: ReqNetwork, topo: Topology, layout: HeaderLayout, enum_type: str, suffix: str) -> str:
    lines: List[str] = []
    lines.append(f"    {top_module}_flit_if_monitor #(")
    lines.append("        .DATA_WIDTH(DATA_WIDTH),")
    lines.append("        .ROUTEID_MSB(ROUTEID_MSB),")
    lines.append("        .ROUTEID_LSB(ROUTEID_LSB),")
    lines.append("        .OPC_MSB(OPC_MSB),")
    lines.append("        .OPC_LSB(OPC_LSB),")
    lines.append("        .USER_MSB(USER_MSB),")
    lines.append("        .USER_LSB(USER_LSB),")
    lines.append("        .USER_MASTER_MSB(USER_MASTER_MSB),")
    lines.append("        .USER_MASTER_LSB(USER_MASTER_LSB)")
    lines.append(f"    ) u_mon_{port} (")
    lines.append("        .clk(clk),")
    lines.append("        .rst_n(rst_n),")
    lines.append(f"        .data({port}_data),")
    lines.append(f"        .head({port}_head),")
    lines.append(f"        .tail({port}_tail),")
    lines.append(f"        .vld({port}_vld),")
    lines.append(f"        .rdy({port}_rdy),")
    lines.append(f"        .state({port}_state),")
    lines.append(f"        .master({port}_master),")
    lines.append(f"        .routeid({port}_routeid),")
    lines.append(f"        .pathid({port}_pathid),")
    lines.append(f"        .seqid({port}_seqid),")
    lines.append(f"        .user({port}_user),")
    lines.append(f"        .in_packet({port}_in_packet)")
    lines.append("    );")
    if has_target:
        lines.append("")
        idx_width = topo.target_idx_width
        lines.append(f"    wire [{idx_width - 1}:0] {port}_target_idx;")
        lines.append(f"    wire {port}_target_hit;")
        lines.append(f"    {enum_type} {port}_target_r;")
        lines.append(f"    assign {port}_target = {port}_target_r;")
        lines.append(f"    {top_module}_pathid_decode u_decode_{port} (")
        lines.append(f"        .pathid({port}_pathid),")
        lines.append(f"        .target_idx({port}_target_idx),")
        lines.append(f"        .target_hit({port}_target_hit)")
        lines.append("    );")
        allowed = set(req.switch_targets.get((sw, port), []))
        lines.append("    always @* begin")
        lines.append(f"        {port}_target_r = NONE_{suffix};")
        lines.append(f"        if ({port}_pathid != {layout.pathid_hi - layout.pathid_lo + 1}'b0) begin")
        lines.append(f"            if (!{port}_target_hit) begin")
        lines.append(f"                {port}_target_r = UNKNOWN_{suffix};")
        lines.append("            end else begin")
        lines.append(f"                case ({port}_target_idx)")
        for idx in sorted(topo.terminals):
            out = topo.target_maps.get(sw, {}).get(idx)
            if out is None or out not in allowed:
                continue
            lit = topo.target_literals[(sw, out)]
            lines.append(f"                    {idx_width}'d{idx}: {port}_target_r = {lit};")
        lines.append(f"                    default: {port}_target_r = UNKNOWN_{suffix};")
        lines.append("                endcase")
        lines.append("            end")
        lines.append("        end")
        lines.append("    end")
    return "\n".join(lines)


def emit_top_module(top_module: str, req: ReqNetwork, layout: HeaderLayout, state_type: str) -> str:
    all_switch_eps: List[Endpoint] = []
    for sw, ports in req.switch_inputs.items():
        all_switch_eps.extend(Endpoint(sw, p) for p in ports)
    for sw, ports in req.switch_outputs.items():
        all_switch_eps.extend(Endpoint(sw, p) for p in ports)
    switch_eps = dedup_endpoints(all_switch_eps)
    niu_eps = req.masters + req.slaves
    port_names = [endpoint_port_name(ep, switch=False) for ep in niu_eps]
    port_names += [endpoint_port_name(ep, switch=True) for ep in switch_eps]
    lines: List[str] = []
    lines.append(f"module {top_module}_flit_monitor #(")
    lines.append(f"    parameter DATA_WIDTH      = {layout.data_width},")
    lines.append(f"    parameter ROUTEID_MSB     = {layout.routeid_msb},")
    lines.append(f"    parameter ROUTEID_LSB     = {layout.routeid_lsb},")
    lines.append(f"    parameter OPC_MSB         = {layout.opc_msb},")
    lines.append(f"    parameter OPC_LSB         = {layout.opc_lsb},")
    lines.append(f"    parameter USER_MSB        = {layout.user_msb},")
    lines.append(f"    parameter USER_LSB        = {layout.user_lsb},")
    lines.append("    parameter USER_MASTER_MSB = 15,")
    lines.append("    parameter USER_MASTER_LSB = 14")
    lines.append(") (")
    lines.append("    input clk,")
    lines.append("    input rst_n")
    for name in port_names:
        lines.append(f"    `NOC_FLIT_PORT({name})")
    lines.append(");")
    lines.append("")
    for ep in niu_eps:
        name = endpoint_port_name(ep, switch=False)
        lines.append(emit_niu_decl_and_inst(top_module, name, layout, state_type))
        lines.append("")
    for sw in req.switch_inputs:
        mod = f"{top_module}_{sanitize_ident(sw)}_monitor"
        inst = f"mon_{sanitize_ident(sw)}"
        lines.append(f"    {mod} #(")
        lines.append("        .USER_MASTER_MSB(USER_MASTER_MSB),")
        lines.append("        .USER_MASTER_LSB(USER_MASTER_LSB)")
        lines.append(f"    ) {inst} (")
        lines.append("        .clk(clk),")
        lines.append("        .rst_n(rst_n)")
        sw_eps = [Endpoint(sw, p) for p in req.switch_inputs[sw] + req.switch_outputs[sw]]
        for ep in sw_eps:
            short = ep.port
            top_name = endpoint_port_name(ep, switch=True)
            for suffix in ("data", "head", "tail", "vld", "rdy"):
                lines.append(f"        , .{short}_{suffix}({top_name}_{suffix})")
        lines.append("    );")
        lines.append("")
    lines.append("endmodule")
    return "\n".join(lines)


def emit_v(top_module: str, req: ReqNetwork, layout: HeaderLayout, topo: Topology, master_names: Sequence[str]) -> str:
    state_text, state_width = state_enum(master_names)
    state_type = f"{top_module}_flit_state_e"
    state_text = state_text.replace("__STATE_TYPE__", state_type)
    chunks: List[str] = []
    chunks.append("`timescale 1ps/1ps\n")
    chunks.append("/* verilator lint_off DECLFILENAME */")
    chunks.append("/* verilator lint_off UNUSEDSIGNAL */")
    for warning in topo.warnings:
        chunks.append(f"// Generation warning: {warning}")
    chunks.append("")
    chunks.append(state_text)
    chunks.append("")
    chunks.append(emit_target_enums(top_module, req, topo))
    chunks.append("")
    chunks.append(emit_flit_if_monitor(top_module, layout, state_type, state_width, len(master_names)))
    chunks.append("")
    chunks.append(emit_pathid_decode(top_module, layout, topo))
    chunks.append("")
    chunks.append("`define NOC_FLIT_PORT(NAME) \\")
    chunks.append(f"    , input  [{layout.data_width - 1}:0] NAME``_data \\")
    chunks.append("    , input                  NAME``_head \\")
    chunks.append("    , input                  NAME``_tail \\")
    chunks.append("    , input                  NAME``_vld \\")
    chunks.append("    , input                  NAME``_rdy\n")
    for sw, inputs in req.switch_inputs.items():
        outputs = req.switch_outputs.get(sw, [])
        chunks.append(emit_switch_module(top_module, sw, inputs, outputs, req, topo, layout, state_type))
        chunks.append("")
    chunks.append(emit_top_module(top_module, req, layout, state_type))
    chunks.append("")
    chunks.append("`undef NOC_FLIT_PORT")
    return "\n".join(chunks) + "\n"


def discover_hier_macro(top_file: Path, rtl_files: Sequence[Path], top_module: str) -> str:
    top_text = top_file.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"\b([A-Za-z_][A-Za-z0-9_$]*)\s+(module_0)\s*\(", top_text)
    if not m:
        return "SIG"
    parent_inst = m.group(2)
    for f in rtl_files:
        if f.name.endswith("_module_0.v"):
            text = f.read_text(encoding="utf-8", errors="replace")
            m2 = re.search(r"\b([A-Za-z_][A-Za-z0-9_$]*)\s+(module_lRegime_cm_root0)\s*\(", text)
            if m2:
                return f"{parent_inst}.{m2.group(2)}.SIG"
    return f"{parent_inst}.module_lRegime_cm_root0.SIG"


def emit_vh(top_module: str, req: ReqNetwork, layout: HeaderLayout, axuser_bits: Tuple[int, int], hier_macro: str) -> str:
    guard = f"{top_module.upper()}_FLIT_MONITOR_INST_TEMPELETE_VH"
    user_msb = layout.gen_user_payload_lsb + max(axuser_bits)
    user_lsb = layout.gen_user_payload_lsb + min(axuser_bits)
    eps: List[Endpoint] = []
    eps.extend(req.masters)
    eps.extend(req.slaves)
    for sw, ports in req.switch_inputs.items():
        eps.extend(Endpoint(sw, p) for p in ports)
    for sw, ports in req.switch_outputs.items():
        eps.extend(Endpoint(sw, p) for p in ports)
    eps = dedup_endpoints(eps)
    lines = []
    lines.append(f"// Include this file inside module: {top_module}")
    lines.append(f"// It instantiates exactly one debug monitor: u_{top_module}_flit_monitor")
    lines.append("// The monitor observes DUT flit ports and does not drive DUT signals.")
    lines.append("// Override NOC_MON_HIER(SIG) before include if your include hierarchy differs.")
    lines.append("")
    lines.append(f"`ifndef {guard}")
    lines.append(f"`define {guard}")
    lines.append("")
    lines.append("`ifndef NOC_MON_HIER")
    if hier_macro == "SIG":
        lines.append("`define NOC_MON_HIER(SIG) SIG")
    else:
        lines.append(f"`define NOC_MON_HIER(SIG) {hier_macro}")
    lines.append("`endif")
    lines.append("")
    lines.append("`ifndef NOC_MON_MASTER_USER_MSB")
    lines.append(f"`define NOC_MON_MASTER_USER_MSB {user_msb}")
    lines.append("`endif")
    lines.append("`ifndef NOC_MON_MASTER_USER_LSB")
    lines.append(f"`define NOC_MON_MASTER_USER_LSB {user_lsb}")
    lines.append("`endif")
    lines.append("")
    lines.append("`define NOC_CONN(NAME, SIG) \\")
    lines.append("    , .NAME``_data(`NOC_MON_HIER(SIG``_Data)) \\")
    lines.append("    , .NAME``_head(`NOC_MON_HIER(SIG``_Head)) \\")
    lines.append("    , .NAME``_tail(`NOC_MON_HIER(SIG``_Tail)) \\")
    lines.append("    , .NAME``_vld(`NOC_MON_HIER(SIG``_Vld)) \\")
    lines.append("    , .NAME``_rdy(`NOC_MON_HIER(SIG``_Rdy))")
    lines.append("")
    lines.append(f"{top_module}_flit_monitor #(")
    lines.append("    .USER_MASTER_MSB(`NOC_MON_MASTER_USER_MSB),")
    lines.append("    .USER_MASTER_LSB(`NOC_MON_MASTER_USER_LSB)")
    lines.append(f") u_{top_module}_flit_monitor (")
    lines.append("    .clk(`NOC_MON_HIER(i_lRegime_cm0_root_Clk)),")
    lines.append("    .rst_n(`NOC_MON_HIER(i_lRegime_cm0_root_Clk_RstN))")
    for ep in eps:
        is_sw = ep.inst in req.switch_inputs or ep.inst in req.switch_outputs
        name = endpoint_port_name(ep, switch=is_sw)
        lines.append(f"    `NOC_CONN({name}, {ep.path})")
    lines.append(");")
    lines.append("")
    lines.append("`undef NOC_CONN")
    lines.append(f"`endif")
    return "\n".join(lines) + "\n"


def emit_rc(
    top_module: str,
    req: ReqNetwork,
    layout: HeaderLayout,
    master_names: Sequence[str],
    monitor_instance_path: str,
) -> str:
    root = monitor_instance_path.rstrip("/")
    state_count = 1 + 9 * len(master_names) * 2
    state_width = max(1, (state_count - 1).bit_length())
    state_rng = f"[{state_width - 1}:0]"
    seq_rng = f"[{layout.seqid_hi - layout.seqid_lo}:0]"
    lines = []
    lines.append(f"# Verdi/nWave signal template for {top_module}_flit_monitor.")
    lines.append(f"# Monitor instance path: {root}")
    lines.append("")
    def add_first(path: str) -> None:
        lines.append(f"addSignal -h 15 -UNSIGNED {root}/{path}")
    def add_state(name: str) -> None:
        lines.append(f"addSignal -h 15 -UNSIGNED -holdScope {name}_state{state_rng}")
    def add_seq(name: str) -> None:
        lines.append(f"addSignal -c ID_GRAY3 -ls solid -lw 1 -h 15 -UNSIGNED -holdScope {name}_seqid{seq_rng}")
    def add_target(name: str) -> None:
        lines.append(f"addSignal -c ID_GRAY6 -ls solid -lw 1 -h 15 -UNSIGNED -holdScope {name}_target[3:0]")

    lines.append('addGroup "NoC_Flit_Monitor_NIU_Master" -e FALSE')
    for i, ep in enumerate(req.masters):
        name = "mon_" + endpoint_port_name(ep, switch=False)
        if i == 0:
            add_first(f"{name}_state{state_rng}")
        else:
            add_state(name)
        add_seq(name)
    lines.append("")
    lines.append('addGroup "NoC_Flit_Monitor_NIU_Slave" -e FALSE')
    for i, ep in enumerate(req.slaves):
        name = "mon_" + endpoint_port_name(ep, switch=False)
        if i == 0:
            add_first(f"{name}_state{state_rng}")
        else:
            add_state(name)
        add_seq(name)
    lines.append("")

    for sw in req.switch_inputs:
        inst = "mon_" + sanitize_ident(sw)
        lines.append(f'addGroup "NoC_Flit_Monitor_{sw}" -e FALSE')
        first = True
        for port in req.switch_inputs[sw]:
            if first:
                add_first(f"{inst}/{port}_state{state_rng}")
                first = False
            else:
                add_state(port)
            add_target(port)
            add_seq(port)
        for port in req.switch_outputs.get(sw, []):
            if first:
                add_first(f"{inst}/{port}_state{state_rng}")
                first = False
            else:
                add_state(port)
            add_seq(port)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def run(args: argparse.Namespace) -> None:
    rtl_root = Path(args.rtl_root).expanduser().resolve()
    top_file = Path(args.top_file).expanduser().resolve()
    req_md = Path(args.req_md).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    top_module = args.top_module
    monitor_instance_path = args.monitor_instance_path.strip()
    if not top_file.exists():
        raise Fatal(f"top RTL file does not exist: {top_file}")
    if not req_md.exists():
        raise Fatal(f"Req.md does not exist: {req_md}")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", top_module):
        raise Fatal(f"invalid top module name: {top_module}")
    if not monitor_instance_path.startswith("/"):
        raise Fatal("--monitor-instance-path must be an absolute Verdi hierarchy path starting with '/'")
    bits = parse_bit_range(args.axuser_master_bits)
    master_names = [x.strip() for x in args.master_names.split(",") if x.strip()]
    if len(master_names) < 2:
        raise Fatal("provide at least two master names")

    req = parse_req_md(req_md)
    rtl_text, rtl_files = read_rtl_text(rtl_root, top_file)
    if not re.search(rf"\bmodule\s+{re.escape(top_module)}\b", top_file.read_text(encoding="utf-8", errors="replace")):
        raise Fatal(f"top file does not define module {top_module}")
    validate_endpoints(req, rtl_text)
    layout = extract_header_layout(rtl_text, bits)
    topo = build_topology(req, rtl_text)
    for warning in topo.warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    hier_macro = discover_hier_macro(top_file, rtl_files, top_module)

    release = out_dir / f"{top_module}_flit_monitor_release"
    if release.exists():
        shutil.rmtree(release)
    release.mkdir(parents=True, exist_ok=True)
    v_path = release / f"{top_module}_flit_monitor.v"
    vh_path = release / f"{top_module}_flit_monitor_inst_templete.vh"
    rc_path = release / f"{top_module}_flit_monitor.rc"
    v_path.write_text(emit_v(top_module, req, layout, topo, master_names), encoding="utf-8")
    vh_path.write_text(emit_vh(top_module, req, layout, bits, hier_macro), encoding="utf-8")
    rc_path.write_text(emit_rc(top_module, req, layout, master_names, monitor_instance_path), encoding="utf-8")

    tar_path = out_dir / f"{top_module}_flit_monitor_release.tar"
    if tar_path.exists():
        tar_path.unlink()
    with tarfile.open(tar_path, "w") as tar:
        for p in (v_path, vh_path, rc_path):
            tar.add(p, arcname=f"{release.name}/{p.name}")

    print(f"Generated release: {release}")
    print(f"Generated tar:     {tar_path}")


def parse_bit_range(text: str) -> Tuple[int, int]:
    m = re.fullmatch(r"\s*(\d+)\s*:\s*(\d+)\s*", text)
    if not m:
        m1 = re.fullmatch(r"\s*(\d+)\s*", text)
        if not m1:
            raise Fatal(f"invalid --axuser-master-bits: {text}")
        bit = int(m1.group(1))
        return bit, bit
    return int(m.group(1)), int(m.group(2))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rtl-root", required=True)
    parser.add_argument("--top-file", required=True)
    parser.add_argument("--top-module", required=True)
    parser.add_argument("--monitor-instance-path", required=True)
    parser.add_argument("--req-md", required=True)
    parser.add_argument("--axuser-master-bits", required=True)
    parser.add_argument("--master-names", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    try:
        run(args)
    except Fatal as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
