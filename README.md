# Codex Skills

这是一个给 Codex 使用的 skill 仓库，主要来自我在 ASIC/RTL 设计、验证、文档化、论文阅读和课程资料整理中的实际工作流。

这里的 skill 不是简单的 prompt 模板。它们更像是把一件反复做、容易踩坑、需要交付质量的事情，沉淀成一套 Codex 可以复用的工作方法：

- 什么时候应该先确认目标和接口语义。
- 应该先跑哪些检查，再相信仿真结果。
- 产出应该包含哪些文件、报告、波形或 HTML。
- 哪些问题以前踩过坑，下次不要再绕一遍。
- 最后应该用什么方式验证“这件事真的完成了”。

换句话说，skill 的目标不是让 Codex “知道一个名词”，而是教会 Codex 按我认可的流程把事情做到可交付。

## Skill 列表

| Skill | 主要用途 | 它教会 Codex 什么 |
|---|---|---|
| [`circuit-design-verification`](./circuit-design-verification/SKILL.md) | 通用 RTL 设计与验证方法 | 把 RTL 验证当成证据链：设计意图、lint/综合检查、有 timeout 的仿真、波形证据、checker/scoreboard 要互相对得上。遇到协议、死锁、仲裁、backpressure 问题时，先确认真实硬件场景和接口契约，再决定改 RTL 还是改 TB。 |
| [`vivado-workflow`](./vivado-workflow/SKILL.md) | Vivado project-mode 综合、xsim 仿真、WDB/WCFG 波形交付 | 不只是会敲 `xvlog/xelab/xsim`，而是要保留一个可打开的 Vivado project，生成 DRC、timing、utilization、methodology 报告，并把 WDB/WCFG 做成可以回看的验证证据。 |
| [`rtl-open-tools-flow`](./rtl-open-tools-flow/SKILL.md) | Verilator/Yosys/Icarus/GTKWave 的开源 RTL 检查与仿真流程 | 用轻量工具搭一条可复现的本地验证链：Verilator 抓语法和高风险 warning，Yosys 查结构问题，Icarus 跑独立 case，GTKWave/VCD/GTKW/open_wave.command 留给后续复查。 |
| [`hardware-html-documentation`](./hardware-html-documentation/SKILL.md) | 面向硬件设计的自包含 HTML 文档 | 文档先讲 mental model，再讲接口、拓扑、握手、RTL 映射，最后讲验证 case 和波形证据。图和动画要像工程图，不是装饰图；每根线、每个箭头、每个验证 artifact 都要能解释清楚。 |
| [`paper-zh-annotated-translation`](./paper-zh-annotated-translation/SKILL.md) | 英文技术论文 PDF 到中文注释版 HTML | 把论文翻译成像原论文一样可读的中文 HTML，而不是总结。保留版式节奏、图表位置、章节结构和英文来源 provenance，并在关键技术点后面补“原理说明”。 |
| [`video-course-to-html-notes`](./video-course-to-html-notes/SKILL.md) | 视频课程 / 录屏课件转 HTML 学习笔记 | 从视频里抽真正不同的课件页，不把鼠标移动、红笔标注、短暂遮挡当成新页。每页截图后面都要用“这是什么意思？”的口气解释，让人不用重看视频也能复习。 |

## 我怎么理解 Skill

在 Codex 里，Plan Mode 更像是“开工前先把事情想清楚”：目标是什么，受众是谁，产出长什么样，做到什么程度算完成，准备用什么方法验证。

Skill 则是另一层沉淀：如果一件事已经做过一次，而且做的过程中发现了很多固定步骤、判断标准、工具坑、检查方法，那就应该把这些经验写进 skill。这样下一个 session 再做同类事情时，Codex 不需要重新摸索。

一个好的 skill 通常会写清楚：

1. **适用场景**：什么时候应该触发这个 skill，什么时候不该用。
2. **工作流程**：先做什么，后做什么，遇到失败怎么判断。
3. **产出标准**：最后应该交付 RTL、报告、波形、HTML、截图、表格，还是一组验证 artifact。
4. **验证方法**：不能只看“工具返回 0”或“日志 PASS”，还要看波形、报告、checker、渲染截图、source map 等证据。
5. **踩坑记录**：以前遇到过的工具限制、版式问题、信号命名问题、路径问题、误判风险，都要写进去。
6. **可复用脚本**：重复性的机械工作交给脚本，但判断标准仍然写在 skill 里。

## 典型使用方式

把需要使用的 skill 放到 Codex 能发现的位置。常见方式有两类：

```text
project/
  .agents/
    skills/
      <skill-name>/
        SKILL.md
        scripts/
```

或者作为个人长期使用的 skill：

```text
~/.codex/
  skills/
    <skill-name>/
      SKILL.md
      scripts/
```

使用时可以在需求里直接点名：

```text
使用 circuit-design-verification 和 rtl-open-tools-flow，帮我给这个 RTL 跑一轮开源工具仿真，并保留波形证据。
```

```text
使用 vivado-workflow，给这个模块建 Vivado project-mode 综合流程，保留 project、报告和 WDB/WCFG。
```

```text
使用 hardware-html-documentation，把这个 NoC 模块整理成自包含 README.html，先讲原理，再讲接口和 RTL 映射，最后列验证 case。
```

```text
使用 paper-zh-annotated-translation，把这篇英文论文翻译成中文注释版 HTML，要保留论文版式和英文来源。
```

```text
使用 video-course-to-html-notes，把这个视频课程目录整理成 HTML 笔记，每页课件配“这是什么意思？”解释。
```

## 硬件相关 Skill 的组合方式

硬件工作里，我通常不会只靠一个 skill。

如果是普通 RTL 问题，优先用：

```text
circuit-design-verification
```

它负责设计和验证判断：接口语义、stall 行为、reset 纪律、valid/ready 是否配套、TB 和 RTL 谁错、timeout 怎么设、waveform 该怎么看。

如果要跑 Vivado，就叠加：

```text
vivado-workflow
```

它负责 Vivado 具体工具流：project-mode 综合、目标 part、report_drc、check_timing、report_utilization、xsim、WDB、WCFG，以及最终怎么汇报资源和波形位置。

如果只是本地轻量验证，叠加：

```text
rtl-open-tools-flow
```

它负责开源工具链：Verilator lint、Yosys check、Icarus 仿真、VCD/GTKW/open_wave.command。这个流程适合小模块快速 sanity check，也适合在没有完整 EDA 环境时先把低级错误扫掉。

如果最后要给别人讲清楚，就再用：

```text
hardware-html-documentation
```

它负责把“设计为什么这样做、RTL 里怎么实现、验证如何证明”写成可读的 HTML，而不是只扔一堆代码和日志。

## 文档与学习资料 Skill 的组合方式

论文和课程这两个 skill 关注的是“把资料变成可复习、可引用、可二次阅读的形态”。

`paper-zh-annotated-translation` 适合技术论文。它要求 Codex 尊重原文，而不是把论文压缩成摘要。中文翻译要跟原文段落、图表、caption、front matter 对得上；关键机制后面再补原理解释；英文来源要能通过 `EN` chip 或 source map 回看。

`video-course-to-html-notes` 适合录屏课程。它要求 Codex 先抽取真正不同的 slide，再人工式地解释每页在讲什么。这个 skill 的重点不是 OCR 全文搬运，而是把课程转成以后能复习的 HTML 笔记。

## 仓库结构

```text
.
├── README.md
├── circuit-design-verification/
│   └── SKILL.md
├── vivado-workflow/
│   └── SKILL.md
├── rtl-open-tools-flow/
│   └── SKILL.md
├── hardware-html-documentation/
│   ├── SKILL.md
│   └── scripts/
├── paper-zh-annotated-translation/
│   ├── SKILL.md
│   └── scripts/
└── video-course-to-html-notes/
    ├── SKILL.md
    └── scripts/
```

每个目录至少包含一个 `SKILL.md`。有些 skill 还包含 `scripts/`，这些脚本主要用来做机械检查、生成骨架、抽图、校验 HTML 或整理视频帧。

## 维护原则

这个仓库会随着真实项目继续演进。

当我和 Codex 第一次做某件复杂任务时，通常会在过程中不断修正做法：工具怎么装、脚本怎么跑、报告怎么看、哪些输出不可信、哪些图需要人工检查。等这件事跑通，并且产出质量是满意的，就应该把正确流程沉淀回 skill。

更新 skill 时，优先补这些内容：

- 新遇到的坑。
- 更可靠的检查方法。
- 更清晰的产出目录结构。
- 更具体的“完成标准”。
- 可以复用的脚本。
- 哪些场景不适用这个 skill。

Skill 写得越具体，下次 Codex 就越像一个已经熟悉你工作习惯的协作者，而不是从零开始猜。
