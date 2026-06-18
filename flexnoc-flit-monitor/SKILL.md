---
name: flexnoc-flit-monitor
description: 生成 FlexNoC Req 网络 flit monitor 调试包。Use when Codex needs to create Verilog monitor RTL, an include template, and a Verdi/nWave rc file from a FlexNoC top RTL, monitor instance path, and Req.md Record table, especially for observing Req flit state, seqid, master attribution, and predicted switch target during NoC congestion analysis.
---

# FlexNoC Flit Monitor

这个 skill 用于把 FlexNoC 生成 RTL 中的 Req 网络接口，转换成可在仿真/Verdi 中观察的 flit monitor 包。v1 只支持 Req 网络，不生成 Resp 网络 monitor。

## 必需输入

开始前必须确认下面四个输入。如果缺少、不明确，或用户提供的内容互相矛盾，停止并请用户补齐：

- NoC 顶层 RTL 文件路径、顶层 module 名、monitor instance 路径。生成的 `.vh` 会被 include 到这个顶层 module 内部；生成的 `.rc` 会使用 monitor instance 路径作为波形信号根路径。
- `Req.md` 文件路径。只参考其中 `Record` 栏，不读取、不解析、不依赖 JSON。
- `AxUser` 与 master 编号的对应关系，例如 `AxUser[6:5] -> M0,M1,M2,M3`。

## 工作目录与输入预处理

使用这个 skill 时，先建立一个独立工作目录。所有中间文件、临时文件、隐藏文件和最终 release/tar 产物都放在这个目录下，不要散落到项目根目录或 RTL 源码目录。

执行 Python 脚本前，先人工/脚本检查 `Req.md` 的格式是否符合本 skill 的解析预期：脚本只从 `(a)`、`(b)`、`(d)` section 的 `Record` 栏读取 `instance.port -> instance.port` 形式的 flit 连接。如果用户提供的 `Req.md` 语义完整但 Markdown 格式与脚本预期不同，可以在工作目录内生成一份“仅修改格式、不修改内容含义”的规范化 `Req.md` 副本，并把这份副本作为脚本输入。不要在规范化时新增、删除、重排或猜测 flit 连接；如果无法确认格式转换是否保持语义等价，停止并报告。

## 生成器

优先使用脚本：

```bash
python3 scripts/generate_req_flit_monitor.py \
  --rtl-root <rtl_dir> \
  --top-file <noc_top_file.v> \
  --top-module <noc_top_module> \
  --monitor-instance-path <verdi_monitor_instance_path> \
  --req-md <Req.md> \
  --axuser-master-bits 6:5 \
  --master-names M0,M1,M2,M3 \
  --out-dir <output_dir>
```

脚本只使用 Python 标准库。产出：

- `<top_module>_flit_monitor_release/<top_module>_flit_monitor.v`
- `<top_module>_flit_monitor_release/<top_module>_flit_monitor_inst_templete.vh`
- `<top_module>_flit_monitor_release/<top_module>_flit_monitor.rc`
- `<top_module>_flit_monitor_release.tar`

`.tar` 内只放 release 目录下的 `.v/.vh/.rc`。

## 输入解析规则

从 `Req.md` 的 `Record` 栏解析 flit 连接：

- section `(a)` 的左侧是 master NIU flit 口，只生成 `state/seqid` monitor。
- section `(b)` 的右侧是 slave NIU flit 口，只生成 `state/seqid` monitor。
- section `(d)` 的左侧去重后是 switch input flit 口，生成 `state/target/seqid` monitor。
- section `(d)` 的右侧去重后是 switch output flit 口，生成 `state/seqid` monitor。
- section `(d)` 的 `input -> output` 关系是每个 switch input 的合法 target 候选集合。

严格保持这三类 section 的职责边界：

- `(a)` 和 `(b)` 只决定 NIU flit 口 monitor 范围，不参与 target enum 生成。
- 只有 switch input flit 口需要 `target`，且这些 input 必须来自 `(d)` 左侧。
- `target` 的命名空间只包含同一个 switch 的 output flit 口，且这些 output 必须来自 `(d)` 右侧。
- Master NIU flit 口、Slave NIU flit 口、terminal/slave 名称、MEM 编号、link 中间模块名都不是 target enum value。

如果 `Req.md` 中的实例名、端口名无法在 RTL 中找到，停止并报告缺失项。

## RTL 解析规则

不要在 skill 文档中写死 header bit 位置。生成器必须从 RTL 中解析：

- `TxHdr` 如何拼成 flit HEAD。
- `Tx_Data` 如何放置 `TxHdr`。
- `RouteId` 如何由 aperture/path、`GenRx_Req_SeqId`、disorder bit 等字段拼出。
- `Gen_Req_User` / `GenRx_Req_User` 如何进入 HEAD。
- Req header opcode 字段位置，用于区分 R/W。

如果 RTL 风格变化导致无法确认 seqid、user、opcode、path/route 字段位置，停止并报告。不要生成猜测结果。

注意区分两类失败：

- HEAD packing、`seqid`、`user`、opcode 或 route/path 字段位置无法确认时，必须停止，因为 state/seqid/master 归属会失真。
- 某个具体 PathId 无法被当前 monitor 可靠映射到 switch output 时，不要停止，也不要猜测；生成的 monitor 应把该 input 的 `target` 显示为对应 switch 的 `UNKNOWN`。

## Monitor RTL 结构

生成的 `.v` 应保持这个结构：

- 顶部定义全局 `state` enum。
- 每个 switch 定义独立 target enum type。这个 enum type 使用该 switch 在 `Req.md` section `(d)` RHS 中出现过的所有 output flit port 的并集，并额外包含 `NONE_<switch_suffix>` 和 `UNKNOWN_<switch_suffix>`。
- `switch_suffix` 使用能区分当前所有 switch 的最短数字后缀。例如只有 `switch_0_5_req_main`、`switch_0_6_req_main`、`switch_0_7_req_main`、`switch_0_8_req_main` 时，后缀分别为 `5/6/7/8`；如果存在冲突，再扩展为更长后缀。
- 通用 `flit_if_monitor` 解析 HEAD、保存 packet context，并输出 `state/seqid/pathid/user`。
- 每个 switch 生成一个子 monitor module。子 module 内部信号只保留 flit port 名，例如 `from_Link_24_state`、`from_Link_24_target`、`from_Link_24_seqid`。
- 顶层 monitor module 只例化 NIU monitor 和 switch 子 monitor，不驱动 DUT。

## State 规则

`state` 用 Verdi enum 友好的短名字：

- `I`：idle。
- `F/FH/FT/FHT`：`vld & rdy`，分别表示普通 fire、head fire、tail fire、head-tail 单拍包 fire。
- `S/SH/ST/SHT`：`vld & !rdy`，分别表示普通 stall、head stall、tail stall、head-tail stall。
- `B`：packet 中间 `vld=0` 的 bubble。
- 非 idle 状态必须带 master 编号和读写方向，例如 `FH0R`、`SHT3W`。
- R/W 根据 RTL 解析出的 Req header opcode 判断，不在 skill 中固定 bit 位置。

## Seqid 与 User 规则

- `seqid` 在 HEAD 中的位置从 RTL 解析。若 RTL 表明 `SeqId` 是 `RouteId` 子字段，则按 RTL 拼接关系生成切片。
- `TAIL` fire 当拍仍显示当前 packet 的 seqid；进入 idle 后清零。
- `.rc` 中 `seqid` 使用 `ID_GRAY3`。
- master 归属由用户提供的 `AxUser` bit 与 RTL 中 `AxUser -> Gen_Req_User -> HEAD` 的 packing 推导。
- 如果无法确认原始 `AxUser` 到 HEAD user 字段的映射，停止并报告。

## Target 规则

- 不采 DUT 内部 demux `Sel`。
- target enum 候选必须只来自 `Req.md` section `(d)`。
- 每个 switch 生成一个 target enum type，而不是每个 input 单独生成 enum type。
- 对某个 switch 来说，它的 target enum values 必须是这个 switch 在 `(d)` RHS 出现过的所有 switch output flit port 去重并集，再加上 `NONE_<switch_suffix>` 和 `UNKNOWN_<switch_suffix>`。
- enum value 命名参考：
  ```systemverilog
  typedef enum logic [3:0] {
      NONE_5                       = 4'd0,
      to_Link_75                   = 4'd1,
      to_Link_78                   = 4'd2,
      to_link_0_5_to_0_6_0_req     = 4'd3,
      to_link_1_5_to_1_6_0_req     = 4'd4,
      UNKNOWN_5                    = 4'd15
  } noc_left_sep_switch_0_5_req_target_e;
  ```
- `NONE` 表示该 switch input 当前没有有效 packet/target；`UNKNOWN` 表示 monitor 无法把当前 packet decode 到该 input 的合法 target。实际查 PathId 时遇到空洞、未解析范围、未覆盖目标、或结果不在该 input 的 `(d)` RHS 合法集合内，都应显示 `UNKNOWN`。
- 对每个 `(d)` 左侧 switch input endpoint，它的 target 赋值逻辑只能赋值为 `(d)` 中同一个 input 对应的 RHS switch output port、`NONE` 或 `UNKNOWN`。
- 不允许根据 section `(a)`、section `(b)`、Slave NIU 名称、terminal 名称、MEM 编号、拓扑猜测、端口名相似度或 `to_Link_xx/from_Link_xx` 字符串关系来新增、删除或过滤 target enum value。
- monitor 从 HEAD 中解析出的 path/route 信息，按 RTL 中 switch routing/demux decode 或生成器能够从 RTL/Req.md 可靠恢复出的等价关系，预测该 input 应去哪个 switch output。
- 预测结果必须落在该 input 从 `(d)` 得到的合法 target 集合内；不一致时显示/归类为 `UNKNOWN`。不要为了避免 `UNKNOWN` 而引入基于名称相似度或拓扑直觉的额外 target。
- target enum value 使用 `Req.md` section `(d)` 中真实 switch output flit port 名，例如 `to_Link_75`，不改成方向名，也不改成 slave/terminal 名。
- `NONE` 和 `UNKNOWN` 需要带 switch 后缀避免 enum 名冲突；output 名若全局冲突，再追加最短 switch 后缀消歧。
- `.rc` 中 `target` 使用 `ID_GRAY6`。

## `.vh` 规则

- `.vh` include 到 NoC 顶层 module 内，只例化一个 `u_<top_module>_flit_monitor`。
- 自动生成 `NOC_MON_HIER(SIG)` 宏，用于连接真实 flit port 的 `_Data/_Head/_Tail/_Vld/_Rdy`。
- 若自动层级无法覆盖当前 include 位置，应在 `.vh` 注释中说明如何覆盖宏。
- monitor instance 路径应指向 `.vh` 例化出来的实例，例如仿真层级中的 `/.../u_<top_module>_flit_monitor`。

## `.rc` 规则

- 不使用 subgroup。
- group 固定为：master NIU 一个 group、slave NIU 一个 group、每个 switch 一个 group。
- NIU 与 switch output 顺序：`state`、`seqid`。
- switch input 顺序：`state`、`target`、`seqid`。
- state 不加 `-HEX`，保持 Verdi enum 显示友好。
- `target` 使用 `-c ID_GRAY6 -ls solid -lw 1 -h 15 -UNSIGNED`。
- `seqid` 使用 `-c ID_GRAY3 -ls solid -lw 1 -h 15 -UNSIGNED`。
- waveform root path 使用用户提供的 monitor instance 路径，不再依赖通用占位符。

## 验证流程

生成后至少做这些检查：

- 检查 `Req.md` section `(a)` 左侧的 master NIU flit 口都有 `state/seqid`，且没有 `target`。
- 检查 `Req.md` section `(b)` 右侧的 slave NIU flit 口都有 `state/seqid`，且没有 `target`。
- 检查 `Req.md` section `(d)` 左侧的 switch input flit 口都有 `state/target/seqid`。
- 检查 `Req.md` section `(d)` 右侧的 switch output flit 口都有 `state/seqid`，且没有 `target`。
- 对每个 switch，检查 target enum 完全覆盖并且只覆盖该 switch 在 `Req.md` section `(d)` RHS 中出现的所有 switch output port，再加 `NONE/UNKNOWN`。
- 对每个 switch input，检查 target 赋值逻辑覆盖并且只覆盖 `Req.md` section `(d)` 中该 input 对应的所有 RHS switch output port，再加 `NONE/UNKNOWN`。
- 检查异常 PathId、未命中 PathId、或无法归入该 input 合法 RHS 的 PathId 都会显示为该 switch 的 `UNKNOWN`，不会落到错误的 output port。
- 检查 `.vh` 中无未定义实例/端口，且 `_Data` 宽度与 monitor 参数一致。
- 用 Verilator/Yosys 对生成的 `.v` 做轻量语法/结构检查；如果本机缺工具，明确说明未运行。
- Icarus/iverilog 只作为辅助参考，不作为硬性验收。该 monitor 为了让 Verdi 显示 enum 名称，会使用 SystemVerilog enum；即使用 `iverilog -g2012`，Icarus 也可能对 `fire_body_state = is_write ? F0W : F0R;` 这类 enum 类型三目赋值报 `This assignment requires an explicit cast`。如果 Verilator/Yosys 或目标商业仿真器检查通过，这类 Icarus enum/cast 兼容性报错可以忽略。
- 检查 `.rc` 中 state/target/seqid 数量、顺序、颜色符合规则。
- 检查 `.tar` 只包含 release 目录下的 `.v/.vh/.rc`。
