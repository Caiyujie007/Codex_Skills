---
name: flexnoc-diagram
description: 使用中文流程提取 FlexNoC 生成 RTL 的 NoC Req/Resp 结构关系，并基于 Req.md、Resp.md 与 draw.io 绘制 NoC 架构图。用于用户要求分析 FlexNoC NoC 拓扑、master/slave NIU、switch req/resp 模块、flit 连接关系、Req/Resp 网络或生成 draw.io/SVG/PNG 架构图时。
---

# FlexNoC 架构图绘制

本 skill 用于画 FlexNoC 生成 RTL 的 NoC 架构图。整个工作分为两个步骤：

1. 理清 NoC 结构关系，生成 `Req.md` 与 `Resp.md`。
2. 以 `Req.md` 与 `Resp.md` 为输入，使用 `$drawio` skill 生成 draw.io 架构图。

## 步骤一：理清 NoC 结构关系

你需要建立一个独立的目录，所有中间文件需要放在这个目录下。

### 首先是输入条件，必须要我显示提供，如果没有提供或者则不要自己瞎猜，而是停下工作问我：

- (a) NoC顶层代码的位置模块入口名;
- (b) 画架构图所涉及到的master（_I接口的）、slave（_T接口的）名字以及switch名字，你需要去NoC代码中找到。master、slave的NIU及switch节点的req、resp模块，如果没有提供则不要自己瞎猜，而是停下工作问我。
- 其中 master 必须只在 `_I` 接口/NIU 候选中寻找，slave 必须只在 `_T` 接口/NIU 候选中寻找；不要把同名前缀但接口方向不匹配的 NIU 当成候选。

### 其次，你需要理清我给你提供的master（集合A）、slave（集合B）的NIU及switch节点（集合C）的req、resp模块之间的连接关系(连接关系忽略buffer / pipe / regslice / link module)，过程如下：

#### （1）先处理Req网络，在目录下一个Req网络的MD文件(步骤(a)(b)(c)(d)在MD中分段记录)，并：

- (a) 对于所有集合A中的Master NIU（for i=0 : length(A) ），在代码中寻找其Req口（记录下端口名a）所驱动的switch（记录下switch及其端口名 swXXX.b）。若此switch不在我提供的集合C之中则停下工作并告诉我，否则在MD中记录 master[i].a -> swXXX.b;
- (b) 对于所有集合B中的Slave NIU（for i=0 : length(B) ），在代码中寻找驱动其Req口（记录下端口名a）的switch（记录下switch及其端口名 swXXX.b）。若此switch不在我提供的集合C之中则停下工作并告诉我，否则在MD中记录 swXXX.b -> slave[i].a;
- (c) 对于集合C中的所有switch的Req模块（for i=0 : length(C) ）,遍历其所有输出Flit流（for j=0 : length(C[i].req.output_flits) ），在代码中寻找C[i].req.output_flits[j]所驱动的模块，并分情况判断：
  - case 0:  如果C[i].req.output_flits[j]驱动的是master、slave NIU，在前两个步骤中已经记录过了，无需再次记录；
  - case 1:  如果C[i].req.output_flits[j]驱动的是switch的Resp则判定为异常，停止工作并告诉我；
  - case 2:  如果C[i].req.output_flits[j]驱动的是switch.Req（记录下switch及其端口名 swXXX.b），则判断这个switch（swXXX）是否在集合C之中，如果在集合C之中，则在MD中记录 C[i].req.output_flits[j] -> swXXX.b；
- (d) 对于集合C中的所有switch的Req模块（for i=0 : length(C) ）,遍历其所有输入Flit流（for j=0 : length(C[i].req.input_flits) ），如果这个输入flit流C[i].req.input_flits[j]出现在了步骤(a)(b)(c)所产出的记录MD中（则该输入flit流是与提供的master（集合A）、slave（集合B）的NIU及switch节点（集合C）的req、resp模块有关）。则我们在这个switch模块（C[i]）代码内部找到C[i].req.input_flits[j]所连接的模块：
  - case0:   如果是DEMUX模块，则遍历这个DEMUX模块的每一个输出流（for k=0:length(C[i].req.input_flits[j].demux.output_filts），这个输出流必然是（直接地或者经过MUX间接地）驱动了该switch的某个输出flits流（z）。如果这个输出flits流z出现在了步骤(a)(b)(c)所产出的记录MD中（则该输出flit流是与提供的master（集合A）、slave（集合B）的NIU及switch节点（集合C）的req、resp模块有关），则在MD中记录C[i].req.input_flits[j] -> C[i].req.z；
  - case1:   如果不是DEMUX模块，则必然是（直接地或者经过MUX间接地）驱动了该switch的某个输出flits流（z）。如果这个输出flits流z出现在了步骤(a)(b)(c)所产出的记录MD中（则该输出flit流是与提供的master（集合A）、slave（集合B）的NIU及switch节点（集合C）的req、resp模块有关），则在MD中记录C[i].req.input_flits[j] -> C[i].req.z；

#### （2）再处理Resp网络，在目录下一个Resp网络的MD文件(步骤(a)(b)(c)(d)在MD中分段记录)，并：

- (a) 对于所有集合A中的Master NIU（for i=0 : length(A) ），在代码中寻找驱动其Resp口（记录下端口名a）的switch（记录下switch及其端口名 swXXX.b）。若此switch不在我提供的集合C之中则停下工作并告诉我，否则在MD中记录 swXXX.b -> master[i].a;
- (b) 对于所有集合B中的Slave NIU（for i=0 : length(B) ），在代码中寻找其Resp口（记录下端口名a）所驱动的switch（记录下switch及其端口名 swXXX.b）。若此switch不在我提供的集合C之中则停下工作并告诉我，否则在MD中记录 slave[i].a -> swXXX.b ;
- (c) 对于集合C中的所有switch的Resp模块（for i=0 : length(C) ）,遍历其所有输出Flit流（for j=0 : length(C[i].resp.output_flits) ），在代码中寻找C[i].resp.output_flits[j]所驱动的模块，并分情况判断：
  - case 0:  如果C[i].resp.output_flits[j]驱动的是master、slave NIU，在前两个步骤中已经记录过了，无需再次记录；
  - case 1:  如果C[i].resp.output_flits[j]驱动的是switch的Req则判定为异常，停止工作并告诉我；
  - case 2:  如果C[i].resp.output_flits[j]驱动的是switch.Resp（记录下switch及其端口名 swXXX.b），则判断这个switch（swXXX）是否在集合C之中，如果在集合C之中，则在MD中记录 C[i].resp.output_flits[j] -> swXXX.b；
- (d) 对于集合C中的所有switch的Resp模块（for i=0 : length(C) ）,遍历其所有输入Flit流（for j=0 : length(C[i].resp.input_flits) ），如果这个输入flit流C[i].resp.input_flits[j]出现在了步骤(a)(b)(c)所产出的记录MD中（则该输入flit流是与提供的master（集合A）、slave（集合B）的NIU及switch节点（集合C）的req、resp模块有关），则我们在这个switch模块（C[i]）代码内部找到C[i].resp.input_flits[j]所连接的模块：
  - case 0:  如果是DEMUX模块，则遍历这个DEMUX模块的每一个输出流（for k=0:length(C[i].resp.input_flits[j].demux.output_filts），这个输出流必然是（直接地或者经过MUX间接地）驱动了该switch的某个输出flits流（z）。如果这个输出flits流z出现在了步骤(a)(b)(c)所产出的记录MD中（则该输出flit流是与提供的master（集合A）、slave（集合B）的NIU及switch节点（集合C）的req、resp模块有关），则在MD中记录C[i].resp.input_flits[j] -> C[i].resp.z；
  - case1:   如果不是DEMUX模块，则必然是（直接地或者经过MUX间接地）驱动了该switch的某个输出flits流（z）。如果这个输出flits流z出现在了步骤(a)(b)(c)所产出的记录MD中（则该输出flit流是与提供的master（集合A）、slave（集合B）的NIU及switch节点（集合C）的req、resp模块有关），则在MD中记录C[i].resp.input_flits[j] -> C[i].resp.z；

### 步骤一补充说明

- 即使执行完整画图流程，也必须先完整生成 `Req.md` 与 `Resp.md`，并完成步骤一自检；在 `Req.md` / `Resp.md` 生成并确认之前，禁止开始编写或运行 draw.io / generate_diagram 相关脚本。
- `Req.md` 与 `Resp.md` 是本 skill 的重要产出，不是画图脚本的临时输入缓存；不能为了尽快画图而简化步骤一过程、只记录代表路径或只记录绘图时用到的一部分连接。
- 步骤二只能消费步骤一已经生成的 `Req.md` / `Resp.md`，不得重新追 RTL 来替代、修补或过滤步骤一产物。
- 步骤一产物格式可参考 `references/step1-output-format/Req.md` 与 `references/step1-output-format/Resp.md`。参考文件每段只保留一条记录，只用于说明 Markdown 分段、表格列和 evidence 写法；不要复制其中的具体节点名、端口名或拓扑关系。
- 保留 RTL instance name 与 port name 原名，不要改写成概念名。
- `Req.md` / `Resp.md` 的 Markdown 分段、表格列、`Record` 与 evidence 写法按上述参考文件执行；`Record` 只表达用于画图的抽象连接关系，evidence 只作为 RTL 追踪证明，不作为图中的独立节点。
- evidence 只展开到当前连接关系下一层 hierarchy 的 instance/port 级别，不继续进入这些子模块内部实现。
- 对 switch-to-switch 连接，不要按“源 switch -> 目的 switch”或“同一对 switch”去重；同一对 switch 之间可能存在多条并行 flit/link family，每个 distinct output flit/input flit port 都必须逐条追踪、逐条记录。
- `(d)` 只记录 RTL 中真实追到的内部可达关系，不能做相关 input/output 笛卡尔积，也不能只写代表路径；没有 DEMUX output 或 case1 可达 evidence 的关系不要记录。
- 执行 `(d)` 时，不要假设相关 input flit 一定连接到 DEMUX；如果找不到对应 DEMUX，也必须继续追踪该 input flit 是否通过 pipe / buffer / regslice / mux 等当前层级实例直接连接到相关 output flit，并按 case1 记录，不能因为没有 DEMUX 就跳过该 input flit。

## 步骤二：基于 Req.md / Resp.md 画图

步骤二以步骤一提取的 `Req.md` 与 `Resp.md` 为输入，并以 `$drawio` 为 skill，在步骤一建立的独立工作目录中进行工作。

- 如果找不到 `Req.md` 或 `Resp.md`，停止并告诉操作者缺少输入。
- 如果找不到 `$drawio` skill，停止并告诉操作者缺少 draw.io 绘图依赖。
- 使用 `$drawio` 时必须遵守它的 Tool Preflight：如果缺少 `node`、`drawio`、XML/SVG 校验工具或所选路线需要的工具，停止并告诉操作者安装，不要用其他方法替代。
- 所有脚本、中间文件、最终输出都放在步骤一建立的独立工作目录中。
- 不要把任何脚本、中间文件或最终输出放到步骤一独立工作目录之外；隐藏目录也不例外。如果需要临时文件，也必须放在该独立工作目录内部。
- `.drawio` 是唯一图源，SVG/PNG 必须由 draw.io 从 `.drawio` 导出。
- 最终只需要 `.drawio`、draw.io 导出的 `.svg`、draw.io 导出的 `.png`。
- 不要把脚本自行绘制的 SVG 当作最终产物；这会造成 `.drawio`、SVG、PNG 三者不一致。

### 步骤二风格参考图

- 使用本 skill 的 `assets/flexnoc-style-reference.drawio` 作为 draw.io 风格参考图；`assets/flexnoc-style-reference.png` 只作为人眼快速预览。
- 画图前先参考 `assets/flexnoc-style-reference.drawio` 中的 mxCell 结构、几何和样式，包括：Req/Resp 左右分栏、master/switch/slave 相对位置、颜色、字体、switch 尺寸、port label 贴边方式、内部灰色虚线、switch-to-switch lane 分区和图层顺序。
- 对容易出错的画图细节，必须优先参考 `assets/flexnoc-style-reference.drawio` 中对应元素的具体几何做法，而不是只参考颜色或大体布局。重点包括：flit port label 与模块边界的距离、黑色实线端点贴边方式、switch-to-switch 垂直 lane 的左右分区、上下边界长 port label 的换行/错层、内部灰色虚线起止点与 port label 的相对位置。
- `assets/flexnoc-style-reference.drawio` 只能作为风格参考，不能直接复制为最终 `.drawio`；最终 `.drawio` 必须由当前 `Req.md` / `Resp.md` 和用户显式提供的集合生成。
- 只借鉴参考图的布局和风格，不要复制参考图里的具体工程节点名、端口名、连接关系或 MD 内容。
- 当前输出图的节点、端口、实线连接和内部虚线连接，仍然只能来自当前任务的 `Req.md`、`Resp.md` 以及用户显式提供的 master/slave/switch 集合。
- 如果风格参考图缺失、无法读取或无法作为 draw.io XML 解析，停止并报告，不要自行改用 SVG/PNG 反推风格。

### 步骤二 Drawing Rules

- 图分左右两部分：左侧画 Req 网络，右侧画 Resp 网络。
- 默认布局为 overview 架构图：无论 Req 网络还是 Resp 网络，master NIU 都放在 switch 左侧，slave NIU 都放在 switch 右侧；箭头方向仍严格按 `Req.md` / `Resp.md` 的 `Record`，不要为了布局改写方向。
- 如果 switch instance name 中包含 FlexNoC 坐标信息，例如常见的 `switch_<x>_<y>_*` 形式，优先按坐标排布；同一列中坐标较大的行放上方、坐标较小的行放下方。没有可识别坐标时，按用户给定集合顺序或从连接拓扑推导的层级顺序排布。
- Req/Resp 两侧同一坐标或同一逻辑层级的 switch 必须横向对齐；如果两侧高度不同，以较高的一侧作为该层高度参考。
- 画布保持紧凑的 overview 尺寸，控制 master/switch/slave 水平间距、Req/Resp 间距、switch 间垂直间距和标题/legend 占用空间；不要因为自动布局生成大量空白或过大的画布。
- 实线连接只来自 `Req.md` / `Resp.md` 的 `(a)(b)(c)` 记录，方向严格按 MD 中记录的方向。
- switch 内部灰色虚线只来自 `(d)` 记录，表示物理可达关系，不表示运行时一定选中。
- 画图前先解析并检查 `Req.md` / `Resp.md`：实线数量来自 `(a)(b)(c)`，内部虚线数量只来自过滤后的 `(d)`；不要在画图阶段新增推断连接。
- switch 标题必须使用完整 RTL instance name，例如 req/resp switch module instance 的原名；不要改成概念名、简称或重新命名。switch 标题作为模块识别背景信息，应使用灰色半透明文字（例如 `fontColor=#64748B;opacity=45`），避免与内部灰色虚线争抢视觉主导。
- switch 必须画成矩形或圆角矩形 module box，用来承载 flit port label 和内部可达虚线；不要画成菱形、router symbol、点状节点或其他抽象拓扑符号。
- master/slave 节点显示用户给定的名字、角色序号和对应 NIU instance；每个 master、每个 slave 都必须是独立模块框，不要把多个 endpoint 合并成一个容器、表格、泳道、堆叠卡片或带分割线的组合框。
- port label 使用 RTL port 原名，图中所有可见 flit port label 必须与 `Req.md` / `Resp.md` 的 `Record` 端点中的 port name 一致。
- 图中的 instance name 与 flit port name 不允许缩写、改名或语义压缩；尤其是 switch-to-switch port label 不允许改成 `L0/L1`、方向简写、编号别名或其他 alias。完整 RTL port name 不能只保留在 MD 中而在图上缩写；如果太长，只能换行、调小字号、加宽 switch 或调整布局。
- 每个 flit port 必须有独立 label，并且 label 必须靠近对应 port anchor；不要把多个 port name 合并到同一个 text cell、一行长文本、逗号列表或共享标签里。
- flit port label 使用加粗文字，推荐 draw.io 样式为 `fontSize=9;fontStyle=1;fontColor=#334155`，以保持与风格参考图一致并提高可读性。
- port label 必须保持可读字号；如果 port 数量多，通过增加 switch 宽度/高度、分散 port anchor 或换行处理，不要通过合并标签或无限缩小字号解决。
- 所有 flit port label 之间必须留出可见间隔，不能重叠、贴在一起或视觉上连成一串；尤其是 switch 上下边界的长 port label，如果名字过长导致重叠或间距不足，优先把同一个 flit port label 分成多行显示，draw.io XML 中换行使用 `&#xa;`；如果仍不够，再通过增加 switch 宽度、增加 lane 间距、错层或调整字号来保证每个 label 独立可辨。不要因为名字过长而缩写、改名、合并 label 或让文字重叠。
- 上下边界的 flit port label 必须水平显示，不允许旋转成竖排文字，也不要把文字沿连线方向倾斜；长 port name 通过 `&#xa;` 换行、上下错层、增加 switch 宽度/高度或增加 lane 间距解决。
- 上下边界的 flit port label 与 switch-to-switch 黑色实线必须分离：实线只贴到模块边界 anchor，label 放在边界内侧并紧贴 anchor，黑色实线不能穿过、压住或遮挡 port label。
- 所有 NIU、Switch 之间的实线箭头使用黑色，箭头只贴到 NIU/Switch 边界，不穿入模块框内部。
- 黑色实线、模块边界、flit port label、灰色内部虚线必须满足明确的视觉顺序。对于 master NIU 输出到 switch 输入的连接，顺序必须是：`NIU 内部 flit port label -> NIU 边界 -> 黑色实线箭头 -> Switch 边界 -> Switch 内部 flit port label -> 灰色内部虚线`。
- 对于 switch 输出到 slave NIU 输入的连接，顺序必须是：`灰色内部虚线 -> Switch 内部 flit port label -> Switch 边界 -> 黑色实线箭头 -> NIU 边界 -> NIU 内部 flit port label`。
- 黑色实线的箭头头部和尾部只能贴到模块边界 anchor，不得压住、穿过或覆盖任何 flit port label；flit port label 必须位于模块框内部的边界内侧，不能放在黑色实线上或模块框外侧。
- switch-to-switch 连接按“先定相对方位、再定相向端口、再分 lane、最后画线”的流程处理。对每条 `Record`，先定位源 switch 和目的 switch 的几何中心，判断二者主要是上下、左右还是斜向关系；箭头方向始终严格按 `Record` 从源 port 指向目的 port，不因布局方向而改写。
- 根据相对方位选择 flit port 所在边界：上下关系使用上下相向边界，左右关系使用左右相向边界；斜向关系使用源 switch 朝向目的 switch 的水平边界（右边或左边）以及目的 switch 朝向源 switch 的垂直边界（顶边或底边）。反向 `Record` 重新以该记录的源/目的计算，不套用前一条线的方向。
- 多条 switch-to-switch link 在两个 switch 之间的空隙内分配平行 lane，lane 只用于避免交叉和提高可读性，不改变 `Record` 方向。上下关系使用垂直 lane，左右关系使用水平 lane，斜向关系使用靠近两者中间空隙的平行短斜线或短折线；同一对 switch 的多条 link 不能合并成共享干线后再分叉。
- lane 的默认分区用于保持 Req/Resp 读图一致性：上下关系中，Req 的上到下在左、下到上在右，Resp 反向；左右关系中，Req 的左到右在上、右到左在下，Resp 反向。斜向关系按相同原则把相反方向分到两组平行 lane 中，并优先让线段贴近各自的相向 port。
- switch-to-switch 实线必须留在两个 switch 之间的空隙内，优先使用固定 source/target point 的直线或短折线；不得把 port 放到非相向边界，不得绕到 switch 外侧形成大 U 形路径，不得穿过 switch box、其他模块、其他 port label 或同组黑色实线。
- 所有 flit port 名字放在模块内部、紧贴模块边界；不要使用白色小框。
- 对同一个 switch，左右边界 flit port label 的内侧形成上下边界 port label 的安全水平范围；所有位于 switch 上边界或下边界的 flit port label，其整个文字 bounding box 必须落在这个安全范围内，并留出可见内侧间隔。不能只让 anchor 点在范围内而让文字伸到左右边 flit port label 的外侧；如果超过范围，必须把对应 lane/label 向 switch 中心移动、对 label 使用 `&#xa;` 多行显示、增加 switch 宽度或增加左右内边距。
- 当上下边界存在多条 switch-to-switch link 时，每个 port label 应在自己的 lane 附近独立水平摆放；可以分成靠边界的第一行和稍靠内侧的第二行来避让，但不能合并成一条长文本，也不能旋转。
- switch 内部灰色虚线箭头应紧贴 flit port 名字，但不压住 flit port 名字：以 flit port 名字做一个几乎紧贴文字的外接矩形，虚线连接到该矩形靠近 switch 中心一侧边的中心点。视觉顺序为：模块边界 -> flit port 名字 -> 灰色虚线箭头。内部虚线使用灰色、细线、直线 dashed arrow；优先使用直线边或 `edgeStyle=none`，避免 draw.io 自动路由成弯弯绕绕的路径。
- `(d)` 的每条内部可达记录都必须体现为 switch box 内部的一条灰色虚线箭头；不能省略，不能只写在图例、注释或 note 里。
- 不要为了让外部 switch-to-switch 实线更紧凑而缩小 switch box 到无法容纳内部虚线，也不要用抽象节点替代带内部虚线的 switch module box。
- switch 高度根据过滤后的 `(d)` 内部虚线数量动态调整；内部虚线越多，switch 越高，但不要因为未过滤的推断关系扩大 switch。
- 推荐默认视觉语义：Req switch 使用蓝色系，Resp switch 使用紫色系，master 使用绿色系，slave 使用粉色系；不要把颜色绑定到某个具体工程实例名。
- draw.io XML 图层顺序固定为：底层模块框 -> 连线 -> 文字标签，避免模块填充遮挡虚线或文字。
- draw.io cell 文本换行必须使用 XML 兼容写法，例如 `&#xa;`，避免 draw.io 导出后多行文字挤成一行。
- 不写死特定工程示例中的 master/slave/switch 名称；所有节点、端口和连接都从 `Req.md`、`Resp.md` 以及用户显式提供的集合推导。

### 步骤二输出检查

- 使用 `xmllint --noout` 检查 `.drawio`。
- 使用 `xmllint --noout` 检查 draw.io 导出的 `.svg`。
- 用 draw.io 从 `.drawio` 导出 `.png` 后进行视觉检查。
- 检查 `Req.md` / `Resp.md`：四个标题必须以 `## (a)`、`## (b)`、`## (c)`、`## (d)` 开头；表格必须包含固定 `Record` 列；连接符应统一为 `->`；evidence 不应出现自造箭头，也不应把 wire/signal 名串成主要路径。
- 视觉检查重点：switch 是 module box 而不是抽象符号、`(d)` 内部虚线画在 switch box 内部、实线贴边、switch-to-switch 线按 Req/Resp 方向分区且不交叉、port 标签逐个独立且贴边可读、内部虚线直连且方向清晰、SVG 与 PNG 来自同一个 `.drawio` 图源。
- 如果导出 PNG 后发现任意 flit port label 与其他 label、黑色实线、灰色虚线或模块边界重叠，或者 label 之间没有可见间隔、无法独立辨认，必须修改 `.drawio` 后重新导出，不能交付该图。
