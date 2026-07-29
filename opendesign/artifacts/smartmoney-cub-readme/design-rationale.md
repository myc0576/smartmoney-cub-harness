# Design Rationale — SmartMoney-Cub README Visuals

## 探索过程

用 OpenDesign wireframe 流程生成三个粗方向（见 `../../mockups/smartmoney-cub-readme-directions/directions.html`）：

- **A · Editorial Control Plane**：左文右图，纸张卡片 + 细线管线；
- **B · Evidence Loop**：居中环形闭环，图形抽象；
- **C · Open-Source Modular System**：模块插槽，强调外部接入。

## 选定方向：A（吸收 B、C 的局部）

**理由：**

1. **GitHub 首页识别度**：2:1 横幅中左文右图分区明确，缩到窄屏仍能先读到产品名与定位；B 的环形在横幅比例下挤压文字，缩略时环上小字先失读。
2. **定位准确性**：项目是"只读复盘与证据治理控制平面"，A 的编辑式证据卡片最贴合"研究工具"气质；C 会被误读为插件市场广告，将可选集成置于核心复盘之上，主次颠倒。
3. **中英双语排版**：A 的左栏为双语层级（EN 主标题 + 中文副行）提供了自然落位；B/C 都缺乏稳定的双语文本区。
4. **两图一致性**：A 的卡片-细线-编号语言可以直接延伸为 system-flow 的四区布局。
5. **非俗套**：无 K 线、无金币、无仪表盘；核心隐喻是"证据文档流经人工门禁"。

**融合**：hero 右侧采用 B 的闭环反馈线（EVOLVE → HUMAN GATE → INPUT）；system-flow 区域 2 采用 C 的外部插槽语言（虚线边界 + Optional · User-selected · External）。

**Claude-inspired 元素**（气质层面）：暖纸底色、人文 serif 展示字体、单一陶土色强调、大量留白、细线与克制阴影。

**SmartMoney-Cub 原创元素**：证据卡折角与哈希纹理、灰绿 HUMAN GATE 门禁符号、双语节点层级、READ_ONLY 契约条、01–10 编号管线。未使用任何 Anthropic/Claude 标志、字标、插画或页面布局。
