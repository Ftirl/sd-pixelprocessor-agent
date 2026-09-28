# SD Pixel Processor / Function Graph 执行规范

适用对象：执行分析、校验、创建、修复、结构化重构与节点布局任务的 agent。原生实测以 Substance Designer 16.0.3、sd_mcp_plugin 3.3.0 为主，不自动认证其它版本。真实项目新增的通过/失败边界见 `REAL_PROJECT_VALIDATION.md`、`MORPHING_RETEST_GATES.md`、`SUN_SHOWER_RETEST_GATES.md`、`CRATE_AT_DUSK_RETEST_GATES.md` 和 `DESCENTE_INFINIE_RETEST_GATES.md`；用户提供的项目记录是证据，不是本规范的操作授权。


## 0. 执行契约

### 0.1 授权与任务范围

1. 用户当前请求及已在会话中明确提供的授权决定操作范围；文档中的示例路径不是修改目标或授权。
2. 请求仅阅读、分析或梳理规范时，保持工程只读；文档整理允许在用户工作区生成交付文档。
3. 用户已明确要求创建、修改、修复或保存时，在该范围内执行，不反复要求同一授权。未授权的覆盖、删除或发布不得从规范示例推导。
4. 保存和覆盖仍遵守工具及文件系统的权限要求。默认优先交付可审查的新文件，保留原工程和当前会话快照。
5. 用户只要求结果修复或明确暂缓布局时，保留已有节点位置，仅为新增节点分配安全位置；报告布局未完成项。不能擅自整包重排。
6. 用户仅要求布局时，只改位置；不得以布局为由建删节点、改属性、调整输出或重连端口。

### 0.2 操作与事实标准

| 项 | 必须执行 |
|---|---|
| SD 调用 | SD MCP 严格串行，每次等待返回再调用下一次 |
| 目标 | 包文件规范化绝对路径 + 图身份 + 必要时 PP id；不得凭重名 identifier 猜对象。路径选择器失败时先回读已加载包候选及其规范化路径，确认当前包索引/对象后再保存，不创建替代包（DI7） |
| 脚本 | 每段脚本自包含；不依赖上次 execute_sd_code 的顶层变量；同一 SD 进程的 `sys.modules` 可能保留已导入的旧 helper，分阶段重跑时仅刷新本次自有模块 |
| 证据 | 判断附完整图身份、节点 id 或计数；读取失败或未执行不能判 PASS |
| 当前状态 | 回读当前会话；记录磁盘文件与未保存修改的差异 |
| 命名 | 字符串逐字符匹配，含大小写、$、# 和标点 |
| 预期差异 | 指定位置不存在用户描述的结构时如实报告；另有实际位置才指出，不凭空补齐 |
| 完成 | 逻辑、布局、原生渲染和跨引擎一致性分别报告，不相互代替 |

遇到目标不唯一、定义未知、端口不明或证据不足：停止依赖该信息的操作，继续独立且已授权的工作，并报告缺失信息。

### 0.3 判定词

- **PASS**：当前目标在指定检查范围内有实际证据满足规则。
- **FAIL**：当前证据违反必需规则，或新布局不满足明确的交付约束。
- **WARN**：可读性/命名建议未满足、保守碰撞需要复核，或存在已说明的局部例外。
- **N/A**：任务范围内不适用，例如纯表达式图没有循环。
- **未验证**：适用但没有执行、无法读取或检查能力不足。不能用 N/A 隐藏。

报告允许检查项为 WARN，并不允许将适用的未验证项写为 PASS。

## 1. 索引与执行顺序

| 类别 | 编号 | 所在章节 |
|---|---|---|
| 硬性禁止 | N1–N28 | §3 |
| 逻辑、结构与布局检查 | I1–I41、I13b | §4 |
| 结构化重构规则 | A1–A12 | §4.5 |
| 标准作业流程 | SOP-0–SOP-9、SOP-0A、SOP-3A、SOP-5A、SOP-5B | §5 |
| 工具行为陷阱 | T1–T47 | §6 |
| 内建库函数台账（171 函数逐节点核对） | §11.12、`references/SD_LIBRARY_FUNCTIONS_v2.5.0.md`、`references/library_functions_v2.5.0.json` | 调用库函数前按需 |
| 图语义与移植 | 四通道、节点、循环、循环格式降级、While 连接规划、语句树连接方式（Set→Statement Sequence→局部值消费者→纯算子终端）、类型、源码函数边界 | §7 |
| 症状诊断 | D1–D35 | §8 |
| 交付报告 | 固定字段 | §9 |
| 布局执行规则 | L1–L16 | §10 |
| 版本限定的原生证据 | 实测表与局限 | §11 |

**流程选择**：

1. 判断环境模式与用户授权，精确定位目标（SOP-1）。迁移/建图任务若依赖未在当前会话验证的引擎行为，先执行 SOP-0A 能力探针。
2. 分析：SOP-2 → SOP-3 / SOP-4 / SOP-5 → SOP-5A（适用时）→ 适用 I 检查 → §9 报告。
3. 创建或修复：先记录快照与诊断 → 源码结构分类 → **循环格式台账与 While 连接规划（SOP-3A，源码含循环时必做，按 §7.9.10 模板填写）** → SOP-5A Architecture Pass → SOP-6 / SOP-7 → 适用逻辑与结构检查（含 I32–I36）→ SOP-8 预布局反馈门 → 最终布局 → SOP-9 → 保存与回读。
4. 布局：先执行 Architecture Gate；未触发结构重构时才进入快照与逻辑指纹 → §10 生成布局计划 → SOP-8 应用与验收 → 保存与回读。

Architecture Pass 先于最终布局。布局任务无需同时做无关的数值重构，但若用户要求交付可维护的大图，而当前图触发 A1 且存在安全拆分点，不能用纯位置调整掩盖结构问题。纯布局且用户明确禁止逻辑重构时，只报告结构 WARN/FAIL 候选，不越权修改。文档整理任务不调用 SD 写操作。

## 2. 环境与工具选择

### 2.1 环境模式

工程任务报告第一行写 `环境模式：A / B / C`，并说明执行能力。

| 模式 | 判定 | 交付与验证 |
|---|---|---|
| A 在线 | 有可调用的 SD MCP 且连接有效 | 回读/修改 SD；实际执行的检查可判 PASS |
| B 离线可运行脚本 | 无可用 SD MCP，但用户能在 SD 执行脚本 | 交付自包含 Python、构建/布局计划及自检；未在 SD 执行的项标未验证 |
| C 离线不可运行 | 无可用 SD MCP，且无法在 SD 执行 | 交付可读 IR 与脚本，工程结果全部未验证 |

工具名字存在但连接失败，不能声称当前具有在线验证能力。用户运行并提供的日志作为用户回报证据，注明来源。
离线可以验证 Python 语法、静态数据或 XML 可解析性；必须说明这些不等于 SD 编译、渲染或包可打开验证。

### 2.2 工具矩阵

| 任务 | 首选 | 约束 |
|---|---|---|
| 包、图、函数资源定位 | execute_sd_code + getChildrenResources(True) | 精确包路径；递归查资源；图不唯一则停 |
| PP 内部图读取 | execute_sd_code | 由 PP.perpixel 取 property graph |
| 函数图读取 | execute_sd_code | 不依赖 get_graph_info 对函数的解析 |
| 复合图浅层核对 | get_graph_info | 仅在目标已确认无歧义时；显式 node_limit |
| 定义校验 | list_node_definitions；SD 中 graph.getNodeDefinitions() | 新建前确认定义存在 |
| 节点与连线 | MCP 结构化工具或 SD API | 库/函数实例先查真实端口；内部函数图使用 API |
| 位置修改 | move_node 或 node.setPosition(float2(x,y)) | 不使用 arrange_nodes；只改授权图 |
| 保存 | save_package 或包管理器保存 API | 精确包对象/包路径；遵守授权和权限 |

离线不得直接手写 `.sbs` 交付。可以只读解析现有 XML，但创建与修改 `.sbs` 必须由 SD 自己保存；XML 语法正确不足以证明 UID、连接、类型和资源引用合法。

### 2.3 运行时安全与版本门控

1. 原生 Probe 必须使用本次运行独占的 `newUserPackage()`；禁止枚举未保存包后“挑一个复用/清空”。清理只能针对本次明确登记的图对象。
2. Probe 输出必须写入本次运行独占目录；禁止清空固定目录或删除未知来源文件。
3. 内建 Functions 只允许从 Adobe 精确的 `resources/packages/functions.sbs` 解析；用户包同名 Function 不能成为候选。0 个或多个命中都应 fail closed。
4. 版本敏感的“实测语义”按 `references/COMPATIBILITY_MATRIX_v2.5.0.md` 管理。内置 native cook 基线是 16.0.3；16.0.5 与未知版本在同版本 Probe 通过前均为 `RUNTIME_REPROBE_REQUIRED`。不得把 16.0.3 的实测写成 16.0.5 PASS。
5. 同版本 Probe 完成后，用 `scripts/verify_probe_report.py` 验证完整性、版本一致性与匹配距离；验证失败仍是“未验证”。
6. 发布包必须通过 `python scripts/eval_release.py`。该门包含静态规范检查、Python 编译、Manifest 完整性和 behavioral safety eval。


## 3. 硬性禁止（N）

| ID | 禁止 | 替代执行方式 |
|---|---|---|
| N1 | 并发 SD MCP 调用 | 严格串行；仅独立的非 SD 读取可并行 |
| N2 | 调用 arrange_nodes | move_node / setPosition；历史环境记录其破坏连线 |
| N3 | 未验证 definition_id 就 newNode | **每次**创建前断言该 id 属于**目标图对象**的 `getNodeDefinitions()`，不能以另一图类型或一次会话检查替代。Sun shower 16.0.3 回测中在 compositing 图创建 `sbs::function::*` 返回空 MCP 结果；之后只读回查该图与阶段标记，不能盲重试。见 `SUN_SHOWER_RETEST_GATES.md` |
| N4 | 假设实例输出固定为 unique_filter_output | 查 getProperties(Output)；多输出必须明确选端口 |
| N5 | 未经用户授权改图、删资源、写工程 | 按 §0.1 确定权限；已有授权不重复索取 |
| N6 | 用 graph_identifier 猜重名图或函数图 | 精确包路径、资源/图身份、PP id |
| N7 | 手写/编辑 .sbs XML 作为创建或修复交付 | SD 内 Python → SD 保存 |
| N8 | 将未执行的离线工程产出称已测试 | 区分语法检查和 SD 检查，列未验证项 |
| N9 | 新节点不设位置、只留下(0,0)堆叠 | 每个原子/实例节点创建即有初始坐标；交付前布局验收 |
| N10 | 为布局复制、删除、改类型、改属性或重连节点 | 布局只改 Position；用 I20 指纹核对 |
| N11 | 直接将旧 sd_layout.py 的结果视作本版合规 | 按 §10 实现/审查布局器并执行 SOP-8 |
| N12 | 以保守矩形候选数宣称参考发生真实视觉重叠 | 分开记录保守筛查、实测包围盒与 UI 复核 |
| N13 | 已触发 A1 且存在已确认安全拆分点时，仍把单体大图仅靠扩大 X/Y 布局作为创建/修复最终交付 | 先执行 SOP-5A；完成函数化/模块化或记录 STRUCTURAL_EXCEPTION |
| N14 | Function Graph 抽取时先删除原区域、再尝试重建 | 先快照与候选 IR；新函数和首个实例验证成功后再逐步替换，最后删除被替代节点 |
| N15 | 源码已有清晰函数边界时，无评估地全部 inline 到单个 PP / Function Graph | 按 §7.7 先评估保留为 Function Graph；仅因 API/语义限制不能安全映射时才 inline 并记录原因 |
| N16 | 把一个超大 PP 包进一个近似同规模的单一 Function Graph 就宣称“已拆分” | Architecture Pass 递归检查新函数；仅形成真实语义边界和复杂度下降才算完成 |
| N17 | 为追求紧凑、短连线或视觉对称而打散源码/IR的语句树，将不同语句的私有表达式交错排布 | 最终布局必须保持“Sequence 纵向主干 + 语句表达式树”结构；共享 DAG 只作为明确例外处理 |
| N18 | 未征询布局/结构偏好，就把具有赋值或顺序语句的命令式源码直接降级成无 Set/Sequence 的匿名纯 DAG | 先建立源码 statement IR 并按 L1 向用户确认 A 结构保真 / B DAG 优先；无选择时不做风格相关写入。A 下赋值与状态走 Set/Sequence，纯表达式函数仍可 DAG。用户明确选 B 且接受结构不保真时，**仅无循环的直线计算**可记录 `USER_SELECTED_DAG`，数值验收但 I26 结构保真不判 PASS；有状态/动态循环须另行协商，不能仅凭选 B 静默取消 While/Sequence。已证明引擎阻塞的例外另记 `STRUCTURAL_FALLBACK` |
| N19 | 创建局部 Set 后仅依赖同名 Get 读取，却不给该 Set 真实连线消费者、Sequence 执行位置或输出可达路径 | Set 必须进入真实可达执行链；同名 Get 不是活性证明。构建后检查 Set 消费者/Sequence 归属 |
| N20 | `mul`/`mulscalar` 选择或端口绑定错误：float1×float1 用 `mulscalar`、向量×标量用 `mul`、`mul` 接不同维操作数、`mulscalar` 顺序颠倒（向量没放 `a`/Vector 或标量没放 `scalar`/Scale）、把 `A`/`B`/`Vector`/`Scale` 标签当端口 id、或凭端口类型读回/节点定义默认值判定操作数维度 | 按 §7.5.1：float1×float1 与同维向量 → `mul(a,b)`；floatN×float1（N≥2）→ `mulscalar(a=向量/Vector, scalar=标量/Scale)`（**顺序不可交换**）；维度必须回溯到真正决定维度的节点或源码 IR，并在创建前产出乘法节点选择表（I40） |
| N21 | 将某次环境中的 While 失败探针外推为“Pixel Processor 逐像素状态不可用”或默认禁止 While | Adobe 官方明确支持 Function Graph While，并将 Pixel Processor 列为主要使用场景；先按 §7.3–§7.4 的官方语义建模。只有当前任务出现异常或依赖未文档化边界时才用 SOP-0A 探针 |
| N22 | 构建器在节点集合尚未创建完整时提前执行统一连线，或交付前未断言最终输出实际有源连接 | 先完成节点/实例声明与登记，再统一 wire；最后回读每个输出的源连接和关键实例端口 |
| N23 | `Set x = expr` 之后的后续语句仍沿用 `expr` / Set 前上游节点的跨行数据线代表变量 x | Set 是变量版本边界；后续语句读取 x 必须创建正确类型的 `Get("x")`。只有同一条赋值语句内部允许直接使用其 RHS 表达式连线 |
| N24 | 源码中的任何循环格式（`for`、`while`、`do-while`、`for(;;)`、嵌套循环、`break`/`continue` 循环、宏/模板展开循环）被保留成"类 for"结构、被纯 DAG 链模拟、或被静默 unroll | 一律按 §7.9.2 降级为结构化 While，并按 §7.9.3 完成连接规划；unroll 只能在 §7.9.8 的显式例外下执行，且必须记录 `LOOP_UNROLL_EXCEPTION:<reason>` |
| N25 | While 建立时不做连接规划：`init`/`cond`/`loop` 未断言实际源连接、`cond` 未取反为退出条件、`__constant__` 留空，或在不满足 W7 例外时写 `-1`、端口 id/类型凭定义默认值推断，或 `cond`/`loop` 闭包与其它分支共享节点实例 | 按 §7.9.3 先规划再连线，交付前回读断言三输入有源、cond 为 bool、默认上限为可解释有限值；若使用 `-1` 则必须满足 W7 例外并记录；分支闭包按 W4 私有化（I34/I35） |
| N26 | 用旧 RHS/Set 长连线或仅凭同名/上下位置的裸 Get 假冒 Statement 依赖 | `Set` 必须在同一条可达 Sequence 链的先执行 `In` 路径，下方同维 `Get(name)` 的消费者必须进入其后执行 `Last` 路径；Get 无 Sequence 输入口，须核对实际边/端口、作用域、类型及非零变化数值。先修缺失的后分支连线，不默默用旧 Set/RHS 跨带直连；Sequence-value 仅作获准且数值验证的例外（§7.10.1–§7.10.2/I37/RS2） |
| N27 | 数值函数语义凭习惯推断、或用错误供给源替代：把 GLSL `mod` 当 C `fmod`（或反之）、用原子 `mod` 顶替库函数 `fmod`、假定 `round` 为"远离零取整"、把 `sign(0)` 当 0、把 `frac` 当 `fmod(x,1)`、未查两个供给源就断言"SD 没有 round/frac/trunc/clamp/sign/step/smoothstep"、或不经库函数而手搓已有实现 | 按 §7.5.3 与分支文件 `references/SD_BUILTIN_FUNCTIONS_v2.5.0.md` 查表：先判定源码语义类别（floor 基/截断基/半整数约定），再选"原子 / 库函数实例 / 显式构造"，并在创建前产出**数值语义选择表**（I41）；凡"SD 不支持 X"的结论必须两源都已查证（D35） |
| N28 | 库函数信息凭记忆或单一来源推断：不查台账就按印象接线（形参名/端口/默认值）、把发行包 XML 当唯一权威（可能含陈旧连接）、把 `str(SDValue)` 的 6 位小数当精确值、跨源比对用精确坐标、或声称"库函数内部实现未知"而不查已有的逐节点核对结果 | 库函数一律以 `references/SD_LIBRARY_FUNCTIONS_v2.5.0.md`（人类台账）/ `library_functions_v2.5.0.json`（机器可读）为权威；临时查单个函数用 `scripts/lookup_sd_function.py`；台账未覆盖的版本或包用 `scripts/dump_library_functions.py` + `verify_library_functions.py` 重新生成并差分后再用（T47/§11.12） |

## 4. 检查项（I）

### 4.1 作用域与函数

| ID | 检查规则 | 判定依据 |
|---|---|---|
| I1 | 非图输出的 Get 必须有消费者 | 无消费者且不是 getOutputNodes 成员 → FAIL；直接输出的 Get 有效 |
| I2 | Get 名字可解析，类型与来源明确 | PP 来源=可见局部 Set、父图参数、真实 PP 具名端口、已核实内建；函数来源=可见局部 Set、形参、已核实内建。未知 $ 标未验证；不存在的 # 端口 FAIL |
| I3 | 同作用域重复 Set 必须检查覆盖与顺序 | 未说明重复覆盖 → FAIL；明确需要的顺序重赋值记录例外并检查 I19；不把合法赋值误称引擎禁止 |
| I4 | 新形参及局部名统一 camelCase | 风格不统一 → WARN；纯布局任务不改名；暴露参数可统一 PascalCase；状态量推荐 s. 前缀 |
| I9 | 函数接口直接读取 | Input 为形参、getOutputNodes 为返回节点；历史基线 Output 属性为空，非空须核查并报告差异 |
| I10 | 每个形参有实际 Get 读取 | 完全未读取 → FAIL；有 Get 仍须检查 I1/可达性，不能仅据存在认定有效使用 |
| I11 | 自定义函数实例接口与被调函数接口一致 | 逐端口核对 id、类型、必要输入与连接；不假设 input1/input2 |
| I12 | 函数库无未知用途的孤立调用根 | 完整授权扫描范围无调用者 → WARN；公开入口或包外调用用途明确可记录例外；未扫描范围标未验证 |

I2 的名字集合检查只是初筛，不能证明 Set 在读取前执行；最终作用域与求值顺序由 I6、I7、I19 检查。
$ 和 # 是分类线索，不是名字存在的证据。函数不得默认直接读取调用方 comp graph 的暴露参数。

### 4.2 循环

| ID | 检查规则 | 判定依据 |
|---|---|---|
| I5 | init、cond、loop 均完整连接 | init/loop 为合法单语句或 Sequence；cond 最终返回 bool；必要输入缺失 → FAIL |
| I6 | 循环内外变量状态通过作用域与执行顺序正确传递 | While 内 Set 更新的状态离环后优先走显式返回/纯值路径；只有当前作用域已验证时才用同类型 Get 读取，但必须由 Sequence/数据依赖证明 While 已完整执行在前；禁止把 Exit Cond/Loop Body 内部节点本身直接跨分支复用。只存在同名 Set/Get 而无顺序证明 → FAIL |
| I7 | 循环携带量有明确初值 | 自引用量、跨轮依赖量、cond 读取的循环自身状态必须初始化；每轮先写后读的临时量、外部只读形参/参数无需重复 init |
| I8 | 循环结果出口与状态读取方式正确 | While 直接输出只用于“最后一次 Body 返回值”；持久状态在 While 完成后优先通过显式返回/纯值路径读取；裸 Get 需要当前作用域验证。多状态不因出环而强制打包；若使用向量打包必须有实际接口/调试理由。Body 内部节点跨分支输出 → FAIL |
| I15 | cond 是退出条件 | True 停止、False 进入 loop；移植 C/GLSL 继续条件时必须取反；核对零轮/一轮/预期轮数与上限 |
| I32 | 源码循环台账完整 | 每个源码循环（含嵌套、宏/模板展开、`do-while`、`for(;;)`）在台账中有唯一条目：格式、继续/退出条件、携带状态、每轮临时量、break/continue 目标、预计轮数、上限来源、映射结果。缺条目或映射未定 → FAIL；源码未扫描 → 未验证 |
| I33 | 循环格式降级正确 | `cond` 已取反为退出条件；`do-while` 保留"至少执行一轮"；`break` 之后的语句被条件包装不再执行；`for` 中的 `continue` 仍执行增量；嵌套 `break`/`continue` 只影响最内层；非 1 步长/递减/浮点计数方向正确。任一项错误 → FAIL |
| I34 | While 连接规划完整 | `init`/`cond`/`loop` 三个输入各有**实际源连接**；`cond` 末端类型为 bool 且语义为退出条件；`__constant__` 默认是可解释的有限上限；若为 `-1`，必须满足 W7 的“可证明退出界 / 用户明确要求”例外并记录风险；端口 id 与实例类型来自回读。端口存在但无实连、或按定义默认类型推断实例类型 → FAIL（对应 N25/§7.9.3） |
| I35 | While 分支闭包隔离 | `cond`/`loop` 闭包内节点未同时连接另一分支或环外；环外循环状态优先走显式返回/纯值路径；若用 Get 必须另有当前作用域验证。跨分支共享节点或跨接 Body 内部节点 → FAIL（对应 W4/W5/D25） |
| I36 | While 连接模板一致性 | 新建/修复的 While 默认按 §7.9.10 形态实现：Init 只放初值、cond 只读不写且不与 loop 共用 Get 实例、tail Get 是独立新建节点、常量按语句/分支私有、init/cond/loop 三个子区域齐全且几何未被压平。未按模板且未记录偏离理由 → FAIL；模板前置（最终输出节点、无悬空 Get、PP 已接线）未满足 → FAIL |

简单 I7 初筛集合=`loop Set 自引用量 ∪ cond读取的循环自身状态`；这是下限，不是复杂循环的完整分析。
例如 `x=y; y=x+1` 中 x 虽不直接读自己，仍可能依赖上一轮 y。嵌套循环、间接反馈、条件写入及先读后写必须进行逐语句数据流分析；做不到则标未验证，不能给整体 I7 PASS。

I32–I36 检查的是**循环降级、连接规划与模板一致性**，不是数值等价：即使渲染结果看似正确，只要源码循环被错误格式模拟、被静默 unroll（无 §7.9.8 例外记录）、While 三输入实际未接上、或未按 §7.9.10 模板实现而无偏离记录，仍判 FAIL。源码移植任务在建图前必须先完成 SOP-3A 的台账与连接规划表。

### 4.3 数值与移植

| ID | 检查规则 | 判定依据 |
|---|---|---|
| I14 | `mulscalar` 类型严格正确 | `a` 必须为 float2/3/4，`scalar` 必须为 float1；float1×float1 使用 `mul`。沿真实连线传播检查；仅凭节点定义默认类型不能 PASS |
| I16 | 算术不隐含 GLSL 标量广播 | IR 产出 broadcast lowering table：`vecN ± scalar`、`vecN / scalar`、`min/max/pow/mod(vecN,scalar)` 及 `clamp(vecN,scalar,scalar)` 的标量显式扩成同维，再接普通二元节点；乘法按 §7.5.1/RS6 选择。`lerp.x` 是合法标量权重，不误报。连接成功仍混维 → FAIL |
| I40 | 乘法节点选择表与类型解析有据 | 逐一列出图中每处乘法/归约：操作数维度、**判定依据链**（回溯到 `get_floatN`/`const_floatN`/函数形参/PP `#` 端口/swizzle 输出/`dot` 等确定维度来源；16.0.3 原子定义中无 `length`）、所选 definition 与端口绑定。`mul` 接不同维操作数、向量×标量用 `mul`、`mulscalar` 顺序颠倒（向量接 `scalar`/标量接 `a`）、float1×float1 用 `mulscalar` → FAIL；维度仅凭端口类型读回或定义默认值判定而未回溯 → 未验证；连线/设参使用 `A`/`B`/`Vector`/`Scale` 等标签而非小写 id → FAIL（§7.5.1） |
| I41 | 数值语义选择表有据（两源已查） | 逐一列出源码里出现语义歧义的数值函数（`mod`/`fmod`/`round`/`frac`/`trunc`/`sign`/`clamp`/`saturate`/`step`/`smoothstep` 及任何"工具同名不同义"者）：语义类别、判定依据、所选供给（原子 / 库函数实例 / 显式构造）、端口绑定、与源码差异。用原子 `mod` 顶替 `fmod`、`round` 未对照半整数约定、`sign(0)` 未按官方=1 处理、`frac` 当 `fmod(x,1)`、手搓已有且**当前会话可达**的库函数却未说明差异 → FAIL；库资源不可达时可记录 `LIBRARY_INSTANCE_UNREACHABLE`、显式构造与独立数值等价证据。断言"SD 无某函数"却只查了一个供给源 → FAIL（§7.5.3/N27/D35） |
| I42 | 向量构造槽位 | 每个 `vec2/3/4`、`ivecN`、swizzle 构造先列源分量顺序与端口映射；`vectorN.componentsin` 为前 N−1 个有序分量，`componentslast` 为末分量。实际连接与 IR 不同 → FAIL；向量 oracle 含可区分各分量的非对称值（§7.5.2） |
| I43 | Get 声明维度一致 | 每个 `get_floatN` 的 N 必须匹配**当前作用域**同名 formal/Set/已验证系统变量的声明维度，名称未声明或维度不同 → FAIL；名字正确但只凭多态端口读回 → 未验证。创建/逐函数 cook 前执行 `scripts/project_validation.py::check_get_dimensions`（§7.11） |
| I44 | 变换应用点完整 | 每个源码矩阵/旋转/坐标变换的所有应用点及被作用的量（位置、法线、软法线、光线、UV 等）在 IR 逐项映射；缺一个 → FAIL。每个应用点用非对称输入独立验证，不以 `T=0` 臆断为单位阵（§7.5.2） |
| I17 | atan2、旋转、取整约定与源代码一致 | 按 §7.5.2 的**官方语义**处理角度：SD 只有 `atan2`（无单参 `atan`），输入是 float2 向量（id `a`，标签 `Vector`），返回该向量与水平方向的夹角弧度，**不需要像通常 atan2 那样交换 x/y**；源码 `atan2(垂直, 水平)` 应组装为 `vector2(componentsin=水平, componentslast=垂直)`。同时明确矩阵行列乘法与旋转方向；半整数 round、负数 mod/fract 不凭习惯推断 |
| I18 | 坐标与分辨率正确 | 核对 $pos/$size 实际值、宽高比、Y方向、$outputsize继承及真实纹理尺寸；$pixelsize不得当像素数量 |
| I19 | 有副作用的求值顺序与中间值复用正确 | Set前后读取的变量版本明确；合成表达式不能因同名Set后再次读取而重复执行尘埃、曝光等计算 |

不能只因“图可编译/有图像”而判数值语义正确；不得仅根据端口定义的默认类型推断所有多态算术的实际维度。

### 4.4 布局

| ID | 检查规则 | 判定依据 |
|---|---|---|
| I13 | 位置分配完整，碰撞结果分类清楚 | 新布局须做到计划占位矩形重叠0；已测实际可见包围盒相交或同坐标堆叠 → FAIL；读取参考时仅保守矩形相交 → WARN候选，不等于真实重叠 |
| I13b | 阅读关系符合 L1–L13 | 以代码/IR为结构来源检查：Sequence 主干自上而下、每条语句的 Set/返回值为右侧根、表达式树向左展开、兄弟子树不交错、循环/分支保持结构边界、共享 DAG 例外明确。违反主干顺序、树方向或语句归属 → FAIL；仅紧凑性不足 → WARN |
| I20 | 布局保持逻辑指纹 | 布局前后节点、定义、资源引用、端口、连接、函数形参、输出与逻辑属性一致；只允许授权位置变化。差异 → FAIL，回滚本次位置修改并定位原因 |
| I37 | 语句树连接方式（禁止 Set/RHS 跨带直连） | 逐边统计 dy 并按 statement id 审计边：Set 接先执行 Sequence `In` 路径，下方本带 fresh typed Get 的消费者接同一可达链的后执行 `Last` 路径。回读端口、输出可达性、作用域/维度及非零变化数值；Sequence-value 只作获准且数值验证的例外。另有完整 Sequence 主干也不能放行 Set/RHS→下方普通算子。Get 名称与画布位置不证明执行；进入 While Body 的 Sequence 必须在 Body 内产生；无法逐边统计 → 未验证 |
| I38 | 跨度与节点预算按结构归一化 | 每图在 IR 标明 statement 或 expression 模式。Statement 图报告 `节点数`、语句带数、`nodes_per_statement`、`Y_per_statement`、`X_per_level` 与逐边 dy/dx；纯 Expression 函数（包括 A 方案下的纯函数）前两项结构比记 `N/A(expression)`，改看节点数、深度、每层宽度/扇出与 `X_per_level`，不自动补 Set/Sequence。节点 `≥400` 仍需 Architecture Pass；`1200–1500` 高节点复核并标 WARN，`>1500` 超出通常预算。Statement 的 `Y_per_statement ≤320` 且任一模式 `X_per_level ≤224` 为跨度 PASS；超出 WARN，`>512`/`>384` 无理由或安全拆分未处理 FAIL。用绝对跨度或压缩行距判错/造假通过 FAIL |
| I39 | 计划结构有效性与创建即落位是两个门 | 新建/移植任务：首次 `newNode` 前用 `validate_layout_plan` 逐图/逐嵌套块检查稳定 Sequence 共列、Set/Sequence 同行、树方向、行序与零同坐标；计划无效即 FAIL，不能靠"已按计划落位"放行。创建后用 `validate_position_application` 独立核对坐标；差异仅可由位置-only 几何校正解释（整子树/整语句带平移、计划版本更新记录）。先默认/临时落位、事后整体排布无 `POSTHOC_LAYOUT:<reason>` → WARN；校正改逻辑/连接/接口 → FAIL（I20）；校正后未复查 I13/I13b/I37/I38 → 未验证 |

同坐标检查不能替代矩形检查。普通节点默认计划占位128×96；真实尺寸未知须标为占位估计；多端口实例要扩大，Passthrough不得当成通用节点尺寸样本。
计划占位重叠0只证明计划筛查通过，不能声称所有真实节点在 UI 中不重叠。

### 4.5 结构化重构与大型图 Architecture Pass（A）

本节解决“图能排下”与“图应该保持单体”之间的区别。A1 阈值是 **Agent 交付与可维护性预算**，不是 Substance Designer 引擎限制，也不是对历史参考图的自动判错。结构化重构只有在用户已授权创建/修复/重构的范围内执行；纯读取或纯布局任务只做评估和报告。

| ID | 规则 | 必须执行 |
|---|---|---|
| A1 | 复杂度触发（结构归一化） | 图节点数 `>=400`；或 `节点数 >=192 且 nodes_per_statement > 16`；单一语义区域 `>=32` 个有效计算节点；同构/参数化同构子图重复 `>=2` 次且每份 `>=8` 个有效计算节点；或归一化跨度超标（`Y_per_statement > 320`、`X_per_level > 224`，§7.10.4）时，强制进入 Architecture Pass。节点数 `400–1199` 完成该 Pass 后**不因数量单独失败**，但 Pass 必须与 SOP-5A 的具体函数拆分候选/无安全候选理由联动；`1200–1500` 还须记录高节点复核（拆分决策、响应/回读、cook 与布局）并标 WARN；`>1500` 不作为通常新建单体图交付。`nodes_per_statement > 24` 或 `Y_per_statement > 512` / `X_per_level > 384` 且有安全抽取点时，仍须拆分或记录结构例外。**绝对跨度**（`spanY > 12000` 或 `spanX > 4800`）只触发视觉复核说明，不作为判错依据 |
| A2 | 候选类型 | 识别完全同构 DAG、参数化同构 DAG、单次但语义完整的大型纯计算区域、可复用基础数学/数据处理模块；不得只按 identifier、坐标或 label 判断 |
| A3 | 参数化重复 | 拓扑、definition id、端口和类型一致而常量不同的区域，不因常量差异放弃抽取；仅将不同调用点真正变化的常量提升为 Function Input |
| A4 | 可抽取性 | 默认优先纯计算 DAG。候选不得隐式读取调用方局部 Set、父 comp 参数或 PP #端口；跨边界数据必须成为明确 Function Input。含 Set/Sequence/While/ifelse 的区域仅在状态边界与执行顺序可完整封闭时抽取 |
| A5 | 接口最小化 | 只暴露真实跨边界数据；固定语义常量留在函数内；避免把大量调用方局部变量机械升级为参数。函数名使用语义名称，不用 function1/helper2 |
| A6 | 多输出 | 优先单结果。多结果先核实当前 Function Graph 的真实输出能力；不支持时，仅在类型兼容且无损的情况下允许向量打包。不能安全表达边界则保留原结构 |
| A7 | 递归拆分 | 新建 Function Graph 本身也执行 Architecture Pass。把 300 节点 PP 变成 250 节点 Function Graph 不等于完成；继续拆分直到结构比（§7.10.5）正常，或记录 `STRUCTURAL_EXCEPTION` / `FUNCTIONIZATION_BLOCKED` |
| A8 | 安全替换 | 原图快照 → 候选 IR → 新 Function Graph → Input/内部节点/返回 → 接口验证 → 首个实例 → 回读端口/连接 → 语义验证 → 其它调用点 → 删除被替代节点 → Final IR → 最终布局 |
| A9 | 源码边界优先 | 从 HLSL/GLSL/C-like 源码移植时，已有命名函数默认作为 Function Graph 候选；只有作用域、副作用、节点能力或接口限制使其不能安全映射时才 inline，并记录证据 |
| A10 | 循环体分析 + While 强制默认 | 固定次数 for/while 的 body 天然属于清晰语义区域：先按 A2/A3 评估 body 的 Function Graph 抽取，**不因"次数固定"而展开**。任何源码循环格式的映射目标都是结构化 While（§7.9.2）；只有 §7.9.8 的显式例外才允许 unroll，并必须记录 `LOOP_UNROLL_EXCEPTION:<reason>`、保持每轮 statement block，且不得声称已完全遵循 While 循环规范 |
| A11 | 预布局反馈回 Architecture Pass | Function 抽取后先生成不写 SD 的预布局统计，并对调用方和每张新函数分别回读实际节点数、重新执行 A1/SOP-5A；不能把超预算复杂度移入新函数。预估与实际差异须解释并更新候选投影。任一图触发 A1 的节点数/重复候选/归一化跨度条件时须完成评估，但完成后 `≥400` 本身不阻止 PASS。`1200–1500` 须完成与拆分决策对应的高节点复核并标 WARN；`>1500` 不作为通常新建单体交付。`Y_per_statement > 512`、`X_per_level > 384` 或跨带长连线未处理（I37）且无 `STRUCTURAL_EXCEPTION`/`SPAN_JUSTIFICATION` 时，不得宣称结构/布局最终 PASS |
| A12 | 先函数化后组装（新建/移植默认） | 新建或源码移植任务默认按 **SOP-5B**：先建源码函数表与接口 → 自底向上创建并逐个验证 Function Graph → 再在主图组装实例、语句结构与 While。把"先造完整单体大图、事后抽取"当作**新建任务的默认路径** → WARN（有明确理由可记 `POSTHOC_EXTRACTION:<reason>`），而 A8 的替换顺序只在**既有图修复/重构**时成立。组装阶段仍须满足 A1/A7/A11 的归一化预算、递归拆分与 I37/I38 |

**有效计算节点**：排除纯 Frame/注释；Passthrough是否计入由用途说明，但不能通过大量 Passthrough 人为规避阈值。Set/Sequence/While 属于结构复杂度，不能从节点预算中删除。

**结构比指标**：`nodes_per_statement = 节点数 / 语句带数`（语句带数=Set/语句根数，至少 1）、`Y_per_statement = spanY / 语句带数`、`X_per_level = spanX / 最大表达式深度`。它们比绝对节点数/绝对跨度更能反映可维护性，定义与阈值见 §7.10.4–§7.10.5，实测基线见 §11.7。

**数值来源**：A1 的节点数与归一化跨度数字取自 16.0.3 只读实测参考包 `OKColor_LCH.sbs`（1 张复合图 + 15 张 Function Graph、1058 节点、最大单图 368 节点/43 语句带、`nodes_per_statement` 典型 5.8–13.5、`Y_per_statement` 中位 230/p75 318、`X_per_level` 中位 ≈150、行步中位 224、列步中位 160）。该包属于可接受的语句树形态，故**绝对高度墙被归一化判据取代**。

**阈值制动**：小片段不得被过度函数化。重复区域 `<6` 个有效计算节点通常不抽；重复区域 `>=8` 默认进入候选；单次语义区域通常 `>=24–32` 节点才进入抽取候选。明确的基础数学 primitive、已有源码函数边界或用户指定接口可例外。`nodes_per_statement > 16` 通常意味着语句结构被展开成 DAG：优先补 Set/Sequence/Get 结构（§7.10）或抽取，而不是继续堆节点。

**循环例外**：固定循环的 body 不需要等待图构建后做同构发现；源码 IR 已经证明它是稳定语义区域。即使 body 单次节点数低于普通候选阈值，只要 body 较复杂或会被重复执行，也应评估单轮 Function Graph。循环默认保留结构化 While（§7.9）；是否进入 §7.9.8 的 unroll 例外不是默认路径，函数化不改变"外层是 While"的结论。

**跨度反馈（归一化）**：跨度判据以 `Y_per_statement`/`X_per_level` 为主（§7.10.4），Architecture Pass 前后按同一公式检查；绝对跨度只作报告标志。用"扩大画布/压缩行距/交错语句带"把归一化指标压进阈值但同时引入跨带长连线，属于伪造通过（I37/I38），不得判 PASS。

**节点数不是判错依据**：368 节点 / 43 语句带的语句树属可接受交付形态（§11.7）。节点数只有在**结构比异常**、存在已确认安全抽取点且用户已授权重构时才成为必须拆分的理由。

**结构检查项**：

| ID | 检查规则 | 判定依据 |
|---|---|---|
| I21 | Architecture Pass 触发判断完整 | 记录节点数、语句带数、`nodes_per_statement`、语义区域大小、重复候选、`Y_per_statement`/`X_per_level`；触发 A1 却未分析 → FAIL；纯读取无法完整分析 → 未验证 |
| I22 | Function 候选识别与参数化正确 | 至少比较 definition、端口、拓扑、类型、常量差异和资源引用；仅凭节点名/坐标判重复 → FAIL |
| I23 | Function 抽取后边界无隐式调用方依赖 | 所有跨边界输入显式化；函数内部未偷读调用方局部/父参数/#端口；无法证明 → 未验证或 FAIL |
| I24 | 结构重构语义等价 | 比较外部输入集合、最终输出、类型、运算/副作用顺序、常量精度、参数映射；在线时优先做同输入原生渲染对照。仅“函数创建成功”不能 PASS |
| I25 | 结构复杂度实际下降 | 报告拆分前后图数、各图节点数、最大图节点数、`nodes_per_statement`、`Y_per_statement`/`X_per_level`、跨带长连线数与接口数量；仅移动复杂度到一个超大函数或接口爆炸 → FAIL/WARN，并按 A7 继续 |
| I26 | 命令式源码结构保持 | 源码中的赋值、顺序语句、循环展开后的每轮语句块在 Final IR 中仍可一一追溯到 Set/Sequence/控制块；命令式源码被无说明地压成纯 DAG → FAIL。若用户明确选纯 DAG 且 `USER_SELECTED_DAG` 经无循环/结构取舍门通过，报告结构保真为有意偏离（WARN），不得判 PASS或伪称源码语句结构仍在 |
| I27 | Set 活性与执行锚点有效 | 每个有副作用 Set 至少满足：属于可达 Sequence、返回值有真实消费者、或自身为输出可达节点之一；只存在同名 Get 不算消费者 → FAIL |
| I28 | 构建完整性 | 所有节点/实例创建后均登记进 IR/表达式/布局表；统一连线发生在最后一个声明之后；最终输出有实际源连接；任一缺失 → FAIL |
| I29 | 依赖环境行为的能力证据充分 | `$pos/$size/$outputsize`、Function 实例、导出/回读及**官方未明确或当前出现异常的 While 边界行为**按任务验证；官方已明确的 While 基本语义不要求每次重新证明。把历史异常当通用规则 → FAIL |
| I30 | 树形几何可机器检查 | Statement 模式下逐条断言 `x(私有输入)<x(consumer/Set/语句根)<x(关联 Sequence)`，同块 Sequence 的 X 稳定、Y 按 IR 递增，关联根与 Sequence 同行；计划坐标与 SD 回读坐标分别执行。违反任一左右方向或主干顺序 → 布局 FAIL，即使数值与跨度 PASS |
| I31 | Set 后变量版本切断正确 | 对 `Set x = expr`，生产 Set 接先执行 Sequence `In` 路径，下方本带新建同维 `Get("x")` 的消费者接同一输出可达链的后执行 `Last` 路径；再以非零变化用例验证同作用域可见性。若失败先检查/修复连通性、端口、名称和维度；拓扑正确仍失败才阻断或请求 Sequence-value 例外。不得沿用旧 RHS/Set 输出跨语句；fresh Get 的存在本身不构成正确性证据。 |

I20 只用于**纯布局不变性**。Function Graph 抽取属于有意拓扑重构，不能因为节点/连接指纹改变而直接判 I20 FAIL；这类阶段改用 I24 的语义等价检查，并保存重构前后两个结构指纹用于追溯。

## 5. 标准作业流程（SOP）

下列代码是模板。涉及目标或写操作的模板必须填写参数并确认授权后执行；不因读取本文件自动运行。
每次调用将所需模板与 SOP-0 合并在同一脚本。检查代码的语法通过不等于 SD API 执行通过。

### SOP-0：自包含引导与通用读取

```python
import os
import sd
from sd.api.sdproperty import SDPropertyCategory as C

app = sd.getContext().getSDApplication()
pkg_mgr = app.getPackageMgr()

def normpath(path):
    return os.path.normcase(os.path.normpath(os.path.abspath(path)))

def defid(node):
    return node.getDefinition().getId().removeprefix('sbs::function::')

def sval(node, pid):
    prop = node.getPropertyFromId(pid, C.Input)
    if prop is None:
        raise RuntimeError('Missing property: %s.%s' % (node.getIdentifier(), pid))
    value = node.getPropertyValue(prop)
    return None if value is None else value.get()

def src(node, pid):
    prop = node.getPropertyFromId(pid, C.Input)
    if prop is None:
        raise RuntimeError('Missing port: %s.%s' % (node.getIdentifier(), pid))
    conns = list(node.getPropertyConnections(prop) or [])
    if len(conns) > 1:
        raise RuntimeError('Multiple sources require explicit handling: ' + pid)
    return conns[0].getInputPropertyNode() if conns else None

def refname(node):
    resource = node.getReferencedResource()
    return resource.getIdentifier() if resource is not None else None

def pp_graph(node):
    return node.getPropertyGraph(node.getPropertyFromId('perpixel', C.Input))

def upstream(node, seen=None):
    if seen is None:
        seen = set()
    if node is None or node.getIdentifier() in seen:
        return seen
    seen.add(node.getIdentifier())
    for prop in node.getProperties(C.Input):
        for conn in (node.getPropertyConnections(prop) or []):
            upstream(conn.getInputPropertyNode(), seen)
    return seen

def get_names(node):
    # Identifier 集合只在本图内使用；函数形参和名字不混入节点 id。
    names, seen = set(), set()
    def walk(n):
        if n is None or n.getIdentifier() in seen:
            return
        seen.add(n.getIdentifier())
        if defid(n).startswith('get_'):
            names.add(str(sval(n, '__constant__')))
            return
        for prop in n.getProperties(C.Input):
            for conn in (n.getPropertyConnections(prop) or []):
                walk(conn.getInputPropertyNode())
    walk(node)
    return names

def flatten(node, through_passthrough=False, stack=None):
    if node is None:
        return []
    stack = set() if stack is None else set(stack)
    nid = node.getIdentifier()
    if nid in stack:
        raise RuntimeError('Cyclic Sequence/input path: ' + nid)
    stack.add(nid)
    if defid(node) == 'sequence':
        return (flatten(src(node, 'seqin'), through_passthrough, stack)
                + flatten(src(node, 'seqlast'), through_passthrough, stack))
    if through_passthrough and defid(node) == 'passthrough':
        child = src(node, 'input')
        if child is not None:
            return flatten(child, True, stack)
    return [node]

def consumers_map(graph):
    result = {}
    for node in graph.getNodes():
        for prop in node.getProperties(C.Input):
            for conn in (node.getPropertyConnections(prop) or []):
                nid = conn.getInputPropertyNode().getIdentifier()
                result[nid] = result.get(nid, 0) + 1
    return result

def exact_value(value):
    # 保留 SD 常量真实分量，不用 float2 的六位显示文本作为精确数据。
    if value is None:
        return None
    raw = value.get()
    if hasattr(raw, 'x'):
        return [getattr(raw, a) for a in ('x', 'y', 'z', 'w') if hasattr(raw, a)]
    return raw

def D(node, depth=0, maxdepth=4):
    # 可读近似表达式；深度截断会显示 ...，不能当作完整代码证明。
    if node is None:
        return '?'
    if depth > maxdepth:
        return '...'
    kind = defid(node)
    if kind.startswith('get_'):
        return str(sval(node, '__constant__'))
    if kind.startswith('const_'):
        return kind + '(' + repr(exact_value(node.getPropertyValue(
            node.getPropertyFromId('__constant__', C.Input)))) + ')'
    args = []
    for prop in node.getProperties(C.Input):
        child = src(node, prop.getId())
        if child is not None:
            args.append(prop.getId() + '=' + D(child, depth + 1, maxdepth))
    return (refname(node) or kind) + '(' + ', '.join(args) + ')'
```

辅助函数不静默吞掉异常；外层捕获时打印目标、步骤与 traceback，将依赖该读取的项标未验证。
`refname` 仅取真实资源引用，不用节点 label 伪造调用关系。循环/函数完整还原应另建 IR，D 仅辅助展示。

### SOP-0A：迁移能力探针（按需）

**触发**：当前任务的正确实现依赖具体 SD 版本/插件环境行为，且当前会话尚无直接证据。§7.11 与 `REAL_PROJECT_VALIDATION.md` 可指导探针，但不能自动替代当前验证。

按最小原则创建临时/探针图，并在完成后清理或保存为明确诊断资源。只测试任务真正依赖的能力：

1. **渲染管线活性**：每一诊断轮先输出 `const_float4(1,0,0,1)`，执行 `graph.compute()` + 可用导出通道，确认产物确实为纯红；同时回读目标包的规范化绝对路径/资源身份，断连或卸载后先重新获取/显式加载，不从前缀匹配静默创建替代包。诊断脚本自身未验证前，不据它否定引擎。
2. **坐标与尺寸**：若使用 `$pos`，确认 PP 图像 `input` 有有效来源，并验证 `$pos` 梯度；若使用 `$size/$sizelog2`，同时核对 comp graph 与 PP 节点 `$outputsize` 的继承方式和真实尺寸。
3. **类型节点**：若使用 `mulscalar`，验证 `a` 为向量（标签 Vector）、`scalar` 为 float1（标签 Scale）；标量乘法与同维向量用 `mul`。**实测（§11.11）**：混维连线不会报错而是**静默返回 0**，因此探针要检查"结果是否为 0"而非"是否抛异常"。角度按 §7.5.2 官方语义处理（`atan2` 输入 float2 向量、不交换 x/y）；`swizzle`/其它多态节点按真实端口与最小输出探针验证。数值语义与循环边界按 **SOP-0B** 用原生 cook 取证。
4. **While 能力探针只用于异常/未文档化边界**：官方 While 语义本身不需要先证明“逐像素可用”。若当前图在遵守 Init/Exit Cond/Loop Body、Set/Get/Sequence 和分支隔离后仍异常，再建立最小复现；必须同时包含已知常量控制组和逐像素/采样组。失败只记录为当前环境/结构异常，不升级为通用禁令。
5. **Function Graph 逐像素能力**：若结构方案依赖 Function 实例处理逐像素值，建立 `FG(a)->vec4(a,a,a,1)` 或等价最小图确认实例路径。
6. **输出尺寸与导出**：需要固定尺寸时，对 comp graph 和 PP 节点都读取/设置 `$outputsize` 继承方法；导出后回读实际 W/H，而不是只相信 property 读回值。

探针结果记录：环境版本、目标临时资源、输入条件、实际输出、PASS/FAIL。相同会话中已验证的事实可复用，不重复建探针。

### SOP-0B：原生数值探针（真实 cook 取证）

**触发**：需要确定某函数的**数值语义/边界行为**（负数、半整数、零点、混维、循环迭代与零迭代），而文档只给描述或存在两种竞争语义；或改动后需证明语义未变。

**步骤**：

1. 用 `pkg_mgr.newUserPackage()` 建**未保存临时包**；不改动、不保存任何用户工程。
2. 每项探针一张独立合成图：`sbs::compositing::pixelprocessor` → `sbs::compositing::output`（输入 id `inputNodeOutput`）→ `graph.setOutputNode(out, True)`。
3. PP 内部图：`pp.newPropertyGraph(pp.getPropertyFromId('perpixel', Input), 'SDSBSFunctionGraph')`；结果节点用 `ig.setOutputNode(node, True)` 标记（T45）。
4. 结果先编码进**严格开区间 `(0,1)`**；可能为负的量用 `(v+A)/(2A)`（读回逆变换 `2A*enc-A`），不能用 `v/scale` 把负数截成 0。编码链只用已判定正确的节点（float1×float1 用 `mul`，禁止用 `mulscalar` 接 float1），避免用被测对象测被测对象。16.0.3 PP 内图以 float1/float4 作诊断根，float2/3 经 float4 或独立标量通道承载；预期值落在边界、溢出或非有限时不得拿饱和通道作为数值证据。
5. 为每项探针写出**两种竞争语义**的预期值（如 floor 基 vs 截断基、`x ≥ a` vs `x > a`）。
6. 先回读 PP 内图 `getOutputNodes()` 数量及根维度（16.0.3 实测 PP 的 float2/3 标记无效；未知版本先测），再 `graph.compute()` → `sd.tools.export.exportSDGraphOutputs(graph, 本次运行独占目录, 'bmp')` → 回读**实际** `graph.getIdentifier()`，按完整 `<actual_identifier>_output_` 前缀唯一匹配文件、核对 BMP 尺寸与行方向、解析像素；与全部候选取**最近者**并记录距离；距离不显著或文件不唯一时判"未验证"，不得猜。
7. 清理：删除全部本次运行创建的探针图，再**独立回读资源清单**；报告残留的未保存临时包数量。超时/中止后批内 delete 可能未持久化而探针创建仍留存，先回读再决定清理；分批 cook（本项目建议 ≤20/批，但不是平台保证），不要把批内 delete 响应当作最终清理证明。
8. 记录：环境版本、探针表达式、实测值、判定、局限（8bit 量化 ±1/255；未覆盖全域）。

现成实现：`scripts/probe_sd_semantics.py`（当前 24 项，含原有 22 项数值/循环基线与新增坐标/尺寸探针）；历史 22 项原生实测基线及新增项的未验证边界见 `references/NATIVE_PROBE_RESULTS_v2.5.0.md`。

### SOP-0C：已授权图内诊断抽头（不作单独根因证据）

1. 先用已有输出/日志；确需改图观测时，记录目标图和当前 `getOutputNodes()` 的**对象引用/完整身份**、节点/连接指纹及本轮临时资源清单，不靠 identifier 前缀找回原根。
2. 从已标根沿真实连接**反向追踪端口**确定源节点。禁止只凭坐标、definition id 或近似别名选“同名”节点。优先新建独立诊断图并联调用；若只能临时换根，需先证明抽头源的维度由自身上游固定，或保留下游定型消费者。多态 `min/max/add/ifelse/swizzle` 直接变唯一根可能改变类型解析，不能把读数当原值。
3. 记录每条源分量→诊断节点→comp swizzle→BMP 通道映射；用已知常量和独立统计做通道/量级自检。选择 direct 或无裁切的仿射编码并记录逆变换/量化容差。
4. 一条抽头读数仅形成假设；报告根因前至少取得一条**不经过该抽头**的独立证据（真实成图分区统计、另一数据路径等）。证据冲突时抽头标无效，不得用它覆盖真实图像。
5. 恢复保存的原根对象与连接，按所有权删除本轮临时节点/图；独立回读资源表、输出根与原逻辑指纹。超时/空响应先只读查状态，不盲目重做或假设删除完成。

### SOP-1：精确定位

```python
PACKAGE_PATH = r'<目标包绝对路径.sbs>'
GRAPH_ID = '<目标复合图标识>'
PP_ID = '<目标PP节点id>'

matches = [p for p in pkg_mgr.getUserPackages()
           if p.getFilePath() and normpath(p.getFilePath()) == normpath(PACKAGE_PATH)]
assert len(matches) == 1, 'Package not unique/loaded: ' + repr([p.getFilePath() for p in matches])
pkg = matches[0]
resources = list(pkg.getChildrenResources(True))
comps = [r for r in resources if r.getClassName() == 'SDSBSCompGraph']
funcs = [r for r in resources if r.getClassName() == 'SDSBSFunctionGraph']
targets = [r for r in comps if r.getIdentifier() == GRAPH_ID]
assert len(targets) == 1, 'Graph not unique: ' + GRAPH_ID
g = targets[0]
pp = [node for node in g.getNodes()
      if node.getDefinition().getId() == 'sbs::compositing::pixelprocessor']
selected = [node for node in pp if node.getIdentifier() == PP_ID]
assert len(selected) == 1, 'PP not unique: ' + PP_ID
pp_node = selected[0]
pg = pp_graph(pp_node)
assert pg is not None, 'Selected PP has no existing perpixel graph'
print('TARGET', pkg.getFilePath(), GRAPH_ID, PP_ID, 'modified', pkg.isModified())
print('RESOURCES', [r.getIdentifier() for r in comps], [r.getIdentifier() for r in funcs])
```

函数任务以 funcs 中精确资源身份定位，不要求先选 PP。同标识资源不唯一时使用可核实资源路径/URL进一步定位，否则停止。
包未加载可在用户授权的读取范围内 loadUserPackage 指定文件；加载不等于允许保存更新后的包。
内部图 identifier 可能为空，身份采用 `(规范化包路径, comp身份, PP id, 'perpixel')`；函数图采用完整资源身份。
跨图节点身份=`(包身份, 图身份, node id)`，禁止只用 node id 建全包字典。

### SOP-2：代码还原与快照

```python
outs = list(pg.getOutputNodes())
assert outs, 'Function graph has no output nodes'
for output in outs:
    print('OUTPUT', output.getIdentifier(), defid(output))
    for i, statement in enumerate(flatten(output, True)):
        if defid(statement) == 'set':
            print(i, statement.getIdentifier(), sval(statement, '__constant__'),
                  '=', D(src(statement, 'value')))
        else:
            print(i, statement.getIdentifier(), 'VALUE', D(statement))
```

还原 While、条件分支与函数调用时递归建立块 IR，保留端口、类型与求值顺序。遇到多个输出逐个处理，不默认 outs[0] 已覆盖全图。凡源码出现乘法、向量缩放或点积，必须在 IR 阶段记录操作数维度并产出**乘法节点选择表**（§7.5.1/I40），不允许留到连线后再判类型。凡源码出现 `mod`/`fmod`/`round`/`frac`/`trunc`/`sign`/`clamp`/`saturate`/`step`/`smoothstep` 或任何"同名不同义"的数值函数，必须查分支文件 `references/SD_BUILTIN_FUNCTIONS_v2.5.0.md`（原子目录 85 + 库 Functions 171 两源）并产出**数值语义选择表**（§7.5.3/I41）。
快照至少包含节点身份、定义、引用、逻辑属性精确值、输入连接两端口id、函数接口、输出集合及坐标。
当前会话与磁盘不同应保留两者来源；不能为了“对齐文件”丢弃未保存修改。

### SOP-3：循环台账与作用域初筛

```python
for w in [node for node in pg.getNodes() if defid(node) == 'while']:
    init = flatten(src(w, 'init'), True)
    body = flatten(src(w, 'loop'), True)
    init_names = {str(sval(n, '__constant__')) for n in init if defid(n) == 'set'}
    body_names = {str(sval(n, '__constant__')) for n in body if defid(n) == 'set'}
    self_reads = {str(sval(n, '__constant__')) for n in body if defid(n) == 'set'
                  and str(sval(n, '__constant__')) in get_names(src(n, 'value'))}
    own_state = init_names | body_names
    cond_state = get_names(src(w, 'cond')) & own_state
    missing = (self_reads | cond_state) - init_names
    print('WHILE', w.getIdentifier(), 'maxiter', sval(w, '__constant__'))
    print('EXIT_COND', D(src(w, 'cond')))
    print('INIT', sorted(init_names), 'BODY', sorted(body_names))
    print('I7_SIMPLE_SCREEN', 'missing', sorted(missing))
    print('TAIL', body[-1].getIdentifier() if body else None)
```

之后必须：

1. 判断 cond 为退出条件，打印初始判断值/零轮边界及预计迭代数，不因端口叫 cond 就按 C while 解释。
2. 将 init/cond/loop 的上游闭包作为候选范围；共享节点不一定归该循环，闭包不能当作唯一作用域证明。
3. I6 按每个循环和外层执行顺序核对：若环外通过 Get 读取循环状态，必须证明 While 先完整执行，并确认读取的是 Loop Body Set 更新后的变量；若使用 While 直接输出，则核对它确实代表所需的最后一轮 Body 值。两种方式都不得跨接 Cond/Body 内部节点。
4. I7 补充间接反馈、嵌套循环、分支写入、临时量先读后写。未完成补充分析时只报告初筛结果。
5. 记录尾值类型、零轮返回行为、maxiter是否足够；没有测试过零轮返回值时标未验证，不默认尾值已执行。
6. 每个 While 额外判 I34/I35：回读 `init`/`cond`/`loop` 的实际源连接与实例类型、`__constant__` 取值，并检查 `cond`/`loop` 闭包是否被跨分支共享。

源码移植或建图任务在创建任何节点之前，必须先执行 SOP-3A。

### SOP-3A：循环格式台账与 While 连接规划（建图前）

**触发**：源码（GLSL/HLSL/C-like）含任何循环格式，或图中已有 While 需要按 §7.9 复核。本步骤以纯数据形式完成，先于节点创建。

1. 扫描源码全部循环（含嵌套、宏/模板展开、`do-while`、`for(;;)`、`break`/`continue`），为每个循环建立 ledger 条目：
   `{loop_id, source_span, format, continue_cond, exit_cond, carried_state, per_iter_temp, break_targets, continue_targets, est_iters, max_iters_source, mapping}`。
2. `mapping` 只允许 `WHILE`（默认）或 `LOOP_UNROLL_EXCEPTION:<reason>`（§7.9.8）；其它取值视为降级未完成（N24/I32）。
3. 按 §7.9.2 写出该循环的 Init / Exit Cond / Loop Body 语句清单；按 §7.9.4–§7.9.5 写出 `break`/`continue`/`do-while` 所需的标志语句与条件包装；按 §7.9.7 推导 `Max iterations` 及其来源。
4. 生成**连接规划表**（仍不写 SD）：`{while_alias, init_src, cond_expr_root, loop_seq_root, max_iter_value, branch_private_nodes[], outside_readers[]}`。`branch_private_nodes` 必须是该闭包独占的节点，`outside_readers` 必须是环后新建的 Get。表的形态按 §7.9.10 模板填写：Init 主干、cond 判定子树、Body 主干（含嵌套层级）、tail Get 各自写出节点角色与端口。
5. 与 §4.5/A10 的 body Function Graph 决策合并：函数化只改变 loop 闭包内部结构，不改变"外层是 While"与连接规划。
6. 建图阶段按连接规划表与 §7.9.10 模板执行；完成后回读并断言三输入有源、`cond` 为 bool、上限默认有限可解释（或按 W7 合法使用 `-1`）、闭包私有（I34–I36）。

下面的模板打印现有图中 While 的连接规划现状，用于 I34/I35 初筛：

```python
for w in [n for n in pg.getNodes() if defid(n) == 'while']:
    print('WHILE', w.getIdentifier(), 'max_iter', sval(w, '__constant__'))
    for port in ('init', 'cond', 'loop'):
        prop = w.getPropertyFromId(port, C.Input)
        conns = w.getPropertyConnections(prop)
        upstream = [c.getOutputPropertyNode().getIdentifier() for c in conns]
        # 端口名固定，类型随实例多态：必须用实例类型判定，不能按定义默认值推断
        print('  PORT', port, prop.getType(), 'connected', bool(conns),
              'src', defid(src(w, port)), upstream)
    const = w.getPropertyFromId('__constant__', C.Input)
    value = w.getPropertyValue(const)
    print('  MAX_ITER_VALUE', value.get() if value is not None else None)
```

### SOP-4：函数扫描与接口核对

1. 递归枚举授权包中 funcs；读取节点数、Input 形参、Output 属性、getOutputNodes。
2. 遍历函数内部 Get，检查 I1、I10 与类型；保留死形参证据。
3. 遍历复合图、所有 PP 内部图及函数内部图的真实引用资源；缺失内部图记录，不调用 None.getNodes。
4. 对每个自定义函数实例，逐个打印调用端口与形参的 id、类型、连接与默认值，判 I11。发现差异时不能凭 label 更改端口。
5. 引用统计使用完整资源身份，不能用函数短名跨包合并。I12注明扫描范围和包外调用是否已核实。

下面模板打印真实接口，**不是完整 I11/I12 自动校验器**：

```python
for fg in funcs:
    print('FUNCTION', fg.getIdentifier(), 'nodes', len(list(fg.getNodes())))
    print('INPUTS', [(p.getId(), p.getType().getId()) for p in fg.getProperties(C.Input)])
    print('OUTPUT_PROPERTIES', [p.getId() for p in fg.getProperties(C.Output)])
    print('RETURN_NODES', [(n.getIdentifier(), defid(n)) for n in fg.getOutputNodes()])
    gets = {str(sval(n, '__constant__')) for n in fg.getNodes() if defid(n).startswith('get_')}
    unused = [p.getId() for p in fg.getProperties(C.Input) if p.getId() not in gets]
    print('UNUSED_FORMALS', unused)
```

### SOP-5：Get 消费者与名字初筛

```python
# PP 模式；函数模式改为 set名字 ∪ fg形参，不合并调用方父图参数。
defined = {str(sval(n, '__constant__')) for n in pg.getNodes() if defid(n) == 'set'}
known = defined | {p.getId() for p in g.getProperties(C.Input)}
known |= {p.getId() for p in pp_node.getProperties(C.Input) if p.getId().startswith('#')}
# 填入当前目标已核实的内建；例如历史案例的 $pos/$size。
# 默认空集合，不能把历史可用性直接当作当前目标的证据。
VERIFIED_BUILTINS = set()
outputs = {n.getIdentifier() for n in pg.getOutputNodes()}
consumers = consumers_map(pg)
dead, dangling, unknown_builtin = [], [], []
for node in pg.getNodes():
    if not defid(node).startswith('get_'):
        continue
    name = str(sval(node, '__constant__'))
    evidence = (node.getIdentifier(), name)
    if consumers.get(node.getIdentifier(), 0) == 0 and node.getIdentifier() not in outputs:
        dead.append(evidence)
    if name.startswith('$'):
        if name not in VERIFIED_BUILTINS:
            unknown_builtin.append(evidence)
    elif name not in known:
        dangling.append(evidence)
print('I1', 'FAIL' if dead else 'PASS', dead)
print('I2_NAME_SCREEN', dangling, 'UNVERIFIED_BUILTINS', unknown_builtin)
```

此初筛不能证明变量在读取前被定义，也不能检查嵌套作用域遮蔽或 `get_floatN` 维度；最终 I2 结合 I6/I7/I19/I43 和原生诊断。在逐函数 oracle 前，将真实 formal/Set/已验证 builtin/Get 回读成带作用域和维度的快照，先运行 `scripts/project_validation.py::check_get_dimensions`；未知 builtin 不得用 `$` 前缀直接放行。
不要以 # 开头直接免检；必须存在对应 PP 端口。

### SOP-5A：Architecture Pass 与 Function Graph 抽取计划

**触发**：分析/创建/修复任务满足 A1 任一条件；源码存在清晰命名函数边界；或用户明确要求拆图/函数化。纯布局任务若不允许逻辑变化，则执行到计划与报告为止，不修改结构。

1. 基于 SOP-2 的完整 IR，统计每张 PP 内部图和 Function Graph 的节点数、输出可达区、语义块、共享 DAG、Set/Sequence/While 状态块及初步规划跨度。若来源是命令式源码，先建立源码 statement/loop/function IR，不能只从已生成节点反推结构。
2. 建立候选子图签名。固定次数循环的 body 直接作为参数化重复候选，不等待展开后再做图同构发现。签名至少包含 definition id、输入端口 id、输出类型、内部边结构、引用资源身份和常量类型；同时生成“忽略可参数化常量值”的第二签名用于发现参数化同构。
3. 对每个候选计算边界：外部输入、内部状态读写、外部消费者、输出数量、类型、调用次数、节点数和副作用。不能证明作用域/顺序封闭时标 `FUNCTIONIZATION_BLOCKED:<reason>`。
4. 源码移植任务额外读取源码函数边界：命名函数先与 IR 区域对齐；可安全表达时优先一函数一 Function Graph，再在函数内部继续执行 A1/A7。
5. 生成纯数据 `ARCH_PLAN`，至少包括：`source_graph`、`source_nodes_before`、`candidate_id`、`semantic_name`、`node_keys`、`call_sites`、`inputs`、`outputs`、`parameterized_constants`、`side_effects`、`replaceable_nodes`、`caller_replacement_nodes`（实例及胶水）、`projected_caller_nodes = source_nodes_before - replaceable_nodes + caller_replacement_nodes`、`projected_function_nodes`、`safe`、`decision`（抽取/保留/阻断）、`reason`。按**实际要替换的调用方节点**计数，不把重复调用数乘到单个函数节点数上；无安全候选时也记录检查范围和原因。安全且能减少调用方节点数的候选，已授权结构修改时须抽取；因任务范围或结构风险保留时写 `STRUCTURAL_EXCEPTION:<reason>`，接口不安全则写 `FUNCTIONIZATION_BLOCKED:<reason>`。此阶段不删除节点。
6. 创建/修复已获授权时，按 A8 逐候选执行：先建新函数与接口，完成内部节点和返回；验证函数自身 I1/I2/I9/I10，并以独立 oracle 做非退化数值测试；创建首个实例并按 I11 回读真实端口、连接和类型；首个调用点通过 I24 数值/图像等价后再继续替换其它调用点。仅有计划、创建成功或 cook 成功均不算“已完成拆分”。
7. 删除旧区域只能发生在对应调用点已经重新连接并通过当前阶段验证之后。共享节点若仍被其它区域使用不得删除；消费者映射必须重新计算。
8. 全部替换完成后重新生成 Final IR 与结构统计，记录调用方和每张新 Function Graph 的**实际**节点数及其与第 5 步投影的差异，执行 I21–I31；每张新图独立应用 A1/§7.10.5，若仍触发并存在未处理安全候选则递归执行 SOP-5A，不能仅把主图减小作为完成证据。
9. 全部结构替换完成后先生成 **预布局**，执行 A11：检查每图节点数、重复候选、X/Y 跨度、statement band 数与最大单 band 尺寸。IR 或候选变化时回到本 SOP；同一版 IR 的候选已全部抽取或注明例外/阻断时，不因 `≥400` 重复空转。只有 Architecture Pass 完成、或所有剩余候选均有明确 `STRUCTURAL_EXCEPTION` / `FUNCTIONIZATION_BLOCKED`，才进入 SOP-8 最终布局。

离线脚本无法实际执行 SD 原生渲染时，可以生成 ARCH_PLAN、创建顺序和静态检查；I24 动态等价仍标未验证。

### SOP-5B：源码优先函数化与主图组装（新建/移植默认路径）

**触发**：新建 PP/Function Graph 交付、GLSL/HLSL/C-like 源码移植、或用户明确要求"先拆函数、再组装主图"。**既有图的修补/重构走 A8 的替换顺序，不走本 SOP。**

1. **只写计划**：按 SOP-2 建立源码 IR 与目标 IR，并按 L1 取得/记录用户的 A/B 图结构选择；除函数表，还要列出源码每个语义**section 和顶层 branch**，逐项标 `PORTED`/`OMITTED`/`BLOCKED`，并标出计算因子最终应被谁消费；按 SOP-3A 建循环台账；按 A9/§7.7 建**源码函数表**（函数名、参数、返回、调用关系、是否纯函数、读取的外部状态、循环/分支、副作用）；按 SOP-5A 第 5 步生成 `ARCH_PLAN`。同时生成 `BUILTIN_AVAILABILITY`、I42 向量槽位、I44 变换应用点、I16 广播降级、`BRANCH_COVERAGE`（源码路径→判别用例 id）、以及时间双通道来源/选择表（适用时）。重复调用的 helper 在写图前估算 `calls × helper_nodes + glue`，再对抽取方案估算调用方替换量与新函数自身节点数，分别执行 A1 预算；此阶段**不创建任何节点**。
2. **定函数边界与决策**：每个源码函数或语义区域给出 `FUNCTION_GRAPH` / `INLINE` / `BLOCKED`；循环体按 A10 作为候选；被调用 `>=2` 次、内部 `>=8` 有效计算节点或本身 `>=24` 节点的语义函数默认 `FUNCTION_GRAPH`。预计任何单图 `≥400` 时逐候选记录拆分前后投影；预计 `1200–1500` 时，若有安全且减量的候选，先函数化再进入高节点复核，保留则需 `STRUCTURAL_EXCEPTION`；`>1500` 先继续拆分或征求用户明确超预算批准。`BLOCKED` 必须写 `FUNCTIONIZATION_BLOCKED:<reason>`。
3. **先定接口再建图**：按 A5 为每个函数定形参表与返回表。**所有跨边界数据必须是显式 Input**；调用方局部 Set、PP `#` 端口、父 comp 参数不得被函数内部偷读（I23）。在每张 Function Graph 的 IR 中断言形参名与 loop-carried Set/Get 状态名**无交集**（Sun shower 中 formal `p` 遮蔽 carried `p`）；不同名状态在 Init 中从形参初始化。循环体函数必须把每个被更新状态**同时列为形参（入）与返回（出）**（§7.9.11）。
4. **先规划排布（仍不写 SD）**：函数边界与接口确定后，树形结构已经可知，因此按 L13/L16 为**每一张将要创建的图**生成纯数据布局计划：语句带与 Sequence 主干列、每个节点的角色/树深度/标称占位与**计划坐标**、While 与 Ifelse 子区域、网格原点。计划必须通过 L12/L14/L15 检查（零计划重叠、树方向、带完整性、归一化预算预估、计划中会出现的跨带边清单）。**计划未通过前不得创建任何节点。**
5. **自底向上创建函数图并逐个验证（创建即落位）**：先建被调者、再建调用者。每个节点在创建时立即写入其计划坐标（L16/I39）。每个函数完成"形参 → 内部语句/表达式 → 返回节点（`getOutputNodes`）"后**立即回读并判 I1/I2/I9/I10/I23/I42/I43/I44，再用非退化输入对独立数值 oracle 逐函数测试**；函数根默认经真实纯算子桥接：裸 formal Get 与直接控制/结构节点 `while/sequence/set` 都不得只凭 `getOutputNodes()` 认作调用点可读，偏离须当前会话探针和首调用点数值验证。向量用例的分量须非对称且能暴露交换；分支用例从源码控制流生成，`if` 两支、各 return/三元分支与关键边界都登记到 `BRANCH_COVERAGE`，未覆盖不得全量 PASS。编码方式与解码容差须能分辨下游量化台阶（§7.11）；函数自身触发 A1 时递归执行 SOP-5A/A7。**函数图未通过自身数值检查前不得创建实例。**
6. **组装主图并回读实例接口（创建即落位）**：在目标 PP/复合图中先建骨架（输入通道、PP `#` 端口、输出节点），再为每个调用点创建 Function 实例，均写计划坐标；逐端口回读 id/类型/连接判 I11（不假设 `input1/input2`）；首个调用点按 I24 通过后才复制其它调用点。
7. **在主图重建代码结构**：语句以 `Set` 落地并挂 `Sequence` 主干；生产 Set 接先执行 `In` 路径，下方带内 fresh typed `Get(name)` 的消费者接同一可达链的后执行 `Last` 路径（Get 本身无 Sequence 输入口）。先回读实际边/端口/输出可达性，再以非零变化用例验证名称、维度和作用域。不能等全部表达式建完才补 Sequence，却保留 Set→下方算子的 DAG 直连。Get 读值异常先修后分支连通性；拓扑正确仍异常才阻断或请求经数值验证的 Sequence-value 例外，不静默改变用户选定结构（§7.10/W15/N26）；循环按 §7.9.2 保持结构化 While，并按 **§7.9.10 模板 + §7.9.11 函数化规则**连线。标根后从输出沿真实边逆向遍历，IR 必需的 pre-loop Set/Sequence 与 While 必须全在可达闭包内；同名 Get 本身不形成 Set→Get 实边。PP 根维度与标记数量按 `MORPHING_RETEST_GATES.md` P0 回读。
8. **几何校正与收尾**：回读真实坐标、真实占用及各图节点数，比较 `ARCH_PLAN` 的调用方/新函数投影并解释偏差；对每张图重新执行 A1/SOP-5A 与 §7.10.5，高节点图还需响应/回读、cook、布局证据。按 SOP-8 第 6 步做**仅位置**的几何校正（整子树/整语句带平移、重新吸附、重新查碰撞）；按 §7.10.4–§7.10.6 判 I37/I38；生成 Final IR；按 SOP-9 验证与保存。报告须包含函数表、section/branch 覆盖表、`ARCH_PLAN`、布局计划与计划-实际偏差/校正轮次（I39）、实例与调用点清单、循环台账、归一化指标与未验证项。未能完成全量移植时，以可独立 oracle 验证的最大子集交付，并明确未移植层/预期图像差异，不能称全量一致。

**与 A8 的分工**：A8 的"原图快照 → 候选 IR → 新建函数 → 首个实例 → 回读端口 → 语义验证 → 其它调用点 → **删除被替代节点**"是**既有图替换**顺序；新建/移植任务没有"被替代节点"，因此走本 SOP 的"先函数化 → 再组装"，且不得遗留未接线的孤岛节点（I1/I2/I28）。

**SOP-5B 阶段锁（DI1）**：第 5 步不是事后补测项。每个函数执行 `create → readback → (已授权时保存/快照) → native cook → independent oracle compare → gate PASS`，再调用 `require_verified_dependencies(caller, deps, verified)`，通过后才允许第 6–7 步创建该函数的调用方/主 PP 实例。同一次 MCP 脚本可包含多个阶段，但必须在脚本内逐函数检查并在 FAIL 时立即停止，不能先构完 5 函数与主图再补单元测试。记录 `source_hash`、输入、来源路径/分支、原生值、独立 oracle、编码逆变换与容差；`check_function_numeric_gate` 检查单函数证据，`check_build_stage_order` 审计事件顺序。用非对称 vec2 故意交换分量作测试夹具负例；若错误未被拦住，不可将该单元 harness 用作放行门。一组非零输入只算 smoke test，未覆盖分支/边界须单列未验证。详见 `DESCENTE_INFINIE_RETEST_GATES.md` DI1。

### SOP-6：已授权创建/修复

1. 回读快照、代码 IR 和适用检查，给出诊断；用户已授权修复时直接继续，不另设无依据的确认关卡。
2. 在大规模创建/修复前执行 SOP-5A；未触发 A1 也应记录 Architecture Gate=PASS/N/A。源码已有函数边界时执行 A9 评估；源码含循环时先执行 SOP-3A 台账与 While 连接规划，再按 A10 评估 loop-body Function Graph（循环默认保留 While，unroll 仅在 §7.9.8 例外）。**新建/源码移植任务按 SOP-5B 先函数化再组装（A12）；既有图的修补/重构按 A8 替换顺序。**
3. 定义校验、端口读取后操作；按可回读的小阶段串行执行。避免隐式删除重建同名图。先执行 L1 的用户选择门：A 下命令式源码进入 **Statement 模式**，每条赋值/状态更新建立真实 Set，并由 Sequence 表达执行顺序；纯表达式函数进入 Expression。B 只允许无循环直线计算经记录 `USER_SELECTED_DAG` 后进入 Expression；状态/循环冲突须另问，不能自行改选。
4. 新节点以**布局计划坐标**创建（创建即落位：`newNode` 后立即 `setPosition` 到计划坐标，L16/I39），不再使用"临时初始坐标 + 事后整体排布"；计划尚未生成时不得开始大批创建。大批创建按授权保存阶段快照，不只等到全部完成才保存。新建/移植按 SOP-5B（先函数化 → 先规划排布 → 再组装主图）；既有图抽取遵守 A8（先建新函数，首个调用点验证通过前不删原区域）。生成后只做几何校正（SOP-8 第 6 步）。
5. 每个逻辑修改阶段后跑名字/连线/类型检查；结构重构阶段额外运行 I21–I31，循环阶段额外运行 I32–I36。所有节点/实例先创建并登记，再统一连线；While 按 §7.9.10 模板形态连线，完成后立即检查输出源、While 三输入实连、Set 活性与实例端口。完成后重新还原 Final IR，按目标语义对照。
6. Architecture Pass 已完成或有明确结构例外后，才执行适用最终布局：范围内需要布局则 SOP-8；用户明确暂缓则保留布局 WARN/未验证项。
7. SOP-9 通过后保存最终交付，并回读目标身份、各图节点数、最大图节点数、修改状态和文件路径。
8. 创建或修复后的逻辑指纹应与目标 IR 对照；不能拿“修改前后逻辑不同”本身判失败。I20用于纯布局阶段；结构化重构用 I24 判语义等价。

### SOP-7：离线创建/修改脚本交付

脚本必须包含：

- SOP-0 引导；固定且可修改的目标配置；环境/路径/权限前置检查。
- 定义存在性、资源定位、真实输入输出端口检查。
- 幂等策略：目标已存在且指纹/版本符合时打印并跳过；存在不一致或部分成果时明确报告停止/授权恢复，不能只按节点类型去重。
- 阶段运行使用分离的 helper 模块命名空间；只刷新本次自有的 `sys.modules` 项，避免共享 `exec` 遮蔽函数。创建前枚举实际资源 id，遇 `_1` 等自动后缀先核验身份/指纹，不按前缀清理用户资源。导出使用独占运行目录和精确文件名/前缀，不按子串选择或批量删除。
- Architecture Gate、SOP-5A 的 ARCH_PLAN 与幂等 Function 创建策略；**新建/移植任务按 SOP-5B 输出函数表、接口表、自底向上创建顺序与调用点清单（A12）**；触发 A1 时必须包含 I21–I31。源码含循环时必须包含 SOP-3A 的循环台账、`mapping` 决策（`WHILE` / `LOOP_UNROLL_EXCEPTION`）、按 §7.9.10 模板的连接规划表与 I32–I36 检查（loop 体函数化时另含 §7.9.11 的跨界状态表）；固定循环需记录 loop-body Function 决策与 Statement/Expression 模式。
- **创建前完成的布局计划（每节点计划坐标 + 标称占位 + 网格原点；模式 A 创建即落位）**；所有节点声明完成后再统一连线；生成后仅几何校正（L16/I39；既有图按 SOP-8 模式 B 做 position-only 应用，并记录 `POSTHOC_LAYOUT`）；后置 I1/I2/I6/I7/I13/I13b/I15/I20/I21–I39 等适用检查。
- 进度日志、异常 traceback；不得裸 except: pass；不得先打印“自检完成”却未调用检查。
- 构建完成标志只在检查与保存成功后写入；保存失败不得输出 BUILD OK。
- 明确执行入口与输出路径。历史插件入口为 initializeSDPlugin()；其它执行渠道按当前 SD 版本核实。

关键创建 API 模板：

```python
from sd.api.sdbasetypes import float2
from sd.api.sbs.sdsbsfunctiongraph import SDSBSFunctionGraph
from sd.api.sdtypefloat2 import SDTypeFloat2

def checked_new(graph, definition_id, position):
    valid = {d.getId() for d in graph.getNodeDefinitions()}
    assert definition_id in valid, 'Unknown definition: ' + definition_id
    node = graph.newNode(definition_id)
    node.setPosition(float2(float(position[0]), float(position[1])))
    return node

def connect_checked(from_node, from_output_id, to_node, to_input_id):
    assert from_node.getPropertyFromId(from_output_id, C.Output) is not None
    assert to_node.getPropertyFromId(to_input_id, C.Input) is not None
    # 还需依据目标判断是否允许覆盖已有连接；本模板不自动删除连接。
    return from_node.newPropertyConnectionFromId(from_output_id, to_node, to_input_id)

# 已授权创建新 PP 内部图时，才允许调用 newPropertyGraph。
prop = pp_node.getPropertyFromId('perpixel', C.Input)
inner = pp_node.getPropertyGraph(prop)
if inner is None:
    inner = pp_node.newPropertyGraph(prop, 'SDSBSFunctionGraph')

# 已确认目标函数不存在，并取得明确创建授权后执行。
fg = SDSBSFunctionGraph.sNew(pkg)
fg.setIdentifier('<新函数标识>')
fg.newProperty('p', SDTypeFloat2.sNew(), C.Input)
# body 由已验证定义的节点构造，并为每个节点设置位置。
# fg.setOutputNode(body, True)
```

**16.0.3 SDK 值/资源 API 回测（`SUN_SHOWER_RETEST_GATES.md`）**：`SDProperty` 本身没有 `setValue`；不要调用 `node.getPropertyFromId(...).setValue(...)`。输入值走 `node.getInputPropertyValueFromId(id)` / `node.setInputPropertyValueFromId(id, SDValueX.sNew(value))`；继承模式走 `graph.getPropertyInheritanceMethod(prop)` / `graph.setPropertyInheritanceMethod(prop, SDPropertyInheritanceMethod.Absolute)`。向量值先构造基类型，再作为**单个**实参传入：`SDValueFloat4.sNew(float4(r,g,b,a))`、`SDValueInt2.sNew(int2(log2w,log2h))`；`$outputsize=(5,5)` 在该回测得 32×32。资源用 `SDSBSCompGraph.sNew(pkg)` / `SDSBSFunctionGraph.sNew(pkg)`；本回测 `SDPackage.newResource` 不存在。代码经 `execute_sd_code` 调用时显式调用入口函数，不依赖 `__main__` 守卫；记录当前源码哈希并只刷新本次拥有的模块。具体 SDK 仍以当前版本能力回读为准。

新未保存包路径为空，不能通过“第一个空路径包”定位。使用本次创建取得的确切包对象；有保存授权时先保存到目标路径，再分阶段创建资源。
已保存目标包若在后续调用中找不到，先按规范化绝对路径重新获取/显式加载并核实资源数，绝不回退到新建空包；路径选择器报 `Package not found` 也须先列出已加载包的规范化候选。`exact_loaded_package_path` 可校验斜杠/反斜杠与大小写；若 SDK/MCP 路径查找仍失败，刷新 scene info 后用 `exact_loaded_package_index` 匹配**当前**报告的索引或直接使用已验证包对象，紧接保存前再次核实路径与图身份。不得硬编码历史索引或把该症状解释为包已卸载（DI7）。每轮原生数值判定前重跑已知常量活性 cook。导出按创建后读回的实际 graph identifier 和扩展名选文件，自动 `_1` 等后缀不等于请求名；清理只限本次运行确认为自有的临时对象。
多输出源必须显式选 id；不能为了方便在 connect_checked 中自动选第一个输出。

### SOP-8：布局计划、应用与验收

**触发**：用户要求布局；或已授权创建/修复的节点需要交付可读布局。遵守 §0.1 的范围例外。

**前置门**：创建/修复任务必须已有 Architecture Gate 结果。触发 A1 且存在安全拆分点时，先回到 SOP-5A；不得通过继续增大画布绕过。纯布局且无结构修改授权时可以继续布局，但必须在报告中保留结构问题，不宣称整体可维护性 PASS。

**入口模式**（先声明，决定"计划"与"应用"的先后，L16）：

- **模式 A（新建/移植，默认）**：**创建前**完成布局计划，节点创建即写计划坐标；生成后只做几何校正。
- **模式 B（既有图/纯布局）**：节点已存在，生成计划后仅做 position-only 应用；无 `POSTHOC_LAYOUT` 记录时只能用于既有图。

1. 读取目标图坐标和逻辑快照；**声明入口模式**；确定本次范围、代码/IR结构、网格原点、占位来源。
2. 按 L13 从代码/IR生成"语句主干 + 表达式树"的纯数据布局计划，不先写 SD。每个节点具有独立图身份、所属语句/结构块、树深度、角色、占位矩形与**计划坐标**（模式 A 必须在创建前完成）。
3. 计划中必须识别所有 Sequence、While、Set、返回根、Passthrough及共享 DAG；禁止把未识别节点统一塞入兜底列，禁止以最短线/重心/力导向式压缩替代代码结构。
4. 检查 L1–L8 的树方向、Sequence 自上而下顺序、Set/语句根同行、兄弟子树不交错、循环/分支结构边界，再检查占位矩形及相对网格；模式 A 还要在此阶段预判 L14/L15 与"计划中会出现的跨带边"。
5. 应用：模式 A 在创建时写计划坐标（`newNode` 后立即 `setPosition`，每节点创建即落位）；模式 B 仅对授权图 `setPosition(float2(x,y))`。两种模式都不在布局函数中保存或修改逻辑；保存由外层作业流程控制。
6. 回读真实坐标与真实占用，做**几何校正**（仅位置、按整子树/整语句带移动、重新吸附、重新查碰撞）；不以内存计划作为"已应用"证据；检查 I13/I13b/I20/I39。
7. 无逻辑变化时沿用原逻辑验证记录，并注明来源；必要时复核原生输出。若指纹差异，先定位与恢复，不用渲染看起来类似掩盖。
8. 如需保存则由外层按授权保存并回读；报告入口模式、计划-实际偏差与校正轮次、占位估计、视觉复核范围、绝对总跨度及其归一化解释（`Y_per_statement`/`X_per_level`/`nodes_per_statement`）、跨带长连线清单与例外（§7.10.4/I37/I38/I39）。

可复用的纯数据检查模板：

```python
def snap(value, origin=0.0, grid=32.0):
    return origin + round((value - origin) / grid) * grid

def grid_error(value, origin=0.0, grid=32.0):
    return abs(value - snap(value, origin, grid))

def overlap_pairs(rectangles):
    # 每项: (qualified_node_key, left, top, right, bottom)。
    # 坐标必须转换为同一锚点含义，不默认 SD Position 是矩形左上角。
    found = []
    for i, a in enumerate(rectangles):
        for b in rectangles[i + 1:]:
            if max(a[1], b[1]) < min(a[3], b[3]) and max(a[2], b[2]) < min(a[4], b[4]):
                found.append((a[0], b[0]))
    return found

def same_row(a_position, b_position, tolerance=2.0):
    return abs(a_position[1] - b_position[1]) <= tolerance
```

该模板只检查数据，不是完整布局算法，也不读取 SD 的实际可见尺寸。新布局默认在约束计划中用相同Y对齐；2单位为参考测量容差，不用于放宽明显的同行错误。
计划逻辑指纹至少包括：节点完整键及定义；引用完整身份；每个输入/输出端口id；连线源/目标完整键与两端口id；函数形参id及类型；输出集合；逻辑输入属性与常量精确值；节点/图语义注解；PP内部图归属。
排除 Position 与可再生成的纹理/编译缓存；属性读取失败或类型无法序列化时标未验证，不能用对象地址或截断显示字符串作为稳定指纹。

### SOP-9：结果验证与交付

1. 分别说明静态检查、SD编译/原生渲染、独立数学对照和跨引擎对照的执行范围。
2. 动态输入至少测试默认与相关边界；有分辨率/坐标相关逻辑时至少一张非方图；循环测试预计迭代数和可行的零轮/边界情形；存在循环时必须核对 I32–I36（降级映射、`cond` 取反、三输入实连、分支隔离、§7.9.10 模板一致性）与 §7.9 的格式降级要求。
3. 检查必需输入、Get/Set、函数接口、类型、退出条件与中间值复用；同时检查 I26–I31：源码结构可追溯、Set 活性、节点/实例登记、最终输出真实连线及树形几何。源码未定义或实现相关行为列为限制。
4. 发生结构化重构时执行 I24：至少比较输入/输出/类型/副作用顺序/参数映射；在线能力允许时对重构前后相同输入执行原生渲染对照。
5. 修改布局不重新解释源码；纯布局逻辑指纹必须保持一致。视觉复核未做不能声称精确 UI 排布验收。
6. 保存后的文件路径、包状态、图数量、各图节点数、最大图节点数、语句带数、`nodes_per_statement`、`Y_per_statement`、`X_per_level` 与跨带边数必须回读；响应空或丢失时先查状态/日志，不重复创建。
7. §9报告列出全部适用检查、Architecture 结果、差异、失败/警告、未验证项及产物路径。

## 6. 工具行为陷阱（T）

本表是来源文档中的历史观察及本次整理约束。能力随环境变化，回读当前API；不将未隔离的故障猜测写为普遍事实。

| ID | 历史观察/问题 | 执行动作 |
|---|---|---|
| T1 | get_scene_info漏列folder内函数图 | 递归getChildrenResources(True) |
| T2 | 顶层函数node_count可能报0 | len(list(fg.getNodes()))实读 |
| T3 | identifier解析工具未递归找函数图 | 用精确包对象与递归资源 |
| T4 | 跨包重名identifier取首个匹配 | 精确包路径；不猜 |
| T5 | execute_sd_code 每次顶层命名空间独立，但 SD Python 进程的 `sys.modules` 会保留已导入 helper | 每段自包含；阶段重跑只刷新本次自有模块，helper 分模块导入，不把多个文件 `exec` 进同一命名空间 |
| T6 | MCP可能注入pkg_mgr，类别等未注入 | 显式引导与import |
| T7 | 目标PP内部图挂在perpixel | 取该属性；不推断其它属性是否有函数图 |
| T8 | get_graph_info默认node_limit=100 | 显式上限或API全量读取 |
| T9 | SDValue显示对象地址 | .get()；精确记录各分量 |
| T10 | SDPackage没有getChildren | getChildrenResources(False/True) |
| T11 | #端口在PP自身，不在comp参数表 | 合并真实具名端口；#前缀不免检 |
| T12 | loop中临时Set不一定要init | 判断携带与每轮先写后读 |
| T13 | 节点id混入变量名字集合 | 分开存储；图身份限定id |
| T14 | 新PP的getPropertyGraph返回None | 仅在创建授权内newPropertyGraph |
| T15 | setOutputNode缺少isOutput参数报错 | setOutputNode(node, True) |
| T16 | 新包filePath为空，定位错包 | 保留确切对象；授权后立即定路径 |
| T17 | 空响应不代表未执行 | 回读节点/修改状态；不重复写 |
| T18 | Context没有getPackageMgr | getSDApplication().getPackageMgr() |
| T19 | 长调用stdout/stderr可能丢失 | 分阶段；进度文件+traceback；回读日志 |
| T20 | usage字符串注解调用疑似静默中断 | 这是未隔离的历史嫌疑；避免复用该调用。如任务需usage，核实注解类型/API，不把功能一律视为装饰 |
| T21 | 历史重负载后两次SD崩溃 | 在类似大批建图前告知用户保存其它未保存工程；分阶段保存与回读。节点数/跨度不是已证明的崩溃阈值 |
| T22 | 历史Python API无align/snap/grid | 自算相对网格；当前版本需查API，不能猜菜单能力已暴露 |
| T23 | SD API包装对象==不是稳定身份比较 | 用图限定的getIdentifier；跨图键带图身份 |
| T24 | 旧Sequence中点/固定384排法与参考不符 | L2/L3与I13b；不用旧模块合规认证 |
| T25 | 绝对32整数网格误报参考全部偏离 | 估计每图网格原点，相对吸附 |
| T26 | 统一128×96与真实节点尺寸不同 | 区分候选碰撞、计划占位、实测包围盒 |
| T27 | 节点标签或六位向量显示造成假证据 | 资源引用用真实对象；数值用精确分量 |
| T28 | 基线中 `SDPackage` 无 `getIdentifier()/save()` | 包身份用 `getFilePath()/isModified()`；保存用 package manager 的 `savePackage/savePackageAs`；当前版本仍需实读 API |
| T29 | 新包 `getFilePath()` 为空 | 持有本次 `newUserPackage()` 的确切对象；获得保存授权后尽早 `savePackageAs` 固定路径 |
| T30 | `$outputsize` 的值是 log2 指数对：16.0.3 回测 `(5,5)` 得 32×32，误填像素数可产生 8192×8192；只改 graph 尺寸也不一定改变 PP 实际尺寸 | 先按目标像素计算指数、设置/回读 comp 和 PP 的继承模式及值、导出后回读 BMP 真实尺寸；双 Absolute 是本次成功配方，不是所有工程的必选模式 |
| T31 | 16.0.3 基线中 PP `input` 未连接时 `$pos` 探针为 0 | 依赖 `$pos` 的任务先按 SOP-0A 验证/提供有效图像 input；不同版本不自动外推 |
| T32 | `SDTexture` 回读可能为 BGRA8 且 rowPitch 为负 | 读取像素时按实际 pixel format/rowPitch；不要把错误读回当图像错误 |
| T33 | 16.0.3 基线中 `mulscalar(a=float1, scalar=float1)` 静默得 0 | N20/I14：标量乘法用 `mul`；仅向量×标量用 `mulscalar` |
| T34 | 仅被同名 Get 读取、无真实执行可达性的 Set 会被消除/失效 | N19/I27：让 Set 进入 Sequence 主干或有真实返回值消费者 |
| T35 | Accretion 首次实跑中曾出现“While 携带逐像素状态失败”的最小复现，但这与 Adobe 官方 Pixel Processor While 用法冲突，且同轮已有诊断脚本污染史 | 仅保留为历史异常。先按官方 W1–W10 检查 Set/Get/Sequence、branch-private、类型和连线；仍失败才做 SOP-0A 探针。禁止据此默认 unroll |
| T36 | Function Graph 实例在同一基线中可正确处理逐像素输入 | 可用于大型逐像素计算的结构抽取；仍需当前任务接口/类型验证 |
| T37 | 自定义构建器若在后续节点尚未创建前调用统一 `wire()`，最终输出可能无连接而全 0 | 节点/实例声明完毕再统一连线；I28 最后断言输出源连接 |
| T38 | 共享 DAG 布局递归若遇共享节点立即 return，可能导致其唯一可达子树完全没布局 | 只有共享叶子可直接进入共享区；带子树的共享节点首次遇到时完整布局，后续消费者只引用 |
| T39 | Function 实例若未登记进表达式/布局表会停在默认坐标并重叠 | 每次 `newInstanceNode` 与原子节点一样立刻登记完整图键、角色、占位和初始坐标 |
| T40 | 不同 Function Graph / PP 内部图坐标空间独立 | 碰撞、跨度和树形几何必须按图分别统计；禁止跨图矩形比较 |
| T41 | `mul` 输入 id 为 `a`/`b`（标签 A/B），`mulscalar` 输入 id 为 `a`/`scalar`（标签 **Vector**/**Scale**，顺序不可交换）；官方描述为 "multiplies each component of the input **Vector** by the same scalar value **Scale**"，且 `a` 仅接受 float2/3/4；`mul` 官方为 "two **same type** values" 并接受同维向量；用 `getPropertyFromId` 查询 `A`、`B`、`Vector`、`Scale` 均返回 None | 连线/设参只用小写 id；向量×标量必须向量接 `a`、标量接 `scalar`；float1×float1 与同维向量用 `mul`、不同维先修 IR（§7.5.1/I40/N20；官方原文见 `references/SD_BUILTIN_FUNCTIONS_v2.5.0.md`） |
| T42 | SD **原子层只有 `atan2`、没有单参 `atan`**；`atan2` 输入 id `a`（标签 **Vector**，float2），输出弧度；官方语义为"输入向量与水平方向的夹角，**不需要像通常 atan2 那样交换 x/y**"。`cartesian` 输入 id **`rho`（标签 Length）/ `theta`（标签 Angle）**，输出 float2，官方公式 `Length × Float2(cos(Angle), sin(Angle))`。`vector2` 输入 id `componentsin`/`componentslast`（标签 `In`/`Last`），2 分量时 `componentsin`=水平 x、`componentslast`=垂直 y。旧规范"源码 `atan(x,y)` 需输入 `yx`"的指导**已作废**（会造成角度镜像） | 按 §7.5.2 映射表接线；`vector2` 组装 (水平, 垂直)；`atan(t)` 用 `atan2(vector2(1, t))`；`cartesian` 直接按 Length/Angle 接线（自带文档已给出端口，无需探针） |
| T43 | 数值语义在两个来源里，且原子层**没有** `round`/`frac`/`trunc`/`sign`/`clamp`/`saturate`/`step`/`smoothstep`（85 个原子定义全表核实为 0 命中）：这些只存在于内建库 Functions（`functions.sbs`，171 个函数图）。官方语义：`round_float1` = "Rounds up when decimal is **greater or equal than 0.5**"（实现 `floor(input+0.5)`，实测 `round_float1(−2.5)=−2`）、`sign` = "If X == 0, returns **1**"（实测成立）、`fmod` = "remainder of a/b with the **same sign as a**"（实测 `fmod(−0.25,1)=−0.25`）、`frac` = "fractional portion"（实现 `input - floor(input)`，实测 `frac(−0.25)=0.75`）、`step` = "one if **x ≥ a**"（实测边界含等号）；原子 `mod` 标签 Modulo、端口 `a`/`b`（标签 A/**Divisor**），**实测为 floor 基**（`mod(−0.25,1)=0.75`），与库函数 `fmod` 语义相反 | 按 §7.5.3 与分支文件 `references/SD_BUILTIN_FUNCTIONS_v2.5.0.md` 查表接线：GLSL `mod` 直接用原子 `mod`（已实测 floor 基）；HLSL/C `fmod` 用库函数 `fmod`；`round`/`frac`/`trunc`/`sign`/`clamp`/`saturate`/`step`/`smoothstep` 一律优先实例化库函数而非手搓（N27/I41/D35；实测基线见 `references/NATIVE_PROBE_RESULTS_v2.5.0.md`） |
| T44 | 连线层**不校验类型/维度**：`mulscalar.a←float1`、`mulscalar.scalar←float2`、`mul.a←float2` 同时 `mul.b←float1`、`mulscalar(a=float1, scalar=float2)` 四类混维连线经 `newPropertyConnectionFromId` **全部返回连接（无异常）**；这些 `mul`/`mulscalar` 样本及 `mod(float2,float1)` cook 为 0。rain_text 的 16.0.3 补充实测又表明混维 `add`/`sub`/`pow` 可产生非零的部分/恒等式外观，结果形状跟随输入 `a`，所以“混维统一静默 0”不成立 | 不得以"连线成功/无异常"或“结果看似合理”证明类型正确；维度与类型必须在创建前按 §7.5.1 判定链解析（I40），创建后逐端口回读；不同维度必须改成同维或正确的标量节点（§7.5.3/§11.11/D34） |
| T45 | **新建 PP 没有内部图**：`pp.getReferencedResource()` 对刚创建的 PP 返回 None，必须 `pp.newPropertyGraph(pp.getPropertyFromId('perpixel', Input), 'SDSBSFunctionGraph')` 实体化（属性 `perpixel`，label `Per pixel function`，`isFunctionOnly=True`）。PP 内部图的输出由 `SDSBSFunctionGraph.setOutputNode(node, True)` 标记**任意普通节点**（语料实测输出节点为 `pow`、`vector4`、`instance` 等），**不存在 "output 节点类型"** | 判断"缺输出"以 `getOutputNodes()` 为准（`loop whlie.sbs` 的 PP 内部图为 0 → 未标记输出，不是缺某类节点）；`sd_mcp_plugin` 未实现 `newPropertyGraph`，新建 PP 内部图必须走 SDK（`execute_sd_code`）（SOP-0B） |
| T46 | **原生数值验证通路**：`graph.compute()` 阻塞至 cook 完成，`sd.tools.export.exportSDGraphOutputs(graph, dir, 'bmp')` 导出 24bit **线性** BMP（实测：线性候选距离 ≤0.002、sRGB 候选 ≥0.07），无需保存工程与外部渲染器即可取得真实求值结果 | 数值与循环语义取证优先走该通路（SOP-0B）；负值/大值先仿射编码进 `[0,1]` 再读；精度受 8bit 量化限制（±1/255）；每项探针须给出**两种竞争语义**的预期值并取最近者 |
| T47 | **库函数实现图的取数陷阱**（三源核对时实测）：① `SDConnection.getOutputPropertyNode()` 返回的是**消费方**、`getInputPropertyNode()` 才是**源节点**（连接方向与直觉相反，反了就会把整张网表接错）；② `SDValueFloatN.get()` 返回结构化 `sdbasetypes.floatN`，对它 `str()` 只给 **6 位小数**（`9.0537e-05`→`9.1e-05`），逐分量读取才是精确值，比较必须按 **float32** 归一化；③ 节点坐标存在 float32 亚像素漂移（活动对象 `1189.3333740234375` vs 文件 `1189.33337`），跨源配对须按 3 位小数取整；④ 发行包里可能有**陈旧连接**（`distance_vec3` 中连向 `length_vec3` 已不存在的形参 `input_v`），活动对象里看不到、也不影响求值 | 库函数取数一律走 `scripts/dump_library_functions.py`（活动对象）+ `scripts/verify_library_functions.py`（独立 XML 解析）并做差分；不得只手写 XML 解析、不得用 `str()` 结果当真值、跨源配对不做精确坐标比较、不照抄文件里的边（§11.12/SOP-0B） |

| T48 | PP `$pos/$size` 被当作同一坐标约定，空间结构退化 | 16.0.3 本次 32²/双 Absolute 回测 `$pos` 位于像素中心、Y 向下，`$size≈32`、`$sizelog2≈5`；另一工程曾见 unit-like `$size`，原因未隔离，不能归因于继承模式。当前图用 float4/分两次探针核验 X/Y、尺寸、BMP 行方向与非对称图像；未验证时显式提供 aspect/virtual resolution。 |
| T49 | 某次 Set 后裸 Get 读 0，但 statement Sequence 有正确值；未证明 Get 消费路径接入同一 Sequence 的后分支 | RS2：原因未定，先核对/修复 `Set→In` 与 `Get→消费者→Last` 的可达拓扑，再查名称/类型/作用域与非零数值；不可据此禁用正确连接的 Get |
| T50 | 不同项目的 Sequence/Set 标记输出结果不一致 | RS3/RS4：默认追加纯算子 identity；必须回读 `getOutputNodes()` 并以独立数值 oracle 验证当前函数与调用点。不能把单个小探针提升为通用输出定律 |
| T51 | While Body 消费外部 Sequence 导致主线程挂死/MCP 超时 | SAFETY_INVARIANT_002：禁止该边；在 Body 内重建纯值 |
| T52 | `mulscalar(Sequence(floatN), scalar)` 值异常 | RS6：scalar 显式广播到 floatN，改用同维 `mul` |
## 7. 图语义与源码移植

### 7.0 PP 四条数据通道

| 通道 | 外部 | 内部读取 | 必查 |
|---|---|---|---|
| 图像输入槽 | PP input/input:N | samplecol/samplelum的int2(图槽,通道)及pos | 槽对应图像、通道、采样位置；图像源无需内部连线 |
| PP具名值端口 | PP实际存在的#Name端口及外部连线 | get_floatN/get_bool('#Name') | 完整端口id、类型、连接与默认值 |
| 父comp暴露参数 | 所属comp Input | Get('Name') | 名字、类型、取值及求值顺序 |
| 局部量 | 当前作用域Set | Get('name') | 定义、作用域、执行先后与类型 |

函数形参为该函数 Input，通过 Get 按名读取；不是第五条 PP 图像通道，也不能默认读取调用方参数。
名称解析的来源须核实；本文件不凭静态名字集合规定一切遮蔽情形的引擎查找优先级。

### 7.1 节点与端口速查

历史基线的端口如下；创建前仍查询当前定义及实例接口。

| 节点 | 语义/端口 |
|---|---|
| set | __constant__为名、value为表达式；有副作用，返回所赋值 |
| get_floatN/get_integerN/get_bool | __constant__为读取名；按类型读取 |
| sequence | 先seqin后seqlast，返回seqlast；它自身是需要布局的节点 |
| passthrough | input；走线整理，不新增执行语句 |
| while | init一次、cond为退出bool、loop为迭代体；__constant__为上限int1 |
| ifelse | condition / ifpath / elsepath；分支结果类型及状态写入要核对 |
| instance | getReferencedResource定位；输入id来自被调函数形参 |
| samplecol/samplelum | pos；__constant__为int2槽/通道；samplecol结果通常为颜色向量，核实实际类型 |
| add/sub/mul/div/min/max/mod/gt/gteq/lr/lreq/pow/dot | a / b；动态算术维度要传播检查 |
| mulscalar | a为向量 / scalar为float1 |
| lerp | a / b / x；x为插值权重 |
| atan2 | 输入 id `a`（标签 `Vector`），**float2 向量**；输出 float1；见 §7.5.2 官方语义 |
| floor/cos/sin/exp/log/sqrt/abs/neg/not | a；not的类型为bool |
| swizzle1/2/3 | vector；__constant__为int/int2/int3分量索引 |
| vector2/3/4 | componentsin（标签 In）/ componentslast（标签 Last）；逐级拼接，核对总维度；2 分量时 `componentsin`=x=水平、`componentslast`=y=垂直（§7.5.2） |
| const_* | __constant__为类型对应值 |

### 7.2 语句、变量版本与 Set/Sequence 值边界

把 `Set/Get/Sequence` 拆成“状态命名、执行顺序、值传输”三个职责。一次真机项目观察到裸 Get 返回 0、Sequence 输出正确，但未证实 Get 消费路径确实处于同一 Sequence 链的后执行分支；此观察只能触发拓扑排查，不能证明正确连线的 Get 不可靠。

1. 普通赋值 `x = expr`：`expr -> Set("x")`，Set 表示状态写入边界。
2. 用户选定 Statement/Get 结构时，写入 Set 位于先执行的 Sequence `In` 路径，下方同维 `Get("x")` 的消费者位于同一输出可达链的后执行 `Last` 路径。Get 无 Sequence 输入口；所谓“连上 Sequence”指其输出经下方表达式接入 `Last`。再以非零变化数值核实名称/类型/作用域；仅靠同名或画布上下位置不足以证明读值。
3. Get 读 0 时先核对真实端口/边和输出可达性，再查作用域、名称、维度及参数栈顺序；缺后分支连线则先修线。拓扑正确仍失败时记录运行时异常并请求显式备选，而非默认认为 Get 不可用。
4. 自更新 `x += y`：读旧状态的 Get 必须位于适当的后执行分支；计算后 `Set(x)` 接入当前语句的 `In` 路径，随后读取新值的 Get 应在下一后执行分支。
5. 同一 RHS 内部公共子表达式可复用；跨 statement 的变量依赖必须登记生产 Set、Sequence `In`/`Last` 端口顺序、消费带 Get 路径与维度/数值证据（或获准的 Sequence-value 例外），不允许从旧 RHS/Set 节点随意拉长线。
6. **Sequence 默认只作为局部 statement value carrier**。PP / Function Graph 最终输出默认经过纯算子归一化；这是一项保守构建策略，不是所有 Designer 图都禁止 Sequence 输出的引擎定律。例外须当前会话的最小探针与调用点数值验证（RS3/RS4）。
7. 坐标只用于阅读，不是执行证明；版本关系由控制结构、statement Sequence 和已验证的作用域规则证明。

**布局含义**：每个 Set 是语句写入根；对应 Sequence 位于 statement spine。下一语句依赖该写入时，其 Get 消费树须汇入同一可达 Sequence 链的后执行分支。布局只用于阅读，不能替代端口与路径检查；禁止把“创建 fresh Get”本身当成正确性的证据。

详见 `references/RUNTIME_SEMANTICS_BASELINE_v2.5.0.md` RS2–RS4。

### 7.3 While Loop 官方语义基线与硬限制

本节以 Adobe 官方 Control nodes、Set/Sequence、Pixel Processor 文档及 Adobe Substance 3D 官方 While 教程为基线。历史项目探针只能补充当前环境异常，不能推翻这些通用语义。

**W1 — 执行顺序**：`Init` 在第一次迭代前执行一次；随后每轮重新计算 `Exit Cond.`。`Exit Cond. == True` 时停止，False 时进入/继续 `Loop Body`。移植 C/GLSL 的“继续条件”时必须转换成 SD 的“退出条件”。

**W2 — 状态跨迭代保留**：官方明确说明变量会在迭代之间保留，并可在 Exit Cond. 中读取。因此循环计数器、累加器、raymarch 状态等可用 Set/Get 表达；不得因为一次失败探针就默认改成 unroll。

**W3 — Set/Get/Sequence 的循环规则**：Init/Body 可以使用 Set 表达状态写入；分支私有 Sequence 的先执行 `In` 路径包含 Set，后执行 `Last` 路径包含下一语句的 Get 消费者，且该链在 Body 内可达输出。仅同名、上下排布或一个未进入后分支的裸 Get 不构成读后写保证。Loop Body 内所有 Sequence 必须在 Body 闭包内部创建。

**W4 — 分支节点隔离是硬限制**：Cond/Body 计算闭包必须 branch-private。**SAFETY_INVARIANT_002**：**Loop Body 不得消费由 Body 外部产生的 Sequence 输出**；真机实测该形态可能挂死 Designer 主线程。进入 Body 的值必须由 Body 私有常量、formal、经过验证的 loop-local state read 或 Body 私有纯算子重建。禁止在生产会话自动探针复现已知 hang 图。

**W5 — 环前/环后变量传递**：
- 进入循环：外部 **Sequence 绝不直连 Body**。只读值用 formal/常量/纯算子或经过验证的 loop-local state read 在分支内重建。
- 离开循环：优先使用 While 的显式返回值或由 post-While 纯值路径承接的结果；若依赖命名状态，必须在当前版本/作用域证明 Get 可读到该写入，不能仅凭同名裸 Get 判定成功。
- 两个独立 While 的整段先后仍由外层 Sequence/依赖证明，但该外层 Sequence 不得作为另一个 While Body 的数值输入。

**W6 — While 输出**：官方定义为 Loop Body 最后一次迭代的结果。若首次 Exit Cond. 就为 True，官方文档没有明确“零轮时 While 直接输出”的值；任务依赖该值时必须做最小探针，不能推断。

**W7 — Max iterations**：循环在 Exit Cond. 为 True 或达到 `Max iterations` 时，以先发生者停止。`-1` 可取消上限；官方同时警告可能形成无限循环并令 Designer 无响应。Agent 默认保留有限安全上限，并按 §7.9.7 推导其来源；只有退出条件有明确可证明界限或用户明确要求时才使用 -1。

**W8 — Pixel Processor 中的意义**：Pixel Processor 对每个输出像素并行执行同一个 Function Graph，每个像素不知道邻居的计算结果。因此 While 的 Set/Get 状态是**当前像素这一次函数执行内部的状态**，不是跨像素共享内存。循环内可以按坐标 Sample 输入纹理来累计多个采样，但不能把“前一个输出像素的计算结果”当作下一个像素的可变全局状态。

**W9 — While 与 Function Graph 抽取**：大型 Loop Body 仍执行 Architecture Pass。可将纯计算子步骤抽成 Function Graph，再在 Loop Body 内用私有实例调用；这不要求把整个 While 展开。固定次数循环默认保留结构化 While；unroll 只在 §7.9.8 的显式例外下允许，并记录 `LOOP_UNROLL_EXCEPTION`。

**W10 — 嵌套与多循环**：官方没有把嵌套循环列为禁止项。不得默认“嵌套 While 不可用”；重点检查各层 branch-private 闭包、变量命名、Init、Set/Get 类型、Sequence 顺序与 Max iterations。若当前版本出现异常，再进入 SOP-0A 最小复现。

**W11 — 所有源码循环格式统一降级为 While**：`for`、`while`、`do-while`、`for(;;)`、嵌套循环、`break`/`continue` 循环、宏/模板展开循环一律映射为结构化 While（§7.9.2）。SD 图中不得保留"类 for"结构，也不得用纯 DAG 链模拟循环语义；固定次数、编译期常量次数都不构成 unroll 理由（N24/A10）。

**W12 — While 连接规划是交付物的一部分**：While 的 `init`、`cond`、`loop` 三个输入必须按 §7.9.3 规划，并在交付前回读断言各有**实际源连接**；`cond` 必须是取反后的退出条件 bool；`__constant__` 默认必须是可解释的有限上限；使用 `-1` 时必须满足 W7 例外并记录风险；端口 id 与实例类型必须来自回读（端口名固定、类型多态，对照 N4）。端口存在但未真正接线不算完成（N25/I34）。

**W13 — do-while / break / continue 必须显式降级**：`do-while` 必须保留"至少执行一轮"（首轮标志或 Init 复制一轮）；`break` 用出口标志并入 Exit Cond，并把 break 之后的语句包进 `ifelse`；`continue` 用标志包装其后的语句，且 `for` 的增量必须留在包装**之外**，否则计数器不更新会死循环（§7.9.4–§7.9.5/I33）。

**W14 — 默认每个源码循环一个 While**：除非已有记录的 §7.9.8 `LOOP_UNROLL_EXCEPTION`，一轮迭代等于 loop 闭包的一次执行，不允许把一个源码循环拆成多个 While、或把多个源码循环合并成一个 While（除非源码本身如此）。嵌套循环每级一个 While，各自 branch-private 闭包、各自退出条件与各自上限（§7.9.6）。

**W15 — 循环内状态 Get 的后分支连通性与数值验证**：Body 内 Set 接私有 Sequence 的先执行 `In` 路径，下一本带 fresh typed Get 的消费者接同一 Body 私有可达链的后执行 `Last` 路径；回读实际端口、输出可达性、scope/type 和非零变化值。历史裸 Get=0 案例未证明后分支连线正确，因此优先排查/修复连线。拓扑正确仍失败时才申请经验证的 Sequence-value 例外。禁止直接复用旧 RHS/Set 输出；任何进入 While Body 的 Sequence 都必须由 Body 内部产生（SAFETY_INVARIANT_002）。

**W16 — 跨度按语句与深度归一化，不设绝对高度墙**：`spanY` 主要由语句带数决定，`spanX` 主要由表达式深度决定。参考实测 43 个语句带对应 `spanY` 11419（≈266 px/带）、行步中位 224、`Y_per_statement` 中位 230；列步中位 160、`X_per_level` 中位 ≈150（§11.7）。因此禁止用绝对 Y/X 数值判错，也禁止为压跨度交错混排不同语句的私有子树（§7.10.4/I38）。

### 7.4 While 移植与验收表

| 源码/需求 | SD 表达 | 必查 |
|---|---|---|
| `while (i < N)` | Exit Cond = `i >= N` | True 是停止；i 在 Init 定义且 Body 更新 |
| `for(i=0; i<N; ++i)` | Init Set i=0；Cond `i>=N`；Body 尾部 Set i=i+1 | increment 与其它状态更新的 Sequence 顺序；含 `continue` 时增量必须仍在包装之外 |
| `do { B } while (C)` | Init：初值 + `Set firstPass=true`；Cond `not firstPass and not C`；Body：B + 尾部 `Set firstPass=false` | 必须至少执行一轮；不得退化为普通 while（§7.9.5） |
| `while (C) { if (x) break; B }` | Init：初值 + `Set brk=false`；Cond `not C or brk`；Body：`Set brk=true` 并把其后语句包进 ifelse | break 之后语句不得继续执行；嵌套时只影响最内层（§7.9.4） |
| `while (C) { if (x) continue; B }` | 初值 + 每轮复位 `Set cont`；Cond 不变；Body：`Set cont=true` + `ifelse(not cont, B)`；`for` 的增量在包装之外 | 标志复位位置；`for` 增量不能被跳过（§7.9.4） |
| `acc += sample(...)` | Body: Get acc → sample/运算 → Set acc | Set 后再次使用 acc 时新建 Get |
| 多个状态 | Init 分别 Set；Body 按源码顺序更新 | 需要 read-after-write 的位置必须 Sequence |
| 环外读取最终状态 | Sequence 保证 While 完成 → 新 Get(state) | 不直接跨接 Body 内部节点 |
| 一个直接循环结果 | While 输出 | 仅代表最后一次 Body 返回值；零轮未定义需探针 |
| 两个循环共享变量 | Sequence(loopA, loopB/后续读取) | 不依赖画布上下位置 |
| 固定大循环 | 结构化 While（默认唯一映射目标） | 按 §7.9.2 降级；unroll 仅在 §7.9.8 显式例外下并记录 `LOOP_UNROLL_EXCEPTION` |

**完整格式清单（含 `for(;;)`、多出口、非 1 步长、空体、宏展开）与端口级连接规划见 §7.9**：任何源码循环都必须按 §7.9.2 降级，并按 §7.9.3 完成 While 连接规划后才算完成移植。

历史示例轮数仍可用于 cond 方向检查：

| 源码继续条件 | SD Exit Cond | 示例轮数 |
|---|---|---|
| i<10，i=0，步长1.5 | not(i<10) 或 i>=10 | 7 |
| j<=13，j=1，步长1 | not(j<=13) 或 j>13 | 13 |
| i<25，i=0，步长1 | not(i<25) 或 i>=25 | 25 |

官方基线来源：Adobe `Control nodes`（While/Sequence）、`Using the Set/Sequence nodes`、`Variables / Get`、`Pixel processor`，以及 Adobe Substance 3D 官方视频 **While Loops in Substance 3D Designer**（Designer 13.0 引入 loops；演示 Pixel Processor 中的 While）。

### 7.5 广播、坐标和颜色

本节通用条目（先读），随后 §7.5.1 规定乘法节点选择、§7.5.2 规定角度与向量组装：

- 向量加减标量先显式构造同维常量/广播向量；不按GLSL隐式广播理解SD mul/add/sub。
- `p*r(a)`须从源码矩阵定义推导方向；Shadertoy_Glow基线使用x'=x*cos(a)-y*sin(a)、y'=x*sin(a)+y*cos(a)。
- **坐标基线**：PP 内 `$pos` 按官方文档作为 `[0,1]` 归一化坐标；`$size` 官方定义为当前节点像素尺寸，但一个 PP 上下文曾出现 unit-size 观察，因此依赖它的写操作必须先用当前上下文探针确认。未验证时用明确输出宽高/virtual resolution 重建 aspect（RS1）。
- 设置$outputsize=(11,11)意图得到2048平方图时明确Absolute继承；改变继承方式需在授权修改内。
- Time/Audio是该案例的外部接口，不是所有SD工程强制参数；Audio替代音频纹理R采样后图内再pow(Audio,1.8)。
- 反向smoothstep、半整数round、负数mod/fract、GPU/FMA/hash高频精度属于需说明的实现约定，按任务做对照。
- 合成先存入新名，例如exposedColor，色调映射只读该名；避免Set后重新执行读取同名旧值的整段合成表达式。

#### 7.5.1 乘法节点选择：`mul` / `mulscalar`（强制表，实测语料）

| 操作数组合 | 定义 | 端口绑定 | 依据 |
|---|---|---|---|
| float1 × float1 | **`mul`** | `a`、`b`（均 float1） | 4 个参考包 **437/437** 处 `mul` 全是 float1×float1（§11.8） |
| floatN × float1（N=2/3/4），纯表达式向量 | **`mulscalar`** | 向量 → **`a`**，标量 → **`scalar`** | 仅限非 Sequence-derived value |
| floatN × float1（N=2/3/4），**Sequence-derived 向量** | **同维 `mul` + 显式广播 scalar→floatN** | valueN→a，broadcastN→b | RS6：真机 `mulscalar(Sequence(float4), const)` 不可靠 |
| float1 × floatN（N=2/3/4） | **`mulscalar`** | 同上：向量始终放 `a`，与源码书写顺序无关 | 语料无反向先例，按对称处理 |
| floatN × floatN（N=2/3/4，**同维**） | **`mul`** | `a`、`b` | **已确认：`mul` 接受同维向量**（现场确认 2026-09-22；语料虽无实例，但语义与端口一致） |
| floatN × floatM（N≠M） | 无合法选择 | — | `mul` 只接受同维；维度不匹配属源码类型错误，先修 IR（I16），不得靠换节点掩盖 |
| 向量归约（点积等） | `dot` | 按实例回读 | 端口读回 Float2 而实际上游为 Float3 → **端口类型不可信**；CRATE 16.0.3 原生用例的 float2/float3 同维点积均正确返回 float1，不必仅因端口读回为 `dot` 手造替代 |

**端口标识（16.0.3 回读：务必区分"代码 id"与"软件内标识/标签"）**

| 定义 | 代码中的属性 id（`getPropertyFromId` / 连接参数） | 软件内标识（标签） | 类型语义 |
|---|---|---|---|
| `sbs::function::mul` | **`a`**、**`b`** | **`A`**、**`B`** | 同维相乘（含 float1×float1）；N 由操作数决定 |
| `sbs::function::mulscalar` | **`a`**、**`scalar`** | **`Vector`**、**`Scale`** | `a`=float2/3/4，`scalar`=float1 |

- **顺序不可交换**：`mulscalar` 的向量位是 `a`（Vector）、标量位是 `scalar`（Scale）。源码写 `float * vec3` 也必须把向量接 `a`、标量接 `scalar`，不得按书写顺序绑定。
- **`mul` 不广播 float1 到向量**：floatN×float1 必须改走 `mulscalar(a=vector, scalar=float1)`，或先明确广播为 floatN 再用同维 `mul`。Sun shower 中轴向量与正确的标量相乘却读出 0，原因正是 float3/float1 混维；同样的静默结果不代表所有其它混维运算都必为 0。I40 类型表覆盖每个 `mul`/`add`/`sub`/`div`/`pow` 的两侧维度，创建前断言同维。
- **只有小写 id 能被 API 解析**：实测 `getPropertyFromId('A'|'B'|'Vector'|'Scale', C.Input)` **全部返回 None**。因此连线、设参一律使用 `a`/`b`、`a`/`scalar`；`A`/`B`/`Vector`/`Scale` 仅用于向用户说明语义角色。
- 两个定义的输出端口都是 `unique_filter_output`；不存在 `input1`/`input2`。
- 把标签当端口 id 提交会直接失败或报错——这属于"猜端口"，按 N4/I11 判 FAIL（D34 新增此症状）。

**维度判定流程（`mul`/`mulscalar` 混用的根因，必须先做）**：

1. **权威来源=真正决定维度的节点**：`get_floatN` / `const_floatN` / 函数形参声明 / PP `#` 端口 / swizzle 的输出选择 / `samplecol` 等；标量结果节点如 `dot`。16.0.3 原子定义中无 `sbs::function::length`；先查内建库 `length_vecN`，或对已核验维度构造 `sqrt(dot(v,v))`。
2. **多态节点（`add`/`sub`/`mul`/`div`/`pow`/`lerp`/`ifelse` 等）必须递归回溯到上述节点**，或直接采用源码 IR 推导出的类型。**不得**把任一单项作为唯一依据：节点定义默认类型、实例端口类型读回、上游节点的孤立类型字符串。
3. **实测反例（务必记住）**：21/24 处 `mulscalar.a` 端口类型为 Float2，而其上游节点读回是泛型 `SDTypeFloat`（`swizzle1`/`get_float1`/`sub`）；`dot` 端口报 Float2 而上游是 Float3；`add` 也有端口读回 `Float` 而实际收到 Float2 的实例。**"看起来是标量"往往实际是向量** —— 这正是把向量送进 `mul`、或把标量送进 `mulscalar` 的典型成因。
4. **判定时机属于 IR 阶段**：创建前必须产出"乘法节点选择表"（每处乘法的操作数维度、判定依据链、definition 与端口绑定），与 L16 的计划坐标同期完成；创建时按表落节点，不在连线后凭试错改节点类型。
5. **端口名不要猜，也不要用标签**：代码用 `a`/`b`（`mul`）与 `a`/`scalar`（`mulscalar`）；`A`/`B`/`Vector`/`Scale` 只是软件内标签，`getPropertyFromId` 不认（返回 None）。
6. **两类静默错误**：`mulscalar(a=float1, scalar=float1)` 在 16.0.3 静默返回 0（T33）；`scalar` 端口接向量类型不符。二者都可能"编译通过但结果错"，因此判错只能靠类型解析链与回读，不能靠图像。
7. 只有乘法存在标量变体（`list_node_definitions` 过滤 `scalar` 仅返回 `sbs::function::mulscalar`，不存在 `divscalar`/`addscalar`）；`add`/`sub`/`div`/`pow` 的向量运算按 I16 显式同维或按分量展开。

**GLSL 标量广播降级（I16）**：在 IR 逐处列出 `source expression / operand dimensions / explicit lowering / port bindings`。`vecN ± scalar`、`scalar − vecN`、`vecN / scalar`、`min/max/pow/mod(vecN,scalar)` 与 `clamp(vecN,scalar,scalar)` 先把 scalar 通过 `vectorN` 复制为 N 个同值分量，再接同维普通算术；减法保留源码左右次序。`vecN*scalar` 通常走 `mulscalar(a=vecN,scalar=s)`，Sequence-derived 向量按 RS6 显式广播后走同维 `mul`。`lerp(a,b,x)` 的 `x` 是本来就应为标量的权重，不误广播。每个降级后的普通二元节点要从源 IR 解析两侧维度并静态断言相同；详见 `CRATE_AT_DUSK_RETEST_GATES.md`。

#### 7.5.2 角度与向量组装：`atan2` / `vector2` / `cartesian`（官方语义）

**官方定义（Adobe 节点文档，现场确认）**：`Arc tangent 2` 返回 2D 向量 `Vector` **与水平方向的夹角（弧度）**；**不需要像通常的 atan2 函数那样交换 x 和 y**；它是 Cartesian 函数的反函数。

**端口（16.0.3 回读）**：

| 定义 | 代码 id | 软件标签 | 类型 | 输出 |
|---|---|---|---|---|
| `sbs::function::atan2` | **`a`** | **`Vector`** | float2 | float1（弧度） |
| `sbs::function::vector2` | **`componentsin`** / **`componentslast`** | `In` / `Last` | 均为 float1 | float2 |

- `getPropertyFromId('Vector')` / `'vector'` / `'input1'` / `'A'` 在 `atan2` 上**均返回 None**（与 T40 同族的"标签 ≠ 代码 id"陷阱）。
- **`componentsin` = 第一个分量 = x = 水平分量**，**`componentslast` = 最后的分量 = y = 垂直分量**（由标签顺序 `In`→`Last` 与现场构造记录共同确认；语料 23 处 `vector2`）。
- 语料 4 处 `atan2` **全部由 `vector2` 组装后接入 `a`**，无一例直接接 swizzle 结果。

**映射表（按语义，不按参数名）**：

| 源码 | SD 构造 |
|---|---|
| `atan2(y, x)`（y=垂直、x=水平，数学/GLSL 常规） | `vector2(componentsin = x, componentslast = y)` → `atan2.a`；**不要交换 x/y** |
| 已有 (x=水平, y=垂直) 的向量 `v` | `atan2.a = v` 直接接，**不做 yx swizzle** |
| `atan2(x, y)`（源码自己把 x 写进 y 槽的非常规写法） | 按语义：垂直分量是 x、水平分量是 y → `vector2(componentsin = y, componentslast = x)`。**判定依据是"哪个量是垂直/水平"，不是参数名顺序** |
| 单参数 `atan(t)`（**SD 无此节点**，只有 `atan2`） | `atan2(a = vector2(componentsin = 1, componentslast = t))`，即 atan2(t, 1) = atan(t) |
| 角度 → 向量（极坐标重构、Cartesian） | `cartesian`：输入 `rho`（标签 **Length**）/ `theta`（标签 **Angle**），输出 float2，官方公式 `Length × Float2(cos(Angle), sin(Angle))`；与 `atan2` 互为反函数，端口来自 SD 自带文档（T42/§11.10），无需探针 |

**作废的旧指导**：旧规范写的"SD atan2 实测为 atan(a.y,a.x)；源代码 `atan(p.x,p.y)` 需输入 `p.yx`"——公式部分与官方一致（输入向量的 y 为垂直、x 为水平），但"**需交换 yx**"的指导是**错的**：按它接线会把分量对调，使角度镜像。现统一为"按（水平, 垂直）语义组装向量，不做交换"（本项已在 §11.9 与两处 case study 中同步更正）。

**GLSL 矩阵移植门槛**：`matN` 构造器中的向量是列；`M*v` 要从列转出行并逐行与 `v` 点乘，`v*M` 则逐列点乘。每个不同矩阵用非对称且含非零/符号分量的输入独立验证；Morphing 回测修正 ACES `mat3` 行列后，函数测试从 17/20 升为 20/20。纯数据转置校验见 `scripts/project_validation.py` 的 `glsl_matrix_rows`；详见 `MORPHING_RETEST_GATES.md` P2。

**向量槽位与变换落点（I42/I44）**：`vector3(componentsin=vector2(x,y),componentslast=z)` 才是 `(x,y,z)`；`vector2(x,z)` 再接 `y` 得 `(x,z,y)`。`vector4` 同理，前 N−1 个有序分量进 `componentsin`，最后一个进 `componentslast`；按当前图定义回读端口后连接。对每个矩阵/旋转，枚举源码中每一处应用（位置、法线、软法线、光线方向、UV），逐点映射至 IR 并分别用非对称数据测试。`T=0` 不代表变换必为单位阵；CRATE 的 `rotZ(0.3)` 是反例。

只读XML时，历史float类型码为256/512/1024/2048对应float1/2/3/4；这些记录不授权手写XML。

#### 7.5.3 数值语义：`mod`/`fmod`/`round`/`frac`/`trunc`/`sign`/`clamp`/`saturate`/`step`/`smoothstep`（两源查证）

**两个供给源必须分清**（详见分支文件 `references/SD_BUILTIN_FUNCTIONS_v2.5.0.md`，用到时按其查找）：

| 供给源 | 内容 | 数量 | 调用方式 |
|---|---|---|---|
| A. 原子函数节点 | `sbs::function::*` | **85** | `create_node` 直接建 |
| B. 内建库 Functions | 图书馆 Functions 分类的函数图资源（`Functions/Math`、`Functions/Trigo`、`Functions/Transforms`…） | **171** | **instance 节点**调用；输入 id = 其形参名 |

**原子层没有** `round`/`frac`/`trunc`/`sign`/`clamp`/`saturate`/`step`/`smoothstep`/`fmod`（85 个定义全表核实 0 命中）；它们**只存在于 B**。反之 `mod`/`floor`/`ceil`/`atan2`/`cartesian`/`lerp`/`min`/`max`/`pow`/`sqrt`/`log`/`exp`/`log2`/`pow2`/`abs`/`neg`/`div`/`dot`/`rand` 在 A。**凡"SD 没有 X"的结论，必须两源都查过才允许写**（N27/I41/D35）。

**强制映射表（源码语义 → SD 供给）**：

| 源码意图 | 选用 | 标识与端口 | 官方语义（原文要点） |
|---|---|---|---|
| GLSL `mod(x,y)`（floor 基，符号随 y） | **原子 `mod`**（已实测为 floor 基，与 GLSL `mod` 一致） | 原子 `mod`：`a`(A) / `b`(**Divisor**) | "returns modulo of entry value: mod(A,Divisor)"；**实测**：`mod(−0.25,1)=0.75`、`mod(1.25,−1)=−0.75`、向量逐分量 floor 基（§11.11） |
| C/HLSL `fmod(x,y)`（截断基，符号随 x） | **库函数 `fmod`** | `Functions/Math/fmod`：`a`(A) / `b`(B) | "remainder of a/b with the **same sign as a**"；**实测** `fmod(−0.25,1)=−0.25`，与原子 `mod` 的 `0.75` 差 1.0（§11.11） |
| `round(x)` | **库函数 `round_float1`** | `input` | "**Rounds up when decimal is greater or equal than 0.5**"（实现 `floor(input+0.5)`） |
| `frac`/`fract` | **库函数 `frac`** | `input` | "fractional portion of a scalar"（实现 `input − floor(input)`，floor 基） |
| 截断到 N 位小数 | **库函数 `truncate_float1_decimals`** | `input` / `decimals`(**int1**) | "Truncates a Float1's to a specific amount of decimals" |
| `trunc(x)`（向零截断） | **显式构造** `ifelse(x<0, ceil(x), floor(x))` | 原子 `ceil`/`floor`/`lr`/`ifelse` | SD 无现成 trunc |
| `sign(x)` | **库函数 `sign`**（注意零） | `x`(X) | "Returns the sign of a scalar. **If X == 0, returns 1**" |
| `clamp`/`saturate` | **库函数 `clamp`/`saturate`** | `input`/`min`/`max`；`input` | "Returns Min or Max if the input is outside of the Min/Max range"；"0 if lower than 0, 1 if greater than 1" |
| `step(edge,x)` | **库函数 `step`** | `a`(A,=edge) / `x`(X) | "one if **x is greater than or equal to a**" |
| `smoothstep(a,b,x)` | **库函数 `smoothstep`** | `a`/`b`/`x` | "Smooth interpolation between A and B in function of X" |

**强制规则**：

1. **先判语义类别，再选供给**：`mod` 与 `fmod` 是两件不同的事。**实测（§11.11）**：原子 `mod` 是 **floor 基**——`mod(−0.25,1)=0.75`、`mod(1.25,−1)=−0.75`（符号随除数）、向量逐分量同规则，与 GLSL `mod` 一致；库函数 `fmod` 是**截断基**——`fmod(−0.25,1)=−0.25`（符号随被除数）。同一输入两者差 1.0。GLSL `mod` 直接用原子 `mod`，C/HLSL `fmod` 用库函数 `fmod`，**禁止互相顶替**（N27）。
2. **可达时优先实例化库函数**，不要把“文件中存在”误作“当前会话可取到活 resource”。先在当前包/版本找到精确库资源，最小实例回读接口并在首调用点做数值测试。Adobe SDK 有 `loadUserPackage`/`findResourceFromUrl` 的官方实例，但 `functions.sbs` 在本 MCP 环境的可达性**尚未证实**；不得把文档检索脚本当成可实例化资源。若实际不可达，记录 `LIBRARY_INSTANCE_UNREACHABLE:<尝试与结果>`，按 Adobe 实现/目标语义显式构造，做独立 oracle 等价验证；跨包读取仍按 `REAL_PROJECT_VALIDATION.md` 第 5 条保持未验证至调用点实测。库函数语义与源码不一致时也允许带证据显式构造。
3. **半整数约定必须对照**：`round_float1` 是 `floor(x+0.5)`（半整数向 +∞）。若源码为"远离零"或"银行家取整"，负数半整数差 1 → 显式构造并说明依据。
4. **零点与边界必须对照**：`sign(0)=1`（非 0）；`step` 是 `x ≥ a`（写反整段反向）；`frac` 是 floor 基（`frac(-0.25)=0.75`，与 `fmod(-0.25,1)=-0.25` 不同）。
5. **端口 id 用形参名，不用标签**：库函数输入 id 来自 `paraminput/identifier`（如 `input`/`min`/`max`/`a`/`b`/`x`/`decimals`），标签（`Input`/`Min`/`X`/`A`/`Divisor`）不可作为端口 id（T40/T41 同族）。
6. **库函数实例同样纳入布局与登记**：按 T39/I39 立即登记图键与计划坐标；其输出端口名来自被调函数，**不保证是 `unique_filter_output`**，必须回读。
7. **创建前产出可用性与数值语义选择表**：先按 `SD_BUILTIN_FUNCTIONS_v2.5.0.md` 查原子/库候选及当前会话资源可达性，再判语义（I41，与 I40 乘法表、I16 广播表、L16 计划坐标同期完成）。
8. **查找入口**（用到时才查，不要凭记忆）：分支文件 §2 给出 SD 自带文档路径
   `resources\documentation\pythonapi\html\_sources\pythonapi\modules\sbs_function.rst.txt`（85 个原子定义的官方 Label/Description/端口）与
   `resources\packages\functions.sbs`（171 个库函数，含官方描述与实现图），以及工具
   `scripts\lookup_sd_function.py --name <正则>` / `--library --name <正则> --impl`。
9. **同维是硬要求；混维行为不可依赖（实测）**：`mod(float2, float1)`、`mul(float2, float1)` 在原生探针中静默返回 0，但 rain_text 的 16.0.3 实测表明混维 `add`/`sub`/`pow` 可能返回部分或恒等式外观，且输出形状跟随输入 `a`。这些都不是广播契约。需要向量×标量时，要么用 `mulscalar`（向量接 `a`/Vector、标量接 `scalar`/Scale），要么显式广播成同维（如 `vector2(b,b)`）。
10. **连线成功 ≠ 类型正确（实测混维连线均被接受）**：`newPropertyConnectionFromId` 不校验维度与多态类型，错误只在 cook 时显现，既可能是静默 0，也可能是迷惑性的非零值。因此维度与类型必须在**创建前**按 §7.5.1 的判定链解析（I40），创建后逐端口回读；不得用"连线没报错"或“数值非零”当作类型正确（T44）。
11. **数值语义用原生探针取证**：`graph.compute()`（真实 cook，阻塞至完成）+ `sd.tools.export.exportSDGraphOutputs(graph, dir, 'bmp')`（实测导出为 24bit **线性** BMP）→ 把结果与**两种竞争语义**的预期值比较取最近者。现成探针：`scripts/probe_sd_semantics.py`；实测基线与局限：`references/NATIVE_PROBE_RESULTS_v2.5.0.md`（SOP-0B/T46）。

#### 7.5.4 时间来源双通道

保留系统 `$time` 与自定义 `iTime`：Adobe 的系统变量文档说明 `$time` 由 Engine 宿主提供，Designer 内不能手动改变该值，而 Player 可用时间轴播放；`iTime` 用于用户手动控制及确定性逐帧 cook。推荐显式选择 `effectiveTime = useManualTime ? iTime : $time`，播放默认系统通道，验证/手动模式选自定义通道；整个迁移 IR 只使用该选择后的时间。记录两条 Get/参数身份、选择器默认值、非零通道验证和每次 cook 的有效时间。Designer 中 `$time` 静止不能作为删去 Player 时间路径的理由；`iTime` 在父图、函数形参、PP `#` 端口的实际读取路径须分别回读/校准（`MORPHING_RETEST_GATES.md`）。详见 `CRATE_AT_DUSK_RETEST_GATES.md`。

**DI4 回测补充**：创建手动 `iTime` 前先按当前版本枚举可用图参数/PP 输入 API、实际端口与父图继承路径，不根据旧脚本硬编码属性 id；创建后回读默认值、参数身份与 `effectiveTime` 选择器。至少比较 t=0 与一个非零手动值，最好用两个不同非零值检查逐帧变化；系统 `$time` 的非零播放必须在能驱动 Engine 时间的宿主验证。只做 t=0 时仅可判静态帧 PASS，手动和 Player 动画均记未验证，不能以 Designer 静态 `$time` 否定系统通道。

#### 7.5.5 GLSL 未初始化分量

源码移植前在 typed IR/控制流图上执行分量级 definite-assignment：声明时未赋值的分量不在 must-defined 集，分支汇合取各路径已定义集合的交集；每次读取用 `check_definite_component_reads` 核对。读到未初始化分量时停止依赖该值的构建，呈现歧义并取得用户或源规格的明确初始化决策；把选择写入目标 IR、构建和独立 oracle，限定等价性结论。`vec3 positionRayon; positionRayon.y=-6.0;` 的 x/z 不得被默认 0 掩盖；Descente 项目中 x=z=0 是用户明确选择，不是 GLSL 通则（DI3）。

### 7.6 调试中间量

只读诊断先用已有输出与日志。确需改图观测且已授权时：
- 单一 Body 返回值可临时读取 While 直接输出；
- 循环状态变量优先通过 While/显式纯值路径离环；若使用 Get，必须验证当前作用域确实读取到循环写入；
- 多状态不必为了“出环”强制向量打包，除非调试目标就是验证 While 直接输出。
任何调试连接都不得把 Exit Cond/Loop Body 内部节点跨分支复用。记录临时节点与连接，结束后恢复原逻辑和输出，检查 I1/I2/I6/I31 及指纹。

**图内诊断抽头按 SOP-0C**：抽头本身可能改变多态节点类型解析；它的源节点身份、通道映射和数值量级必须独立核实。单条抽头读数只形成假设，不能直接形成根因结论。CRATE 项目的错误抽头两次把实际仍存在的立方体误判为“整段缺失”；详见 `CRATE_AT_DUSK_RETEST_GATES.md`。

### 7.7 源码函数边界与 Function Graph 映射

从 HLSL、GLSL、C/C++ 风格代码或其它具有命名函数的源码移植时，源码函数边界属于结构证据，而不是必须被 inline 的实现细节。

1. 先建立源码函数表：函数名、参数、返回类型、调用关系、是否纯函数、读取的外部状态、循环/分支、副作用。
2. 对每个源码函数建立映射决策：`FUNCTION_GRAPH` / `INLINE` / `BLOCKED`。默认优先 `FUNCTION_GRAPH`，尤其是被调用 >=2 次、内部 >=8 个有效计算节点、或本身 >=24 个节点的语义函数。
3. `calc*`、`resolve*`、`get*`、hash/noise、坐标变换、距离/采样辅助等命名不自动决定结果，但应进入高优先级候选。
4. 仅因函数调用一次，不构成必须 inline 的理由；单次调用但具有稳定输入/输出且显著缩小主 PP 的模块可以独立 Function Graph。
5. 调用方局部变量、PP #端口、父图参数必须成为显式形参，不能在函数内部依赖同名 Get 偷读。
6. 源码函数存在 out/inout、多返回、共享可变状态或依赖执行顺序时，先按 A4/A6 验证；不能安全表达则 `BLOCKED` 并说明原因。
7. 映射完成后，主 PP 优先承担 orchestration：准备输入 → 调用语义 Function Graph → 少量状态/组合 → 输出；不得无理由重新展开为数百节点单体。

### 7.8 命令式源码、固定循环展开与 Statement 模式

源码包含赋值、变量重写、for/while body、按顺序发生的状态更新时，默认把**代码语句结构本身**视为需要保留的语义信息，而不是只保留最终数值依赖。

1. 先把源码还原为 statement IR：每条赋值、函数调用结果落地、条件/循环状态更新都有稳定语句身份。
2. 普通赋值 `x = expr` / `x += expr` 以 Set 为 statement root；表达式 `expr` 在 Set 左侧展开。用户选定 Statement/Get 时，Set 接先执行 Sequence `In` 路径，下方同维 `Get(x)` 的消费者接同一输出可达链的后执行 `Last` 路径；回读真实端口，再以非零变化用例验证作用域/名称/类型。缺线先修；拓扑正确仍异常时停下或请求 Sequence-value 例外。**不得把裸 Get 的存在当作写入已生效的证据，也不得复用旧 Set/RHS 跨带。**
3. 同一执行块的有副作用语句由 Sequence 严格按源码顺序自上而下串联。Sequence 不是“仅为了好看”的布局节点，而是顺序语义的可执行载体。
4. 任何循环格式都先按 §7.9.2 降级为结构化 While，并按 §7.9.3 规划其连接；固定次数循环**不再默认展开**。只有满足 §7.9.8 的显式例外（用户明确要求、当前环境已证明引擎阻塞、或交付目标要求无 While）才 unroll，此时按 A10 抽取单轮/子步骤 Function Graph，生成 `iteration 0 -> iteration 1 -> ...` 的重复 statement block，并记录 `LOOP_UNROLL_EXCEPTION:<reason>`。每轮内部仍按源码顺序 Set/Sequence，不生成匿名大型纯 DAG。
5. 循环索引可作为 Function Input/常量输入；重复变量赋值允许同名 Set，但必须通过 I3/I19 明确版本顺序。若为降低歧义使用 SSA 名，报告源码名到 SSA 名的映射。
6. 纯 DAG/Expression 模式默认只适用于真正的无副作用单表达式函数。另一条例外是用户在听取结构取舍后**明确选择 B**，且本图仅为无循环直线计算：记录 `USER_SELECTED_DAG`，独立数值验收，I26 结构保真标有意偏离/WARN 而非 PASS。若当前环境已证明 Set/Sequence 无法安全表达目标，另记 `STRUCTURAL_FALLBACK`。含状态或动态循环时不能因为选了 DAG 布局就取消执行语义，须先停下和用户重新确定可行结构；§7.9 的 While 规则仍有效。
7. 如果 unroll 后主图主要由重复调用组成，优先让 PP 承担 orchestration：输入准备 → Function 实例 → Set 状态 → Sequence；复杂数学留在 Function Graph 内。

### 7.9 循环格式统一降级与 While 连接规划（GLSL/HLSL 权威映射）

本节是循环映射的**唯一权威**：源码中出现的任何循环格式都必须降级为 SD While，并遵守 §7.9.3 的端口级连接规划。§7.4 的验收表是本节的常见行例子集；**§7.9.10 给出推荐的落地连接模板**（角色、端口级连接链、语义约定、几何），新建 While 时默认照此形态实现。

#### 7.9.1 总则

1. **格式无关性**：`for`、`while`、`do-while`、`for(;;)`、嵌套循环、宏/模板/预处理器展开的循环、由 `break`/`continue`/`goto` 构成的控制流，一律映射为结构化 While。不得在 SD 图中保留"类 for"结构，也不得用纯 DAG 链模拟循环语义。
2. **默认不展开**：固定次数、编译期常量次数、已知上界都不是 unroll 理由。unroll 仅在 §7.9.8 的显式例外下允许。
3. **台账先行**：建节点之前先执行 SOP-3A，为每个源码循环建立唯一条目（格式、继续/退出条件、携带状态、每轮临时量、break/continue 目标、预计轮数、上限来源、映射结果）。
4. **结构边界**：除非记录了 §7.9.8 `LOOP_UNROLL_EXCEPTION`，每个源码循环对应一个 While 节点（或其所在 Function Graph 内的一个 While）；一轮迭代 = loop 闭包的一次执行，而不是一批复制节点（W14）。
5. **禁止跨格式等价替换**：把 `do-while` 当 `while`（丢首轮）、把 `for` 的 continue 当普通跳转（丢增量）、用 ifelse 分支假循环——这些都属语义错误，不是风格差异。
6. 循环体大小与是否函数化按 §4.5/A10 处理；**函数化不改变"外层仍是 While"这一结论**。

#### 7.9.2 格式 → While 映射表

| 源码格式 | Init | Exit Cond（True 停止） | Loop Body | 必查 |
|---|---|---|---|---|
| `while (C) { B }` | 携带量初值 Set（Sequence 组织） | `not C`（显式取反） | B 的语句序列（Sequence 根） | 继续条件必须取反；零轮语义 |
| `for (i=a; C; S) { B }` | `Set i=a` + 其它携带量 | `not C` | B 的语句 + 尾部 `Set i=S` | 增量必须在 Body 尾部且属于 Body Sequence；含 `continue` 时仍要执行 S（§7.9.4） |
| `for (;;) { B }`（无退出条件） | 携带量初值 | 由 break 标志或状态导出（§7.9.4） | B | 无 break 即无退出条件：必须给有限上限并记录来源（§7.9.7） |
| `do { B } while (C);` | 携带量初值 + `Set firstPass=true`（或 Init 内复制一轮 B） | `not firstPass and not C` | B + 尾部 `Set firstPass=false` 与状态更新 | 必须至少执行一轮；不得退化为普通 while（§7.9.5） |
| 循环体内 `break` | 携带量初值 + `Set brk=false` | `not C or brk` | break 处 `Set brk=true`；其后的语句包进 ifelse | break 之后语句不得继续执行；嵌套时只影响最内层 |
| 循环体内 `continue` | 携带量初值 + 每轮按源码语义复位标志 | 不变 | `Set cont=true`；其余语句包进 `ifelse(not cont, ...)` | `for` 的 continue 仍必须执行增量（§7.9.4） |
| 非 1 步长 / 递减 / 浮点计数 | `Set i=a` | `not C`（按真实比较方向） | 尾部 `Set i=i+S` | 步长方向、浮点比较、预计轮数（§7.4 示例表） |
| 嵌套循环 | 外层 Init；内层 While 作为外层 Body 中一条语句 | 各层各自独立 | 内层 While 属于外层 Body 闭包 | 每层 branch-private；内层结果按 §7.9.6 读取 |
| 循环内早退 / 多出口 | 每个出口一个布尔出口标志 | `not C or brk1 or brk2 ...` | 各出口处 Set 对应标志 | 不同出口不得复用同一同名状态导致覆盖歧义（I3/I19） |
| 空体 `for(;i<N;i++);` | 初值 | `not C` | 仅增量 Set | 空体仍是合法 While；不得删除该循环 |
| 宏/模板/预处理器生成的循环 | 按展开后的语法结构映射 | 同 for/while | 同 for/while | 以展开后语义为准，保留属性不变 |

#### 7.9.3 While 连接规划（端口级）

端口 id 来自当前实例回读。16.0.3 实测定义 `sbs::function::while`：输入 `init`、`cond`、`loop`、`__constant__`；输出 `unique_filter_output`。**端口名固定，类型多态**（实测同一实例 `init`/`cond` 为 bool、`loop` 与输出为 float），因此类型必须按实例核实，不能按定义默认值推断（对照 N4/§11.6）。

| 端口 | 语义 | 规划要求 |
|---|---|---|
| `init` | 第一次迭代前执行一次 | 必须是合法单语句或 Sequence 根；初始化所有携带状态；不读取尚未初始化的循环自身状态；不放"每轮才该执行"的语句 |
| `cond` | 每轮先计算的**退出条件** bool | 必须是纯判定闭包（比较/布尔组合），不写状态；`True` 停止、`False` 进入 loop；移植继续条件必须取反；不得与 loop 闭包共享节点 |
| `loop` | 每轮迭代体 | 单语句或 **Sequence 根**；多语句/read-after-write 必须用 Sequence 表达源码顺序；尾部放增量 Set |
| `__constant__` | Max iterations（int1） | 默认使用有限安全上限且来源可解释（静态界/推导界/保守帽，§7.9.7）；`-1` 是 Adobe 支持的无限上限模式，仅按 W7 的可证明退出界/用户明确要求例外使用 |
| `unique_filter_output` | 最后一次 Loop Body 的结果 | 只有需要"最后一轮值"时才作为该语句 RHS；持久状态仍按 W5 在环后用新 Get 读取 |

连接规划固定步骤：

1. 回读目标实例的真实端口 id 与类型；除端口名外不假设任何定义默认值。
2. 先创建 `init`/`cond`/`loop` 三个闭包内的全部节点与 Function 实例，写初始坐标，登记进 IR/布局表（N22/I28）。
3. 闭包内部先按源码顺序完成语句级连线（Set/value、Sequence 链），再连到 While 的三个输入端口。
4. `cond` 与 `loop` 闭包按 branch-private 处理：同一节点实例（常量、Get、运算、Function 实例）不得同时连接 `cond`、`loop` 与图中其它分支；需要相同值时新建独立节点（W4）。
5. 环外读取循环状态：先证明 While 已完整执行，再优先使用显式返回/纯值路径；若使用 Get 则必须验证当前作用域确实读到该写入；禁止把 loop 闭包内部节点直接拉出环外（W5/I6/I8/I35）。
6. 全部连线完成后断言：`init`、`cond`、`loop` 各有**实际源连接**；`cond` 上游末端类型为 bool；`__constant__` 已按 W7 设置（默认有限值；合法例外可为 `-1`）；输出在需要时有真实消费者（I34/N22）。
7. 嵌套循环对每一级重复步骤 1–6；内层 While 作为外层 loop 闭包中的一条语句参与外层 Sequence 顺序。
8. 布局按 L7：While 作为 statement root 或表达式子节点，`init`/`cond`/`loop` 三个子区域在其左侧，默认自上而下 `init → cond → loop`；`__constant__` 是节点属性而非连线，不产生额外子树。

#### 7.9.4 break / continue / 多出口降级

`break` 与 `continue` 是控制流而不是赋值；SD While 没有原生 break/continue 端口，必须用**状态标志 + 条件包装**表达：

1. **break**：Init 建立出口标志（每轮开始或按源码语义复位），`Exit Cond = not C or brk`；break 位置 `Set brk=true`；break 之后的语句必须包进 `ifelse(not brk, ...)`，不得让它们继续执行。
2. **continue**：continue 之后的剩余语句包进 `ifelse(not cont, ...)`，并在 continue 处 `Set cont=true`；标志必须在每轮按源码语义复位（通常在 Body 头部或条件块前）。
3. **`for` 中的 continue 必须保留增量**：源码 `for(;;S){ ...; if (x) continue; ... }` 在 continue 时仍会执行 S。因此增量 Set 必须位于 Body Sequence 尾部，且在 `ifelse(not cont, ...)` 包装**之外**，否则计数器不更新会导致死循环。
4. **嵌套循环**：break/continue 只作用于最内层循环；标志名按层区分，且各层标志各自 branch-private。
5. **`goto`/异常控制流**：只有在能还原为等价的标志 + 条件包装时才降级；无法等价时记录 `LOOP_LOWERING_BLOCKED:<reason>`，不得静默改写语义。
6. 多出口循环为每个出口维护独立标志，并入 Exit Cond 的或组合；不要用一个同名 Set 复用于不同出口（I3/I19）。

**DI8 有证明的首句 break 特例**：若 `if (B) break;` 是该 While Body 第一条可执行动作、`B` 无副作用且仅读与本轮 Body 入口完全相同的状态、此前没有改变状态或可观察结果的计算、break 目标是当前这一层循环，则可把 `B` 并入 `Exit Cond` 并记 `BREAK_HOISTED_TO_EXIT_COND:<source span/proof>`。使用 `can_hoist_leading_break` 作静态门，并用边界/退出轮次 oracle 验证。break 前赋值、条件中副作用、嵌套循环 break 或入口状态不一致均不满足；仍走上面的标志与 `ifelse` 路径。该特例是等价优化，不改变“一源循环一 While”（§7.9.2）。

#### 7.9.5 do-while 降级

`do { B } while (C);` 至少执行一次，不能直接写成 `while (C)`：

- **推荐**：Init 建立 `firstPass=true`（以及其它携带量初值），`Exit Cond = not firstPass and not C`，Loop Body 执行 B 并在尾部 `Set firstPass=false`。B 只建一份，首轮必然进入。
- **备选**：把 B 复制进 Init 一次，`Exit Cond = not C`，Body 只放第 2 轮及以后的 B。仅在 B 很小、或首轮与后续轮确有结构差异（例如首轮不做某些更新）时使用，并记录复制关系。
- 两种方式都必须记录"零轮不可达"这一语义差异（对照 W6/D12）。
- do-while 与 `break`/`continue` 组合时，标志复位与增量规则同 §7.9.4。

#### 7.9.6 嵌套与多循环

1. 每一级循环都需要自己的 Init / Exit Cond / Body 与自己的 branch-private 闭包；不得把外层 Get/常量复用为内层 Cond/Body 的输入。
2. 内层循环结果在内层 While 完整执行后优先由显式返回/纯值路径读取；若用 Get 则需当前作用域验证；若外层 Body 只需要内层最后一轮值，也可使用内层 While 的输出。
3. 两个循环读写同名状态时，必须用 Sequence 明确整段 loop A 完成后再执行 loop B；不得依赖画布位置或节点坐标（W5）。
4. 每一级都单独给出 Max iterations，并逐级记录预计轮数；必要时给出嵌套总预算。

#### 7.9.7 Max iterations 推导

| 源码情形 | `__constant__` 取值 | 说明 |
|---|---|---|
| 静态常量界 `i<32`，步长 1 | 32（或该界的可证明上界） | 与 Exit Cond 一致，先到者停止 |
| 非 1 步长 / 浮点界 | `ceil((bound - start)/step)` 的可证明上界 | 例如 `i<10` 步长 1.5 → 上界 7（§7.4） |
| 由外部参数决定的动态界 | 按分辨率/采样预算推导的安全帽 | 帽值必须 ≥ 源码可证明的最大轮数，并在报告中说明来源 |
| `for(;;)` / `while(true)` + break | 必须给出可证明上界；无法证明时给保守帽并标未验证 | 不允许因为"有 break"就写 `-1` |
| 依赖数据收敛（raymarch 等） | 按视觉/精度预算给出保守上限（历史案例 32/64/128 等） | 记录收敛判据与上限的关系 |
| `Max iterations = -1` | 仅当退出条件有可证明界限或用户明确要求 | 官方警告无限循环会让 Designer 无响应（W7） |

#### 7.9.8 例外：允许 unroll 的条件

While 是默认且必须的映射目标。只有满足以下任一条件才允许 unroll，并且必须记录一行 `LOOP_UNROLL_EXCEPTION:<reason>`，写明源码位置、原循环格式、理由、轮数与替代结构：

1. 用户在当前会话中明确要求展开（例如要求纯 DAG，或目标版本/平台不支持循环）；
2. 已在**当前环境**用最小复现证明该循环结构存在引擎阻塞（SOP-0A），且无法通过调整连接规划绕开；
3. 交付目标明确要求无 While 的静态图（例如导出到不支持循环的消费端）。
4. **目标类型系统无法表示该循环的迭代载体**，例如只有固定次数 `A[i]=f(i)` 的数组下标赋值，而当前 Function Graph 无可验证数组/动态下标载体；记录 `LOOP_UNROLL_EXCEPTION:TYPE_SYSTEM_NO_ARRAY`、数组证据与每轮显式映射。这是有限例外，不适用于通常可用标量/向量携带的计算循环。

unroll 例外下仍然必须：

- 保持命令式源码结构：每轮是独立 statement block，按源码顺序 Set/Sequence（N18/I26/§7.8），不得退化为匿名纯 DAG；
- 按最大轮数评估 Architecture（A10/A11），必要时把单轮体抽成 Function Graph；
- 在报告中把该图标为存在 `LOOP_UNROLL_EXCEPTION`，且不得声称"已完全遵循 While 循环规范"。

#### 7.9.9 验收清单

| 检查 | 要求 |
|---|---|
| I32 | 每个源码循环在台账中有唯一条目并映射到确定 While 或已记录例外 |
| I33 | 格式降级正确：`cond` 已取反、do-while 首轮保留、break/continue 标志与包装正确、`for` 增量在 continue 时仍执行 |
| I34 | 连接规划完整：三输入有实际源、`cond` 为 bool 退出条件、`__constant__` 默认有限且可解释（或按 W7 合法使用 `-1`）、端口 id/类型来自回读 |
| I35 | 分支隔离：`cond`/`loop` 闭包无跨分支共享节点；环外状态用新 Get 读取 |
| I36 | 模板一致性：按 §7.9.10 形态落地（Init 只初值、cond 只读、tail Get 独立、常量私有、三子区域完整），偏离有记录；模板前置满足 |
| 报告 | §9「循环降级与连接规划」小节完整，含模板一致性列与例外理由 |

#### 7.9.10 标准 While 连接模板（推荐连接方式，模板文件实测）

**来源与性质**：本模板从实测模板文件 `loop whlie.sbs`（sha256 `30f259128cff08a00eb159a9160b2965d07e877ddf08cee5e2964d556942f64f`，work copy `E:\SD_AI\sdtext\loop_whlie.sbs`；SD 16.0.3 只读回读，见 §11.6）提取。它是**推荐的落地连接形态**，不是"唯一合法结构"：§7.9.3 是必须满足的规则，本节给出满足这些规则的推荐骨架、节点角色与几何。因源码语义（多出口、需要保留多份状态等）必须偏离时，按 §7.9.3 逐项说明并记录，不得因为"连线方便"而偏离。

**模板使用前置（缺失任一项则不得声称该 While 可交付）**

1. 图必须有最终输出节点（`getOutputNodes()` 非空；PP 内部图需 `setOutputNode(node, True)`），且 While 结果所在语句确实汇入输出（I28）。
2. 不得留下无消费者、也无同名 Set/端口/父参数解析路径的 Get（I1/I2）。
3. 若该 PP 要在复合图中交出结果，PP 节点自身必须接到目标 output（模板文件中 PP 未接线、内部图无输出，属该 demo 的缺陷，不是模板规则）。

**节点角色清单**

| 角色 | 定义 | 关键端口 | 职责 |
|---|---|---|---|
| Loop | `while` | `init`/`cond`/`loop`/`__constant__` | 控制结构本体；`__constant__` 默认写有限上限，`-1` 仅按 W7 例外 |
| Init 主干 | `sequence` | `seqin` → `seqlast` | 让 Init 内多条初始化语句有确定顺序 |
| Init 语句 | `set` | `value`、`__constant__`(名) | 每个携带量初始化一次；RHS 只用常量或环外只读量 |
| Cond 判定 | 比较类（`lr`/`lreq`/`gt`/`gteq`/`eq`）及布尔组合 | `a` / `b` … | 输出 bool 的**退出条件**；只读状态、不写状态 |
| Cond 读取 | `get_floatN` | `__constant__`(名) | 读取携带量当前版本；与 loop 闭包不共用实例 |
| Body 主干 | `sequence`（可嵌套） | `seqin` → `seqlast` | 表达每轮语句顺序；嵌套层级对应语句块层级 |
| Body 语句 | `set` | `value`、`__constant__`(名) | 每轮更新；RHS 起手是该变量的**新建 Get** |
| Tail 读取 | `get_floatN` | `__constant__`(名) | 放在 Body 主干 `seqlast`，给出"本轮结束后的状态"作为 While 直接输出 |

**端口级连接链（模板实测形态）**

```text
while.init        <- init_seq.unique_filter_output
while.cond        <- cmp.unique_filter_output              # bool
while.loop        <- body_seq.unique_filter_output
init_seq.seqin    <- set_d_init.unique_filter_output
init_seq.seqlast  <- set_a_init.unique_filter_output
set_d_init.value  <- const(初值)                            # Init 的 RHS 不带 Get
set_a_init.value  <- const(初值)
cmp.a             <- const(边界)                            # 边界常量接 a
cmp.b             <- get_a_cond.unique_filter_output        # 活状态接 b
body_seq.seqin    <- inner_seq.unique_filter_output
body_seq.seqlast  <- get_d_tail.unique_filter_output        # tail = 本轮更新后的状态
inner_seq.seqin   <- set_d_body.unique_filter_output
inner_seq.seqlast <- set_a_body.unique_filter_output
set_d_body.value  <- sub(get_d_rhs, const(步长))            # RHS 起手新建 Get
set_a_body.value  <- add(get_a_rhs, const(步长))
```

模板实例语义（推演）：`d` 由 100 递减、`a` 由 2 递增，`cond = 边界(6.0) < a` → **Body 执行 5 轮**，终态 `a=7`、`d=95`，`__constant__ = 32` 不触发。

**语义约定（模板核心，新建 While 默认照搬）**

1. **Init 只放初值**：每个携带量在 Init 恰好 Set 一次；RHS 不含对循环自身状态的 Get（否则读到未初始化版本）。
2. **cond 只读不写**：cond 闭包不得含 `set`；cond 的 Get 与 loop 闭包的 Get 必须是**不同节点实例**。
3. **cond 方向**：16.0.3 定义实测 `lr`=A&lt;B、`lreq`=A≤B、`gt`=A&gt;B、`gteq`=A≥B。模板把**边界放 a、活状态放 b**，使 `lr` 直接读作"边界 < 计数 → 停止"。方向必须来自源码继续条件的取反（§7.4/I15），不得由写法习惯决定；模板实例等价于"计数 ≤ 边界时继续"。
4. **Body 顺序 = 源码顺序**：多语句用可嵌套 Sequence 主干自上而下表达；`set.value` 起手用**新建 Get** 读该变量当前版本；同一 block 内再次读同一变量时**再新建一个 Get**（模板为 tail 单独建了第二个 `Get('d')`，而不是复用 `set.value` 的上游 Get）。
5. **Tail 约定**：Body 主干 `seqlast` 放一个读取"本轮结束后状态"的新建 Get，作为 While 直接输出；需要该值时由消费语句接住，不需要时必须明确记录其为未使用（模板文件中它未接消费者——属该 demo 缺陷，不属于模板规则）。
6. **常量私有**：同一数值出现在不同语句/分支时使用独立常量节点（模板中 `add` 与 `sub` 各自持有 `1.0`），避免跨分支共享（W4/I35）。
7. **上限独立**：`__constant__` 单独给有限值并记录来源（§7.9.7）；模板实例的 32 未记录来源，记为 WARN。

**几何模板（L7 落地形态，观测值，非硬性数值）**

| 元素 | 相对 While 的位置（模板实测） |
|---|---|
| cond 子树 | 与 While **同一行**，整体在其左侧（dx≈−224） |
| cond 叶子 | 再向左一列（dx≈−352），`a`/`b` 兄弟上下分列（±96） |
| Init 块 | While 行**上方**（dy≈−224），自带右侧局部 Sequence 主干 |
| Loop 块 | cond 行**下方**（dy≈+864），自带右侧局部 Sequence 主干 |
| Body 语句根 | 与所属局部 Sequence **同一行**，在其左侧（dx≈−128） |
| 表达式树 | 继续向左展开，兄弟输入上下分列；行步 ≥192 且吸附 32 |
| 网格 | 16 相位网格（模板全部坐标均为 16 的倍数） |

**建图顺序（与 SOP-3A 配合）**

1. 按 §7.9.2 写出 Init/Cond/Body 语句清单，按 §7.9.7 定 `__constant__`。
2. 一次性创建三个闭包内的全部节点与实例，各写初始坐标，登记 IR/布局表（N22/I28）。
3. 先连**块内**语句级连线：Init 主干、Body 局部/嵌套主干、各 `set.value`、cond 判定子树、tail Get。
4. 再连三个输入：`init`/`cond`/`loop`。
5. 回读断言：三输入均有源；`cond` 末端 bool；cond 闭包无 `set`；cond 与 loop 的 Get 实例不同；Init 覆盖全部携带量；`__constant__` 按 W7 合规；闭包内节点无跨分支消费者（I34/I35）。
6. 最后处理环外读取：证明 While 已执行 → 使用显式返回/纯值路径；只有经验证的作用域才允许 Get。不要复用 Body 内部节点。

**常见偏离与对应诊断**：tail Get 复用 `set.value` 上游 Get → I31/N23/D24；cond 复用 Body 的 Get → I35/D25；Init 漏初值 → I7/D3；While 有值却无消费者 → I8/I28/D21；为压缩高度打散三个子区域 → L7/I13b。

若 loop 体已按 A10 函数化（Body/Cond/Init 抽成 Function Graph），按 **§7.9.11** 处理跨界状态、`tail Get` 与实例分支隔离。

#### 7.9.11 循环体函数化与 While 连接（与 §7.10 / SOP-5B 配合）

循环体函数化**不改变"外层是结构化 While"**（A10/§7.9.1）。落地规则：

| 项 | 要求 |
|---|---|
| 外层结构 | 仍是 `while`；`loop` 闭包的语句根可以是**一个 Function 实例**（单语句），也可以是含实例的 `Sequence` 根 |
| 跨界状态（必须显式） | Body 函数更新的每个携带量必须**同时是该函数的形参（入）与返回（出）**；调用方拿到返回后 `Set` 回变量，立即值由该 statement Sequence output 承接。后续 Get 仅限已验证同作用域读取。**不得依赖"函数内部 Set 名能被调用方 Get 到"**——一律按**函数局部**处理。 |
| Body 返回与 tail Get | Body 主干 `seqlast` 放"本轮结束后状态"：可消费 Body 实例输出，或在消费该输出的 `Set` 之后新建 `Get`；两者都必须与 `set.value` 的上游 Get 是不同实例（§7.9.10 第 4/5 条） |
| Cond 函数化 | 允许：`cond` 根 = 返回 bool 的判定函数实例。该实例必须与 `loop` 的实例是**不同节点**（即使调用同一函数），保持 branch-private（W4/I35） |
| Init 函数化 | 允许：Init 函数返回初值元组，调用方逐个 `Set`；`init` 闭包不得读取循环自身状态 |
| 逐轮变化的量 | 迭代索引、每轮变化的常量按 A3 提升为形参，不得固化在函数内部 |
| 上限 | 仍按 §7.9.7 单独推导 `__constant__`；函数化不改变上限要求 |
| 纯计算 body | Body 无内部 Set/Sequence 时按 Expression 模式实现为纯函数；有内部语句时按 Statement 模式保留 Set/Sequence，但**新状态仍必须通过返回显式交出** |
| 分支隔离 | Body/Cond 实例、其形参常量与 tail Get 均属该分支私有，不得与其它分支或环外共享实例（W4/I35/I36） |
| 装配顺序 | 按 SOP-5B 第 5–7 步：Body/Cond 函数先建成并单独验证（I1/I2/I9/I10/I23）→ 再建实例并回读端口（I11）→ 最后按 §7.9.10 模板连 `init`/`cond`/`loop` 并断言三输入有源（I34）。函数的计划坐标在创建前已由布局计划确定（L16），实例同样创建即落位 |

### 7.10 语句树连接方式与跨度/节点预算（Set → Statement Sequence → Value Spine → Pure Terminal）

来源：本节数值来自 16.0.3 对参考包 `OKColor_LCH.sbs` 的**只读**回读（§11.7）。该包 = 1 张复合图 + 15 张 Function Graph，按"语句 + 表达式树"组织：变量以 `Set` 落地并大量使用带内 `Get`，而不是把旧上游表达式/Set-value 拉成长线。该布局语料只说明图形结构；执行正确性另须按 RS2 检查 Sequence 两分支及输出可达性。

#### 7.10.1 总则

1. **变量身份由 Set 建立**：凡是后续语句要读取的值，必须 `Set` 到一个**名字**，并锚定在 `Sequence` 主干上（§7.2/W1）。
2. **读取须进入后执行分支**：用户选定的 Statement 图，下方语句在本带新建同类型 `Get(name)`；实际边须证明 `Set→Sequence.In` 为先执行路径，`Get→下方表达式→Sequence.Last` 为同一可达链的后执行路径。Get 无 Sequence 输入口，不能把上下排布误当连线。随后以当前运行时非零变化用例证明同作用域、名称和维度。缺连线先修复；拓扑正确仍失败才阻断/探针或请求显式 Sequence-value 例外。任何情况下不得复用旧 Set/RHS 输出跨带。
3. **禁止跨带直连**：把上方语句的表达式节点、Set 输出或 RHS 节点直接连到下方语句带，属于禁止的 DAC/DAG 式长连线（N26/I37）。
4. **结构不因跨带而改变**：树形展开 = "每语句一棵私有表达式树 + 右侧 Sequence 主干"，不是全局二维压缩 DAG（§10 L4–L8）。

**IR/回读门 `RS_GET_SEQUENCE_TOPOLOGY`**：每条跨语句读记录 `set_node`、`get_node`、作为读写分界的 `sequence_node`、`output_nodes`，以及真实 `wiring_edges`（`source`、`target`、`target_port`）。从该 Sequence 的 `In` 端向上游必须能找到生产 Set；从 `Last` 端向上游必须能找到 Get 消费树，且 Get 不得同时落入先执行 `In` 分支；从 Sequence 向下游必须能到已标记输出。链中间可经过其他 Sequence/表达式节点。`scripts/runtime_semantics.py::validate_ir` 有逐边检查；缺真实边快照报 `RS_GET_EDGE_AUDIT_MISSING`，布尔摘要、坐标或同名均不能替代。随后独立核对名称、维度、scope 与非零变化值。

#### 7.10.2 允许与禁止的连线

| 连线类型 | 判定 | 说明 |
|---|---|---|
| 带内表达式边（父→子，同语句带） | 允许 | 参考实测 dy 中位 0；允许 ≤1 行步（≤288） |
| 语句根 → 其 Sequence | 必须且同行 | §11.7 参考实测 dy 中位 8/p75 18 |
| Sequence → Sequence（主干串联/嵌套） | 允许 | 纵向主干，参考 87 条 |
| 控制块结构边（`ifelse` condition/ifpath/elsepath、`while` init/cond/loop 等） | 允许 | 控制块自成子树（§7.9.10） |
| Function 实例 → 调用点输入 | 允许 | 实例与其形参同带 |
| **跨语句带直连**（上方表达式/Set 输出拉到下方消费带） | **禁止** | 下方消费带建同维 `Get(name)`，让其消费者接入同一输出可达 Sequence 链的后执行 `Last` 分支，先修缺失的路径，再验证当前作用域数值；Sequence-value 路径仅作获准且数值验证的例外 |
| Get 距其同名 Set 很远（Get 与 Set 不同带） | 允许 | **远距离本身不是问题，长连线才是问题**；但 Get 消费路径必须并入该 Set 之后的 Sequence `Last` 分支，且整条链通往输出 |
| 共享非叶 DAG 节点跨带复用 | 仅 L8 登记例外 | 参考中跨 1 行步以上的边仅 7.8%，且集中于控制块链与 Set→Sequence 锚定 |

#### 7.10.3 几何（实测，相对网格吸附）

| 项 | 实测 | 采用 |
|---|---|---|
| 列步（X，树每层） | 中位 160、p90 512、p99 1069、max 1553 | 128/160/192/224；单跳 ≤3 列（≤480）为正常，>7 列须改 Get 或拆语句 |
| 行步（Y，语句带） | 中位 224、p75 288、p90 416、max 704 | 192/224/288 为主，吸附 32 |
| 带内 dy | 中位 0、p90 256 | 0 优先，≤1 行步可接受 |
| 语句根与其 Sequence 同行 | 中位 8、p75 18 | 必须同行（p90 544 属需修形态） |
| 网格 | 全部坐标为 16 的倍数 | 相对原点 + 32 吸附 |
| 语句带高度 | 由私有树高度决定 | 不同语句带的私有子树禁止交错混排（L5/L6） |

#### 7.10.4 跨度预算（归一化，替代绝对高度墙）

- `Y_per_statement = spanY / 语句带数`：`≤320` PASS（实测 p75 = 318）；`≤512` WARN；`>512` 需 `SPAN_JUSTIFICATION:<reason>`，否则 FAIL。
- `X_per_level = spanX / 最大表达式深度`（深度 = DAG 最长路径）：`≤224` PASS（实测中位 ≈150）；`≤384` WARN；`>384` 需 `SPAN_JUSTIFICATION`。
- **绝对跨度只作报告标志**：`spanY > 12000` 或 `spanX > 4800` 时要求在报告中写出语句带数与最大深度，说明属结构规模而非排布缺陷；不作为 FAIL 依据（参考实测 `spanY` 11419/43 带、`spanX` 4640/深度 15 均为可接受形态）。
- 禁止用"压缩行距/交错语句带/扩大画布"制造指标达标（I37/I38）。

#### 7.10.5 节点数量预算（重写）

- **触发 Architecture Pass**：图节点数 `≥400`；Statement 模式 `节点数 ≥192 且 nodes_per_statement > 16`；或单次语义区域 `≥32` 有效计算节点。纯 Expression Function Graph（包括用户选 A 时的纯函数）不套用 `nodes_per_statement` 触发器，而看节点数、最大表达式深度、每层宽度/扇出与 `X_per_level`；其 Statement 比值记 `N/A(expression)`，不得为降比值强加 Set/Sequence。
- **单图数量区间与函数拆分联动**：`400–1199` 先完成带候选投影的 Architecture Pass，数量本身不导致 FAIL；`1200–1500` 必须有高节点复核记录（拆分前/后估算与实际、逐候选安全性/取舍、函数自身与首调用点数值验证、节点回读/编辑响应、cook、布局），状态至少 WARN。高节点复核不是布尔勾选：存在安全且减量的候选时先执行已授权抽取，否则记录 `STRUCTURAL_EXCEPTION`；无安全候选则写清 IR 范围和阻断原因。`>1500` 不作为通常的新建单体交付，应先拆分或请用户明确批准超预算例外，且例外不能掩盖验证失败。每次抽取后调用方和新函数分别重新计数/判预算，不能把超预算转移到函数图。`nodes_per_statement > 24` 且存在安全抽取点（或可拆语句带）仍单独触发结构整改/例外。
- **实测包络**：15 张函数图 10–368 节点；最大 368 节点/43 语句带 → `nodes_per_statement` 8.6；全包 1058 节点、95 Sequence、109 Set、198 Get；`nodes_per_statement` 典型 5.8–13.5。
- **节点数本身不等于引擎错误**：368 节点/43 语句带是历史实测形态，不是现行上限；仅 Statement 模式的 `nodes_per_statement > 16` 提示审查展开/复用，`>24` 且可安全拆分时须处理。所有纯 Expression 图按其源码/布局模式解释，不凭 Statement 指标自动补 Set/Sequence；大 DAG 的每层宽度/扇出与复用候选仍需 Architecture 审查。

#### 7.10.6 检查方法（只读统计模板）

```python
def pct(v, q):
    if not v:
        return 0
    s = sorted(v)
    return s[min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))]

pos, kind = {}, {}
for n in graph.getNodes():
    p = n.getPosition()
    pos[n.getIdentifier()] = (p.x, p.y)
    kind[n.getIdentifier()] = defid(n)

dys, dxs, cross = [], [], []
for n in graph.getNodes():
    for prop in n.getProperties(C.Input):
        for c in (n.getPropertyConnections(prop) or []):
            s = c.getInputPropertyNode().getIdentifier()
            if s not in pos:
                continue
            ddy = abs(pos[n.getIdentifier()][1] - pos[s][1])
            ddx = abs(pos[n.getIdentifier()][0] - pos[s][0])
            dys.append(ddy)
            dxs.append(ddx)
            if ddy > 288:
                cross.append((ddy, kind[s], kind[n.getIdentifier()]))

ys = [v[1] for v in pos.values()]
xs = [v[0] for v in pos.values()]
spanY, spanX = max(ys) - min(ys), max(xs) - min(xs)
stats = {
    'edges': len(dys), 'dy_med': pct(dys, .5), 'dy_p90': pct(dys, .9), 'dy_max': max(dys or [0]),
    'dx_med': pct(dxs, .5), 'dx_p90': pct(dxs, .9), 'cross_band': len(cross),
    'spanY': spanY, 'spanX': spanX,
    'Y_per_statement': spanY / max(1, band_count),
    'X_per_level': spanX / max(1, max_expression_depth),
    'nodes_per_statement': len(pos) / max(1, band_count),
}
print(stats)
print('CROSS_BAND_SAMPLE', cross[:20])
```

`band_count`（语句带数）与 `max_expression_depth`（DAG 最长路径）来自 SOP-2 的 IR/Sequence 展开结果；本模板只做统计，判定按 §7.10.2/§7.10.4/§7.10.5。

#### 7.10.7 与可维护性的关系

节点数与跨度都**不是绝对墙**：真正的可维护性信号是**结构比**——`nodes_per_statement`、`Y_per_statement`、`X_per_level` 与跨带长连线数量。结构比正常而绝对跨度大 = 语句多/树深，属正常；结构比异常 = DAG 膨胀或排布混乱，必须补结构（Set/Sequence/Get）或抽取 Function Graph，而不是压缩几何或交错子树。


### 7.11 真实项目数值门与导出门

`REAL_PROJECT_VALIDATION.md` 是本节的详细证据与操作边界。新建函数必须在被上层实例调用前经过单函数非退化用例与独立 oracle 检验；结构审计、`setOutputNode` 调用成功、`graph.compute()` 和导出成功均不能替代数值检验。`Morphing Abstract_text` 的结构审计 0 错误，但单元数值只通过 3/20、图像 0/5，故不得把底层函数仅凭结构 PASS 提升为可供调用的已验证模块。

1. IR 静态门：每个 `Get` 与可达 `Set`/formal 的名字、维度、作用域和执行顺序匹配；跨边界数据均为显式 formal 且调用点实际连接。Designer 16.0.3 的 `get_floatN` 维度错读可静默为 0，多态端口类型回读不足以排除此错。逐函数 oracle 前执行 I42/I43/I44、广播维度与源码分支覆盖检查；`scripts/project_validation.py` 接受回读后的作用域解析快照，但静态 PASS 不是原生数值 PASS。
2. 输出门：`setOutputNode` 后确认 `getOutputNodes()` 非空，确认输出根真实取到数据，并以区分零值/常量值的用例验证。16.0.3 的 PP 内图经 Morphing 与 Sun shower 两次回测：float1/float4 根可标，float2/float3 根标记后 `getOutputNodes()==[]` 且输出黑；诊断向量经 float4 载体/独立标量通道，未知版本先测。普通 Function Graph 不承受这一 PP 限制；但 CRATE 16.0.3 中 `while` 作为普通 Function marked root 虽列在 `getOutputNodes()`，首调用点仍全 0，改为纯算子组装根后恢复。`while/sequence/set` 直接作根默认不交付，偏离须当前会话最小探针和首调用点数值证据；不宣称所有结构节点在所有版本必定失败。
3. PP 门：先确认 image source → PP `input` 与 PP → composition output 的实际连线，再做内部图/导出。该顺序是低成本检查；`rain_text1` 的 `{}` 响应未隔离出确切原因，不能宣称前置连接是 SDK 硬要求。
4. 尺寸门：按当前包的继承模式与值读回确定实际尺寸，再从导出文件头核对宽高。两项目有效设置方式不同，不指定全局固定继承组合。8192² 意外导出不能当作 1024² 验证结果。
5. 坐标与比较门：分别记录**每个写入器**的文件行序、解码视图、图像顶部映射及源码坐标原点；用不对称 `$pos.y` ramp/分支 marker 和独立解析的一个 world-ray 像素确定方向，不能由较低 MAD 选择翻转。跨文件逐行比较必须先归一为同一视图并附 `top_rows`/`file_rows` 标签。Sun shower 的 SD BMP 与自制 oracle BMP 都声明正高度，但文件首行对应的图像位置不同；近镜像湖面甚至让**错误**翻转的 MAD 更低。按真实输出尺寸做 1:1 对照，报告两个方向的 MAD、RMSE、偏差、尾部分位/最大值及时间/参数。`rain_text1` 的 `uv.y = 0.5 - $pos.y` 是 Shadertoy 底原点迁移的实例，不是对所有 shader 的自动翻转规则。
6. 工具状态门：MCP 空响应或超时等于结果未知；先查日志、阶段标记与只读图状态再决定是否重试，不推断“没有修改”。隔离的跨包函数探针和端到端结果冲突时分别报告，不把任一项扩展为通用结论。
7. 参考图门：每个用于**验收**的 oracle 产物必须有同会话可复现的生成命令、源码与产物哈希、解码视图、分辨率和已覆盖源码 branch 清单；单位期望表优先当次从活模块现算，缓存表还须与其生成模块的源码哈希及表文件哈希同时匹配。源码已改而表未重生时只可 cross-check，不能据旧表判 FAIL/PASS。读模式实现/说明，不凭 `full`/`water` 等名称猜其覆盖范围。不能再生成的旧文件只能作 cross-check。Sun shower 中 `full` 漏折射、`water` 是法线编码，后续 `image` 才恢复完整分支；旧的水面结论须随参考源纠正而重判。小于数像素的特征不可作低分辨率方向地标。
8. 组装图门：逐源码 section/branch 标记 `PORTED`/`OMITTED`/`BLOCKED`，从最终输出逆向验证应生效的因子皆可达（如 vignette，不能让占位常量替代已算因子）；除逐函数单元测试，还要看真实调用域的边界用例与成图后各语义区域的**有符号**误差。子函数单测通过但成图退化时，记录 hold 理由与解除所需的具体测量；已知缺失分支的区域先列预期差异，不嫁祸于通过单测的函数。图超过预算仍需报结构 FAIL，原生 cook 成功不豁免。
9. 精度门：每项数值 oracle 记录 `encoding`、`enc`/`dec` 公式、BMP 位深、解码后一 LSB 容差、下游量化台阶及比值。8-bit direct = `1/255`，仿射 `enc=0.5+v/(2S)` = `2S/255`；若该容差已接近下游台阶，单函数 PASS 不能解释成图“一台阶”残差。被测值严格在 `(0,1)` 且离端点留出量化余量时优先 direct；零/一边界另测，其它值用不裁切仿射并标精度限制。辅助 `check_probe_precision` 的台阶四分之一界是保守归因规则，不是 Designer 引擎精度定律。
10. **RGBA 导出门（DI5）**：四通道验收先在当前环境确认导出容器实际尺寸、通道数及已知两处不同 alpha 测试值（`check_rgba_export`）；选经验证保留 alpha 的 PNG/浮点格式等，再计算 RGBA MAD。Descente 的 16.0.3 BMP 读回 alpha 恒 1，而 PNG 有效；不能据此禁用所有 BMP 类型。若 alpha 未保留，只可报告 RGB 指标并注明传输限制，不把该差异归因于 PP 数学。按真实 graph id 和扩展名唯一匹配导出文件。
11. **诊断编码前置门（DI6）**：在写任何编码节点前，从独立 oracle 计算本轮所有用例的原始分量，检查 `offset + gain×value` 均为有限且严格落在 `(margin,1-margin)`（`preflight_affine_probe`）；记录逆变换与解码后一 LSB 容差。超界则调整已证明范围/比例或使用经验证的浮点导出，不准把夹断的 PNG/BMP 当函数 FAIL。Descente 首次 `.5+.1×6.05=1.105` 误报属于夹具，不是 `DI_densityAt` 计算失败。

## 8. 症状诊断（D）

| ID | 症状 | 优先执行 |
|---|---|---|
| D1 | 全黑/全白 | SOP-5；I15退出条件；I18坐标0/0；I16类型维度 |
| D2 | 参数无效 | 精确Get名、形参/父参数/PP端口来源，打印当前值和连线 |
| D3 | 循环结果错误 | SOP-3；初值、携带、先读后写、cond、尾值与上限 |
| D4 | 循环不跑/只一轮 | 首先区分退出条件与继续条件，再测试初值和计数器更新 |
| D5 | 环外取不到状态 | I6/W5/RS2：先证明 While 完整执行，优先使用 While/显式纯值路径；若用 Get 必须验证该作用域；不得跨接 Body 内部节点 |
| D6 | 不收敛 | cond读取的状态是否更新，上限是否适当；避免阻塞脚本 |
| D7 | 分支结果丢失 | ifelse两支类型、末端值、条件写入与作用域 |
| D8 | 旧值/串值/合成重复 | I3/I19；Sequence端口顺序、变量版本、复用表达式 |
| D9 | 函数调用无效 | SOP-4；真实资源、端口id、类型与返回节点 |
| D10 | #端口读默认值 | PP完整具名端口、外部连线、默认值和Get名 |
| D11 | 名字被报悬空 | 先按四通道核实；#端口须存在，$内建须核实 |
| D12 | 零轮退出 | 打印首次 Exit Cond；源码继续条件应取反。若依赖 While 直接输出，零轮值官方未明确，必须探针；若读取 Init 已建立的状态，仍检查 Sequence/Get 顺序 |
| D13 | 树形图过高或单条语句子树过大 | 先 A1/SOP-5A 判断是否应拆 Function Graph；未触发或无安全拆分点时按 L4/L5/L13 保持树形结构并扩大该语句带宽/高度，不得为压缩高度把不同语句子树交错混排 |
| D14 | Sequence散乱、横向漂移或难以自上而下阅读 | L2/L3；同一代码块使用稳定的右侧 Sequence 主干，严格按 IR 执行顺序向下排列，并与对应 Set/语句根同行 |
| D15 | 参考全部不在网格/大量重叠 | L10/L11；相对原点，保守候选与真实尺寸分开 |
| D16 | 布局后结果或连线变化 | I20指纹；恢复本次位置、停止逻辑变化来源，不靠外观掩盖 |
| D17 | 同一类计算链反复出现、Function Graph 数量异常少 | SOP-5A；A2/A3；比较参数化同构签名，将变化常量提升为形参 |
| D18 | 拆出函数后单个函数仍极大或主图仍难读 | A7/I25；递归 Architecture Pass，不把复杂度从 PP 平移到一个超大 Function Graph |
| D19 | 命令式源码最终变成无 Sequence 的纯 DAG / iteration band | 先核对 L1 用户选择与每图锁定 mode。未选 B 或有状态/循环冲突 → N18/I26/§7.8：回到源码 statement IR，用 Set/Sequence 与 While 恢复结构；已明确选 B 的无循环直线计算可保留纯 DAG，但须记 `USER_SELECTED_DAG`、数值验收且结构保真不判 PASS |
| D20 | planned overlaps=0 但主图/函数跨度仍极大 | A11/I25；预布局反馈回 Architecture Pass。检查是否漏抽 loop-body/参数化重复，不能只以零碰撞结案 |
| D21 | 输出全 0，但中间量看似正确 | 优先 I28/T37：最终输出是否真的连线；再查 N20/I14 类型、SOP-0A 渲染管线与 `$pos` 能力，不先推断数学错误 |
| D22 | 大量节点没坐标、都落共享列或布局提前结束 | T38/L8；共享非叶节点首次出现必须完整布局其子树，只有后续引用跳过重新安放 |
| D23 | Function 实例集中在 (0,0) 或跨图报告大量假重叠 | T39/T40；实例必须登记进布局表，碰撞统计必须按图隔离 |
| D24 | Set 后出现跨多个 statement band 的旧 RHS/Set-value 长线 | N23/I31/§7.2；在 Set 处切断变量版本。生产 Set 接先执行 Sequence `In` 路径，下方 typed Get 的消费者接同链后执行 `Last` 路径；回读真实端口/可达性，再用非零变化用例证明作用域/类型。若不成立先修连线；拓扑正确仍失败则报告并取得例外决定，不能保留 Set/RHS 长线。 |
| D25 | While Cooker 报分支共享/loop variable 错误 | W4；检查 Exit Cond/Loop Body 闭包是否有节点同时连接其它分支。复制/重新创建 branch-private Get/常量/运算/实例，不跨边界共享节点 |
| D26 | 源码循环被保留成"类 for"结构，或被纯 DAG 链模拟 | N24/I32/§7.9.2；回到循环台账，按格式表重建 While；固定次数不是展开理由 |
| D27 | 循环只跑一轮/立即停止/多跑一轮 | I15/I33；`cond` 是否写成继续条件未取反、do-while 首轮是否丢失、上限是否为 0/1、标志复位位置 |
| D28 | break/continue 之后语句仍执行，或计数器不更新导致死循环 | §7.9.4/I33；break 出口标志与 ifelse 包装；`for` 的增量必须留在 continue 包装之外 |
| D29 | While 三输入端口存在但实际未接上，或沿用未核实的端口类型 | I34/§7.9.3；回读端口 id 与实例类型，断言 `init`/`cond`/`loop` 各有实际源连接；不按定义默认值推断类型 |
| D30 | 图里没有 While 但源码有循环，且报告未说明例外 | N24/§7.9.8；确认是用户显式要求或已证明引擎阻塞，并记录 `LOOP_UNROLL_EXCEPTION:<reason>`；否则恢复结构化 While |
| D31 | 图很高/很宽，但结构整齐，却被判为"跨度过大" | §7.10.4/I38；改用 `Y_per_statement` 与 `X_per_level` 归一化判断：语句带数与表达式深度解释得通 → PASS；只有结构比超标或跨带长连线才算缺陷。禁止用绝对 Y/X 判错，也禁止为提高指标压行距 |
| D32 | 排布混乱：不同语句的私有子树交错、或上方表达式被拉线到下方消费 | I37/L15/N26；在消费带内新建同类型 `Get(name)`，然后按"整棵子树/整个语句带"为单位重排（L13 第 9 步），不得改用全局二维压缩打散结构 |
| D33 | 生成完才发现排布混乱，需要大面积重排 | L16/I39；新建/移植任务应"规划排布 → 生成（创建即落位） → 仅位置校正"。若已发生全局重排：更新计划版本、按整子树/整语句带移动、报告计划-实际偏差与校正轮次；反复"创建 → 全局重排"说明计划阶段缺失，按 L16 第 5 条判 WARN 并补齐计划 |
| D34 | 编译通过但数值错/全 0/维度异常，疑似 `mul` 与 `mulscalar` 混用 | §7.5.1/I14/I40/N20：先查每处乘法的操作数维度判定依据。重点排查四类实例：上游或端口读回为泛型 `Float` 而实际是向量（实测 21/24 的 `mulscalar.a` 如此）、`mulscalar(a=float1, scalar=float1)` 静默返回 0（T33）、`mulscalar` 顺序颠倒（标量接了 `a`/Vector 或向量接了 `scalar`/Scale）、把 `A`/`B`/`Vector`/`Scale` 标签当端口 id 提交导致连线失败。结论必须来自类型解析链与回读，不能来自图像 |
| D35 | 数值"看着对"但边界/负数/半整数处错，或报告称"SD 没有某函数" | §7.5.3/I41/N27 + 分支文件：按五类逐一核对——①`mod` vs `fmod`（GLSL floor 基 vs C 截断基，负数结果不同）；②`round` 半整数约定（`round_float1` = `floor(x+0.5)`，与"远离零/银行家"在负数半整数差 1）；③`sign(0)=1`（非 0）；④`frac` 是 floor 基（负数与 `fmod(x,1)` 差 1）；⑤`step` 边界为 `x ≥ a`。凡"SD 无某函数"的断言，必须同时查过原子目录（85）与库 Functions（171）；只查一源即断言 → 结论无效。原子 `mod` 用于可负操作数前必须有探针记录 |
| D36 | 数值 PASS、跨度/碰撞 PASS，但 Sequence 出现在 Set/语句根左侧 | I30/L2/L12：先检查 depth 定义。若 depth 沿 producer→consumer 增大，却用 `x=base−depth×step`，则整图左右镜像。修正为正向 X 或改用从语句根向上游的 depth；计划与 SD 回读都执行逐条 `root.x < Sequence.x` 断言，不改连线即可做纯位置修复。此时逻辑 PASS、布局 FAIL，不得合并成总 PASS |
| D37 | 操作数/输入读数正确，消费者恒 0 | 首查该 `mul`/普通算术的 IR 两侧维度与端口角色，再查标根和仿射传输是否截断负数；混维连线成功不是广播证据。若一整批无关探针皆 0，先对确切包做已知常量活性 cook、查包是否卸载/句柄过期，再讨论图语义 |
| D38 | While 接线符合模板但累计值仍错 | 先查 Function 形参与 carried state 是否同名（Sun shower 的 `p` 遮蔽），再按固定输入 body、独立变换、两轮 vector carry、非恒定 scalar 更新、具体实例调用的次序逐步消融；旧“float2 carry 坏了”结论已被有效包重跑推翻 |
| D39 | 子函数用例通过，组装图大区域错或持续有符号偏差 | 先比对源码 section/顶层 branch 的 `PORTED/OMITTED/BLOCKED` 表与成图的实边可达性；缺 hills、水分支或未接上的 vignette 不会被局部单测发现。按语义区域分桶看有符号误差，定位第一个偏离的源项；参考图须通过范围/视图/来源核验 |
| D40 | 翻转图像后 MAD 更好，或两个 probe 的边界互相矛盾 | 不用 MAD 决定方向：按每个写入器的 `$pos.y` ramp/不对称地标测文件行顺序，所有跨文件逐行 join 使用相同视图标签；相机基向量还要独立解析地核验三分量，不能用其自身分支 marker 自证 |
| D41 | 同一个 Function 在一处 caller 正常、另一处黑/NaN | 先做**该函数**的独立最小 consumer、常量/变化输入和有限值探针；不把某次 `fbm` 失败泛化成实例深度禁令，且 branchless `lerp` 中非激活支的 `NaN*0` 仍可污染整帧 |

二分中间结果只在已有正确基线、输入条件和单调执行链适用；不能断言所有错误都在最后一个“看似正确”变量之后。

## 9. 交付报告模板

工程任务保留以下字段。不适用的小节写N/A，适用但未执行写未验证；布局专项不假装完成数值全检。

```text
环境模式：A / B / C；执行能力与当前工具连接状态

## 目标与授权范围
包绝对路径；资源/图身份；PP id；输入/输出文件；当前会话修改状态
任务：分析/创建/修复/布局；本次允许修改的图和字段

## 结论摘要
三行以内；逻辑、布局、渲染分别说明

## 检查结果
| ID | PASS/FAIL/WARN/N/A/未验证 | 图身份、节点id/计数、方法与范围 |
列出适用I项；布局同时列L项例外

## 代码还原
IR/语句表；表达式截断与未覆盖分支说明
Statement/Get 依赖表：生产 Set/变量名/维度 → Sequence `In` 先执行路径 → 下方消费 Get 及消费者至 `Last` 后执行路径 → 输出可达性 → 非零变化原生读值。附真实连线快照；缺快照不能通过拓扑门。逐边列出跨 statement 的 Set/RHS→普通算子连线；只要存在且无合法结构例外，判 I31/I37 FAIL，即使 Sequence 主干存在。Get 读值失败先列出缺失/错误端口与修复结果；拓扑正确仍失败时才列待决冲突与已授权例外，不静默切换。
时间图附：`$time` 系统路径、`iTime` 参数/手动路径、选择器默认值与 `effectiveTime`；每次验证 cook 的模式和具体时间。不得以 Designer 内 `$time` 静态值删除 Player 路径。
BUILTIN_AVAILABILITY、I42 向量槽位、I43 Get 维度、I44 变换应用点、I16 broadcast lowering、BRANCH_COVERAGE：适用项分别列源码位置/目标映射/静态与数值结果。

## Architecture Pass
Architecture Gate；源码模式（Statement/Expression）；拆分前后图数/各图预估及实际节点数/最大图节点数/预布局跨度；固定循环 loop-body Function 决策；A11 是否触发回流
| candidate | source graph / before nodes | replaceable caller nodes | replacement instance+glue nodes | projected / actual caller nodes | projected / actual function nodes | call sites | typed inputs/outputs | safe? | decision / reason | function oracle | first call-site I24 |
无安全候选时记录检查范围与阻断原因；列出 STRUCTURAL_EXCEPTION / FUNCTIONIZATION_BLOCKED 及证据。`1200–1500` 图附响应/回读、cook、布局证据和 WARN；对拆分后每张图独立写预算结果。

## 循环台账
| 图/while id | 源码循环 | 源码格式 | 退出条件（cond） | init | 携带量 | 每轮临时量 | break/continue 降级 | Body尾值/While输出类型 | 环后读取方式（direct output / post-loop Get） | 预计/实际轮数 | Max iterations 及来源 |

## 循环降级与连接规划
| while id | mapping（WHILE / LOOP_UNROLL_EXCEPTION:reason） | init 源 | cond 源（末端类型） | loop 源 | max_iter 取值/来源 | branch-private 节点数 | 环外读取方式 | 模板一致性（§7.9.10） |
写出 I32–I35 结果；逐项说明与 §7.9.10 模板的偏离（Init 是否只放初值、cond 是否只读不写且不共用 Get、tail Get 是否为独立新建节点、常量是否私有、几何是否保持三个子区域）；存在例外时写明理由与替代结构；模板前置（输出节点、无悬空 Get、PP 已接线）未满足时必须列出

## 函数调用
| 调用完整身份 | 被调资源完整身份 | 来源（已有/源码映射/抽取） | 端口id/类型vs形参 | 连接与一致性 |

## 布局验收
| 图身份 | 节点数/位置覆盖 | Statement/Expression模式 | Sequence主干/语句带 | 计划与回读 `root.x < Sequence.x` 逐条结果 | 原点/网格 | 计划占位/候选碰撞/真实重叠 | 树方向/I30 | x,y跨度 | 指纹 | 布局 PASS/FAIL |
任何关联语句反向时单独报告布局 FAIL；不得因原生 cook 或跨引擎数值 PASS 把布局升级为 PASS。

## 语句树连接与跨度预算
| 图身份 | 节点数 | 语句带数 | nodes_per_statement | 最大表达式深度 | spanX/spanY | Y_per_statement | X_per_level | 边数 | dy 中位/p90/max | dx 中位/p90 | 跨带边数（含例外理由） | 列步/行步 |
Expression 图把 `nodes_per_statement`、`Y_per_statement` 填 `N/A(expression)`，另列每层宽度/扇出；不套用 Statement 比值阈值。
写出逐边 dy/dx 统计与 §7.10.2 例外清单；列出 `SPAN_JUSTIFICATION` / `STRUCTURAL_EXCEPTION`；说明哪些 Get 是"读走上游 Get"的新建节点、哪些读取走的是函数形参；未做逐边统计时标未验证（I37/I38）

## 布局计划一致性（L1/L16）

先列用户图结构选择、每图 source kind 和锁定的 mode；未得到选择、选择 B 与状态/循环冲突、或纯布局将需要改拓扑时标为待用户决定，不能自动转模式。
| 图身份 | 入口模式(A/B) | 计划版本 | 计划坐标数 | 实际坐标数 | 偏差节点数/最大偏差 | 校正轮次 | 是否仅位置修改(I20) | 计划跨带边 vs 实际(I37) | `POSTHOC_LAYOUT` |
模式 A（新建/移植）必须证明节点创建即落在计划坐标；出现计划外重排时给出原因与计划版本更新记录（I39/D33）

## 类型与乘法节点选择（§7.5.1/I40）
| 位置（图/语句） | 源码表达式 | 操作数维度 | 判定依据链（回溯到的确定维度节点/IR 类型） | 所选 definition | 端口绑定 | 探针记录（向量×向量时必需） |
必须覆盖图中每一处乘法与归约；无法回溯维度的一律标**未验证**，不得凭端口读回或定义默认值 PASS（I40/N20/D34）

## 数值语义选择（§7.5.3/I41）
| 位置（图/语句） | 源码表达式 | 语义类别（floor 基/截断基/半整数约定/零点约定） | 判定依据（源码语言与原文） | 所选供给（原子 / 库函数实例 / 显式构造） | 端口绑定（形参 id） | 与源码差异 |
库函数实例另列当前会话资源获取/最小实例/首调用点证据；不可达时列 `LIBRARY_INSTANCE_UNREACHABLE`、显式构造式及独立 oracle。
必须覆盖 `mod`/`fmod`/`round`/`frac`/`trunc`/`sign`/`clamp`/`saturate`/`step`/`smoothstep` 及任何同名不同义者；凡断言"SD 无 X"须注明原子目录与库 Functions 两源均已查证；原子 `mod` 用于可负操作数时必须有探针记录（I41/N27/D35）
占位来源、UI复核范围、桥接/共享/多端口例外

## 问题与预期差异
按严重度列问题、证据、已做动作/建议；当前会话与磁盘差异

## 验证与产物
实际执行的SD渲染条件、静态/数学/跨引擎检查范围
ORACLE_PROVENANCE: source=<当次源码 sha256> table=<当次表文件 sha256|n/a>；缓存表是否由该源码/命令当次生成。哈希不匹配只作 cross-check。
逐函数测试：`BRANCH_COVERAGE`、非对称向量用例、编码 `enc`/`dec`、解码后一 LSB 容差/下游量化步长比值；精度不足时标 WARN，不以 PASS 解释量化残差。
诊断抽头（若有）：源节点真实回溯路径、源分量→BMP 通道、独立交叉证据、恢复原根与临时资源清理回读。
原生探针记录（SOP-0B）：环境版本、目标临时资源、探针表达式、编码方式、实测值、两候选语义距离、判定，以及局限（8bit 量化、未覆盖范围）；未做探针时明确写"未验证"，不得用文档描述冒充实测
回测专项门槛（`MORPHING_RETEST_GATES.md`）：PP 根节点维度/标记数、IR 必需节点至输出的实边可达闭包、逐函数非退化数值用例、最终图像 oracle、实际导出文件名及尺寸、布局方向、当前会话模块/资源残留分别记录 PASS/FAIL/未验证；不可用总体“PASS”掩盖布局或探针失败。
复杂移植专项（`SUN_SHOWER_RETEST_GATES.md`）：源码 section/顶层 branch 的 PORTED/OMITTED/BLOCKED 表、目标包与源码模块身份/哈希、每轮常量活性 cook、预估/实际节点预算；图像比较须列每个写入器的文件行序与归一视图、参考生成命令/源码及文件哈希/分辨率/覆盖分支/同会话重建结果、双方向指标及语义区域有符号误差。参考不能重建或缺分支时，相关数字只能列 cross-check。部分交付分别写出已验证子集、遗漏/阻塞部分和解除 hold 的具体证据，不得合并成全量 PASS。
保存文件路径；保存后回读；脚本执行入口与日志位置

## 未验证项
适用但未读取/未执行、包外调用、真实节点尺寸、跨GPU与零轮行为等
```

不得将“计划占位重叠0”写成“精确UI视觉重叠0”，不得将CPU解释器一致写成“浏览器逐像素一致”。

## 10. 节点布局执行规则（L）

本章定义最终交付布局。对用户选择 A 后的 Statement 图，布局模型不是“尽量压缩的二维 DAG”，而是**代码结构树形布局**：右侧保留 Sequence 执行主干，每条语句以 Set / 返回值 / 控制节点为语句根，依赖表达式从该根向左递归展开。对已选 B 的合法 Expression 图采用纯 DAG 布局；两者均须先锁定源码/用户选择，再优化跨度、连线长度和紧凑性。
本文没有附带完整布局器；agent必须按SOP-8生成计划、检查、应用与回读。布局只解决视觉组织，不承担结构化重构职责；创建/修复任务在进入本章前必须先通过 Architecture Gate。

**生成顺序（默认）**：`规划排布 → 生成节点（创建即写计划坐标） → 几何校正 → 验收`。布局计划是纯数据产物，只依赖 IR/ARCH_PLAN，因此必须在任何 `newNode` 之前完成（L16）。"先出图、再整体排布"只适用于**既有图**修复或纯布局任务（SOP-8 模式 B），新建/移植任务走此路径须记录 `POSTHOC_LAYOUT:<reason>`（I39/D33）。

### L1：先分类布局模式，再建立树

**用户选择门**：新建、移植或涉及图结构/布局风格的修改任务，若用户尚未表态，在首次风格相关写入前**只问一次**：

> 这次希望采用哪种图结构？A. 结构保真：命令式部分用 Set/Sequence，纯表达式函数仍用 DAG；B. DAG 优先：直线计算可改成纯 DAG，但不保留源码赋值顺序结构；遇到状态/循环会先停下确认。

把原话答复与选择（`fidelity` / `dag`）、每图 source kind（`pure` / `straight_line` / `stateful_or_loop`）、选定 mode（`statement` / `expression`）写进 IR 与布局计划。用户已明确指定时不重复问；仅只读分析不为此打断。用户未答复时可继续只读盘点/出备选计划，**不得做依赖此模式的写入**。选择一经记录，不能因某种实现更省节点或渲染分数更好而悄悄切换；改变选项须再征询用户。纯表达式图在 A 下仍是 Expression，Statement 图内的局部表达式也仍可为 DAG，因此项目中同时看到两类局部形态并非自动违规。

最终布局有两种主模式，按**用户选择 + 源码 IR**逐图锁定：

- **Statement 模式（A 下的命令式源码）**：Sequence 构成稳定的右侧纵向主干，阅读方向严格自上而下；每条赋值/状态更新有 Set/语句根。
- **Expression 模式（纯表达式 Function Graph；或 B 下无循环的直线计算）**：没有人为新增 Sequence；真实返回节点位于右侧，整个无副作用表达式树向左展开。B 改写了源码赋值结构时记 `USER_SELECTED_DAG`，I26 不判结构保真 PASS。

若 B 遇到真实状态更新或循环，先说明 pure DAG 与状态/While 语义的冲突，请用户重新决定或单独确认可行的结构取舍；**不得**自动改回 A，也不得仅凭选择 B 静默 unroll/删 While。纯布局且未获结构修改授权时，用户偏好的模式若要求增删 Set/Sequence，只能报告差异并询问是否另行授权，不能把“布局”当改拓扑授权。模式在计划与 SD 回读两个阶段分别用 `scripts/layout_intelligence.py` 的 `select_graph_mode` / `validate_mode_readback` 检查；命令式源码无说明地出现纯 DAG，按 I26 返回结构阶段。

Statement 模式中，Sequence 构成稳定的右侧纵向主干，阅读方向严格自上而下。
每条语句的 Set、返回值、While、ifelse 或其它语句结果节点作为该语句的**右侧根（statement root）**；其 value / 参数 / 条件 / 输入表达式从根向左递归展开。
因此整体阅读方式为：

`左侧叶子/输入 → 中间运算/函数实例 → Set/语句根 → 右侧 Sequence`，同时 `Sequence` 自上而下表达代码执行顺序。

坐标不决定引擎执行顺序，但布局必须忠实表现已还原的 IR 顺序；不得为了视觉紧凑改变语句归属或制造不存在的 Set→Get 数据线。

### L2：Sequence 使用稳定纵向主干

同一代码块 b 定义 Set/语句根列 `Xs[b]` 与 Sequence 主干列 `Xq[b]`，必须满足 `Xs[b] < Xq[b]`。默认 `Xq[b]=Xs[b]+128`；多端口或较宽节点可增至160或按实测占位扩大。Designer 画布 X 增大表示向右；若 depth 从 producer 到 consumer 递增，X 必须随 depth 增大，不能用 `x=base−depth×step`。如从 statement root 向上游计算深度，才可减去深度。两种 depth 语义不得混用。
同一块内所有顶层 Sequence 优先共用同一 `Xq[b]`，不得逐条语句左右漂移。
第 i 条语句根 `s[i]` 与对应 Sequence `q[i]` 同行：`q[i].y = s[i].y`。
`q[i+1]` 必须位于 `q[i]` 下方，并通过 `seqin` 沿主干向下形成清晰执行链；Y顺序以代码/IR语句顺序为唯一依据。
块间桥接 Sequence 可使用独立桥接列，但必须保持父块→子块的自上而下关系并记录角色。

### L3：Set / 返回值是表达式树的右侧根

普通赋值语句以 Set 为 statement root。Set 的直接 value 源放在左侧，优先与 Set 同行；value 的上游继续向左展开。**Set 之后变量版本在视觉上也必须切断**：用户选定 Statement/Get 时，消费带内放新的 typed Get(name) 叶节点，其消费树须实际接入同一输出可达 Sequence 链的后执行 `Last` 路径；再以非零变化数值验状态。验证失败先排查/修复端口与路径，拓扑正确仍异常才停下或申请例外。禁止从前一语句 RHS/Set.value 上游拉长线跨越 statement band。
非 Set 的直接返回表达式，以真实返回节点作为 statement root；不得人为创建不存在的“Output”或“Return”节点。
Sequence 的 `seqlast` 必须连接/对应本行真实语句根；不得把 Sequence 放到两个输入的中点、整棵子树的中点或共享区域重心。
当 seqlast 为 While、ifelse 或子块尾值时，该控制节点/汇合节点就是本行 statement root。

### L4：表达式按树深度向左递归展开

对每条语句建立独立表达式树视图：consumer/父节点始终比其私有输入/子节点更靠右。
同一路径每增加一级树深度，默认向左移动一个列间距；普通节点建议 160–224，多端口实例按实际宽度扩大。
单输入链优先保持接近水平；多输入节点的子树作为兄弟分支在左侧上/下展开，父节点保持靠近这些分支的汇合处。
局部常量、Get、swizzle 等叶节点贴近其实际消费者，不按节点创建顺序或全图统一类型列重新分组。
**禁止为了压缩总高度，将属于不同顶层语句的私有表达式节点交错穿插。**

### L5：以“语句带”隔离各棵树

每条顶层语句先计算其表达式树占位包围盒，形成 `statement band`。
同一代码块中的 statement band 按 IR 执行顺序从上到下排列，相邻 band 默认保留至少一个网格级安全间距；下一条语句根的 Y 必须位于上一条语句完整子树包围盒之后。
因此行高由该条语句实际子树高度决定，而不是统一固定 96/128，也不是允许其它语句随意占用其树内部空隙。
只有明确属于共享 DAG、桥接或父/子控制块的节点可以跨 statement band；必须在计划中标注例外。
若单条语句树本身巨大，应先触发 A1/SOP-5A 检查 Function Graph 拆分，而不是通过交错其它语句来“填空”。

### L6：分支节点保持源码结构而不是视觉重心

ifelse、vector 组合、多输入算术和函数实例均按真实端口/源码表达式关系建立兄弟子树。
兄弟子树的包围盒不得互相重叠；其上下次序优先采用：源码/IR中可恢复的参数顺序 → 真实端口顺序 → 稳定定义顺序。
不得使用“所有父节点取平均 Y”“全图按最长路径层级统一对齐”或力导向/重心压缩算法覆盖代码结构。
函数实例作为表达式树中的普通中间节点；输入子树在其左侧，实例输出继续向右流向父表达式/Set。

### L7：While / 控制结构作为结构化子树

While 本身作为所属语句的 statement root 或其表达式子节点。其 `init`、`cond`、`loop` 是三个明确子区域，整体位于 While 左侧，并保持结构边界。
默认从上到下排列 `init → cond → loop`；如果源码/IR明确提供其它结构顺序，以 IR 为准。While 节点优先与 cond 的结果行对齐，但不得因此把 init/loop 打散到其它顶层语句中。
init 或 loop 内部若含 Sequence，则各自建立**局部纵向 Sequence 主干**，同样从上到下排列；嵌套控制结构递归应用 L1–L7。
ifelse 默认将 condition 置于靠近汇合根的位置，if/else 两支作为独立子树上下展开；两支内部仍保持自己的源码结构。
While 的 `__constant__`（Max iterations）是节点属性而非连线，不构成第四个数据子区域，但必须在报告中记录其值来源。三个数据输入 `init`/`cond`/`loop` 必须各有实际源连接后，该子区域才算布局完成（§7.9.3/I34）。

### L8：共享 DAG 是树形布局的明确例外

逻辑上共享的节点不能为了视觉树形而复制。每个共享节点只保留一个真实位置。
先为节点建立消费者表和最低共同语义归属；**共享叶子**（无输入的常量/Get等）可以直接放公共区域。带输入子树的共享节点在第一次遍历遇到时必须像普通节点一样完整布局其子树并登记位置，后续消费者只复用该位置，不能因为 `consumer_count>1` 就提前 return。共享节点优先放在能够同时服务多个消费者的左侧公共区域，并标记 `SHARED_DAG`。
共享节点可以造成跨 statement band 长线，这是允许的例外；不得以此为理由重新打散所有私有子树。
若共享区域规模很大并严重破坏树形可读性，优先回到 Architecture Pass 评估是否应抽成 Function Graph，而不是用任意二维压缩解决。

### L9：Passthrough 只承担走线职责

Passthrough 保留原连接和转折职责，不视为新的语义语句，也不单独占据完整 statement band。
它应沿所属数据路径放置在父子树之间或跨区线路上，尽量保持左→右数据流。
代码展开可以穿透 Passthrough，但视觉布局必须给它真实坐标；不因其尺寸较小而推广为普通节点占位标准。

### L10：按相对原点吸附

每图记录 `originX/originY` 及默认 `grid=32`，使用 SOP-8 的 snap 公式。
新图可以选择 `(0,0)`，也可以继承已有图的网格相位；整体平移和负坐标不影响结构。
先完成树形相对位置和 statement band，再做网格吸附；不得先全局吸附再反向改变父子/主干关系。
纯读取不改小数坐标；已授权新布局才吸附并回读。

### L11：碰撞检查以子树/语句带为单位

同坐标堆叠或实测可见矩形相交是 FAIL。默认128×96仅为普通节点计划占位，不是精确可见尺寸。
布局计划至少检查：节点矩形、兄弟子树包围盒、statement band、Sequence 主干间距、控制块子区域。所有矩形、跨度与重叠统计必须以完整图身份分组；不同 PP/Function Graph 的坐标不能互相比较。
碰撞修正优先整体移动发生冲突的**子树或 statement band**，不得只推单个内部节点导致树关系破坏；尤其不得单独推 Sequence 使其脱离主干。
Frame 包围所属节点是预期包含，不作为节点碰撞；注释遮挡、跨区长线穿节点另做视觉复核。

### L12：最终布局验收

| 项 | 新布局要求 |
|---|---|
| 位置覆盖 | 全部节点，含 Sequence/While/Passthrough；未覆盖 FAIL |
| 逻辑指纹 | 纯布局阶段 I20 完全一致；差异 FAIL |
| 布局模式 | A 下命令式源码须 Statement、纯表达式函数可 Expression；B 下无循环直线计算可 `USER_SELECTED_DAG`/Expression，结构保真非 PASS。命令式源码无用户选择或无说明地使用纯 DAG、或状态/循环被 DAG 静默替换 → FAIL |
| Sequence 主干 | Statement 模式下同一块 X 基本稳定、自上而下严格遵守 IR 顺序，且每个关联 Sequence 的 X **大于**对应 Set/语句根的 X；任一反向即 FAIL。最终纯输出节点可在 Sequence 右侧 |
| Sequence/语句根同行 | `q[i].y = statementRoot[i].y`（计划严格相同，回读允许测量容差）；违反 FAIL |
| 树方向 | I30：私有输入/叶节点在左，consumer/Set/返回根在中，关联 Sequence 在右；逐条方向检查，任一未说明反向 → FAIL |
| 语句带顺序 | statement band 按执行顺序自上而下，私有子树不得与其它语句交错；违反 FAIL |
| Set/value | value 树在 Set 左侧并短距离汇入；无合理例外却跨越其它语句 → WARN/FAIL 视程度 |
| 跨语句变量读取 | 用户选定 Statement/Get 时，下方消费带新建 typed Get(name)，其消费者须接入 Set 后同一可达 Sequence 链的 `Last` 路径；真实端口、作用域/类型及非零用例共同验证。Sequence-value 只作已批准例外。继续使用前一 Set/RHS/旧版本节点跨 band → FAIL（N23/I31）。 |
| While/ifelse | 控制结构保持独立子区域；内部 Sequence 使用局部纵向主干；结构被打散 → FAIL |
| 共享 DAG | 单实例、明确 `SHARED_DAG` 归属；不得为树形复制逻辑节点 |
| 网格 | 按已记录相对原点吸附；偏离 WARN |
| 碰撞 | 新计划节点和兄弟子树/语句带无非法重叠；实际尺寸未知单列未验证 |
| 紧凑性 | 只在结构保持后优化；图较宽/较高本身不允许成为破坏树结构的理由 |
| Architecture Gate | 创建/修复任务若触发 A1，必须已有 SOP-5A 结果；预布局触发 A11 必须回流；存在安全拆分点却继续单体交付 → FAIL |

Substance Designer 本身在本规范中仍没有已证明的全局固定高度/宽度/节点数硬限制；A1 数字属于 Agent 交付复杂度阈值，不得误写成引擎限制。树形布局可能比二维压缩布局占用更多空间，这是预期行为；应通过 Function Graph 拆分控制复杂度，而不是牺牲代码结构。

### L13：树形布局器实施顺序

0. 检查 Architecture Gate。创建/修复任务触发 A1 时必须先完成 SOP-5A；纯布局且禁止逻辑变化时记录结构候选但不越权重构。
1. 建立完整图键、节点/连接 IR、消费者表、控制块结构及逻辑指纹；每个原子节点与 Function 实例都必须进入同一布局登记表。
2. 从源码/Final IR 分类 Statement/Expression 模式。Statement 模式从 Sequence 还原严格语句执行列表；如果命令式源码没有 Sequence，停止布局并按 I26 返回构建阶段。Expression 模式从真实输出建立单棵表达式树。
3. 对每个 statement root 递归建立其私有表达式树：父节点=consumer，子节点=输入源；记录端口顺序、树深度、共享节点和控制结构。
4. 对树做自底向上的尺寸计算：节点占位 → 子树包围盒 → statement band；兄弟子树先消除内部重叠。
5. 在右侧建立 Set/statement-root 列与 Sequence 主干列；按语句顺序从上到下依次放置 statement band，并令每条 Sequence 与对应语句根同行。
6. 在每个 statement band 内，从 statement root 向左递归安放表达式树；单输入链水平展开，多输入兄弟树上下展开。
7. While/ifelse/嵌套 Sequence 递归建立局部结构；共享 DAG 按 L8 处理：非叶共享节点首次遇到时完整布局，后续引用只复用。
8. 处理 Passthrough 与桥接线路；不得通过移动 statement root 或 Sequence 主干来迁就普通长线。
9. 以“整棵子树 / 整个 statement band”为单位修正碰撞，然后按相对网格吸附；吸附后重新检查树方向、同行、主干顺序和碰撞。
10. 应用前验证计划覆盖、I30（含每条 `Set/statement root.x < Sequence.x`）与 L12，并计算每图最终预估跨度；触发 A11 时返回 SOP-5A，不应用本轮位置。应用后对 **SD 实际回读坐标再次执行 I30**，再查 I13/I13b/I20 及必要原生输出；保存由外层控制。可用 `scripts/layout_intelligence.py` 做纯数据断言。仅凭 `spanX`/`X_per_level`/无碰撞/数值正确不得把镜像布局判为 PASS。
11. **应用时机取决于入口模式**（L16）：新建/移植任务在**创建时**写入计划坐标（创建即落位，第 4–6 步的计划结果直接作为 `newNode` 后的 `setPosition` 参数）；既有图/纯布局任务才在生成后做 position-only 应用。两种模式都必须在应用后按第 9 步做几何校正，并报告计划-实际偏差与校正轮次（I39）。

明确禁止以下布局策略作为最终主算法：按节点类型全局分列、按最长路径统一层级、父节点 Y 取所有输入重心、力导向布局、为了最短连线把不同语句的私有子树交错混排。它们可以用于诊断或局部初始猜测，但不能覆盖代码结构树形约束。

### L14：跨度预算按语句带数与表达式深度归一化

1. 布局计划必须报告 `Y_per_statement`、`X_per_level`、`nodes_per_statement` 与逐边 dy/dx 统计（§7.10.4–§7.10.6/I38）。
2. 行步取 192/224/288（吸附 32），列步取 128/160/192/224；不得为了压绝对高度改小于 192 的行步，也不得交错不同语句带的私有树来缩小包围盒。
3. 触发 A11 回流的是归一化指标（`Y_per_statement > 512`、`X_per_level > 384`、节点数 `≥400`、未处理跨带长连线），不是绝对 Y/X。
4. 绝对跨度超过 `spanY 12000` / `spanX 4800` 时，报告中写出语句带数与最大深度，说明其为结构规模而非排布缺陷（D31）。

### L15：禁止跨带长连线（读取走上游 Get）

1. 每条局部表达式连线应落在同一语句带内（dy=0 优先，≤1 行步）；post-Set 跨带读取应走本带 Get 消费树并接入同一输出可达 Sequence 链的后执行 `Last` 路径。需回读真实端口及验证作用域；Sequence-value 直传仅作获准例外（对应 L13 第 5–6 步）。
2. 例外仅限：Sequence 主干纵向串联、控制块结构边、Function 实例扇出、L8 登记的非叶共享 DAG 例外；例外必须在报告中逐条列出并给理由（§7.10.2/I37）。
3. 修正跨带长连线时先加 `Get` 再删长线；不得靠移动 statement root 或 Sequence 主干去迁就长线（L13 第 8 步）。

### L16：规划排布先于生成（plan-then-generate）

**默认顺序是"先规划排布、再生成节点"，不是"先生成、再整体排布"。** 布局计划是纯数据产物，只依赖 IR/ARCH_PLAN（L13 第 1–4 步），因此必须在任何 `newNode` 之前完成：

1. **计划先于创建**：新建/移植任务在创建前生成每张目标图的完整计划（图身份、语句带与主干列、每个节点的角色/树深度/占位矩形与**计划坐标**、网格原点、While 与控制块子区域）。计划未通过 L12/L14/L15 检查前不得开始大批创建。
   **DI2 计划结构门**：对每张图及每个嵌套 While/分支执行块分别调用 `validate_layout_plan`，将本块关联的 Set/Sequence 对、按 IR 顺序的 Sequence spine、私有表达式边一并传入；要求 `x(input)<x(Set)<x(Sequence)`、Set/Sequence 同行、本块 Sequence 共列且从上到下、无相同计划坐标。纯后处理根可在主干右侧，但不得让主干随全局表达式深度漂移。失败时修计划版本，**首次 `newNode` 不得开始**。该结构门独立于坐标是否被实际应用；创建后再用 `validate_position_application` 与结构回读分别验收。
2. **创建即落位**：每个节点在创建的同一阶段写入其计划坐标（`newNode` 后立即 `setPosition`，与 SOP-7 的 `checked_new` 模板一致），不允许先落在默认/临时位置、事后再由一次全局排布搬动。**"生成完再排布"只在既有图修复或纯布局任务时成立**；新建任务若确实无法提前规划，须记录 `POSTHOC_LAYOUT:<reason>`（I39/D33）。
3. **允许且必须的三段式**：`规划 → 生成 → 几何校正`。原因：节点真实尺寸（形参数量不同的实例、常量/可调尺寸节点）只有创建后才知道，计划只能使用**标称占位 + 余量**；因此"零校正"不是要求，"零计划外重排"才是。
4. **校正仅限位置**：校正阶段只允许 `setPosition`，按"整棵子树/整个语句带"为单位移动，然后重新吸附、重新查碰撞（L11/L13 第 9 步）；不得改变逻辑、连接、名字或函数接口（I20/I39）。
5. **校正不得退化为事后布局**：若校正演变成整体重排（例如超过 1/3 节点换带、语句带顺序改变、主干列平移），必须停止、更新计划版本并说明原因；反复"创建 → 全局重排"即视为计划阶段缺失（D33）。
6. **坐标空间独立**：每张 Function Graph、主 PP 内部图、复合图各自一份计划，互不引用对方的绝对坐标；Function 实例的占位按其形参数量估。
7. **计划即验收基线**：报告必须给出"计划坐标 vs 实际坐标"偏差、校正轮次、是否仅位置修改，以及计划中被预判的跨带边与最终 I37 统计的差异（§9/I39）。

## 11. 证据、失效规则与版本维护

### 11.1 证据范围

历史布局与迁移观察不再作为当前执行规则；当前规则仅见正文与 `REAL_PROJECT_VALIDATION.md`。下列 16.0.3 实测表保留作特定版本的可核查样本，不自动证明新工程已通过验证。
### 11.6 While 连接规划实测基线（16.0.3，2026-09-22）

环境：Substance Designer 16.0.3 + sd_mcp_plugin 3.3.0，模式 A。来源：本版规则修订时对已加载包 `E:/SD_AI/sdtext/Fabrice_Fractal_Port.sbs` 的**只读**回读（未创建、未修改、未保存任何图）。

| 项 | 实测结果 | 状态 |
|---|---|---|
| While 定义 id | `sbs::function::while` | 确认 |
| 输入端口 | `init`、`cond`、`loop`、`__constant__`（Max iterations，int1） | 确认 |
| 输出端口 | `unique_filter_output` | 确认 |
| 端口类型 | 多态：同一实例 `init`/`cond` 为 bool，`loop` 与输出为 float；定义默认类型不能作为实例类型证据 | 确认 |
| 现有 While 实例 | 图 `loop01` 节点 `1582207887`，`__constant__ = 32` | 确认 |
| 现有接线形态 | `init` ← Sequence（`seqin`/`seqlast`）；`cond` ← 比较节点输出；`loop` ← Sequence | 观测（该图语义未在本会话验证） |
| 关联原子端口 | `sequence`：`seqin`/`seqlast`；`set`：`value`/`__constant__`；`ifelse`：`condition`/`ifpath`/`elsepath`；`passthrough`：`input` | 确认 |

用途：作为 §7.9.3 端口规划的当前环境依据。这不等于对任意版本的自动认证；不同版本仍按 SOP-0A 按需复核。**未验证**：该实例的 `cond` 方向与轮数、零轮行为、跨版本端口一致性。

**模板文件实测（§7.9.10 的来源）**

来源：`loop whlie.sbs`（sha256 `30f259128cff08a00eb159a9160b2965d07e877ddf08cee5e2964d556942f64f`，17089 B；本会话只读回读，未修改未保存）。该文件是"计数器上下行 + 状态跨迭代"的单 While 模板。

| 项 | 实测结果 | 状态 |
|---|---|---|
| 包/复合图 | 仅 1 张 `SDSBSCompGraph` / `Substance_graph`（13 节点） | 确认 |
| 循环位置 | PP 节点 `1582386878` 的 perpixel 内部图（21 节点，1 个 `while`） | 确认 |
| While 实例 | `1582386889`，`__constant__ = 32` | 确认 |
| Init 链 | `while.init` ← `sequence 1582386906`：`seqin`=Set(`d`)=100.0、`seqlast`=Set(`a`)=2.0 | 确认 |
| Cond 链 | `while.cond` ← `lr 1582386891`（bool）：`a`=const 6.0、`b`=Get(`a`) 1582386892 → `6.0 < a` | 确认（`lr` 定义描述实测为 A<B） |
| Loop 链 | `while.loop` ← `sequence 1582386900`：`seqin`=`sequence 1582386930`（Set(`d`)=Get(`d`)−1 → Set(`a`)=Get(`a`)+1）、`seqlast`=Get(`d`) 1582386896 | 确认 |
| Tail 约定 | Body 主干 `seqlast` 用**独立新建**的 Get 给出"本轮更新后的状态" | 确认（与 Set RHS 的 Get 非同一实例） |
| 轮数与终态（推演） | Body 执行 5 轮；终态 `a=7`、`d=95`；上限 32 不触发 | 静态推演（未做原生渲染） |
| 分支私有 | init/cond/loop 闭包两两无交集；闭包内节点无跨分支消费者 | 确认 |
| **该 demo 的缺陷（不属于模板规则）** | ① 内部图 `getOutputNodes()` = 0，While 输出无消费者；② 悬空死节点 `Get('d0')` `1582386920`（无 Set/无消费者/非父图参数）；③ PP 节点在复合图中无任何连线 | 确认（对应 I1/I2/I8/I28） |
| 模板未覆盖 | `Max iterations` 来源未记录（WARN）；无 GLSL/HLSL 源可比对（I32/I33 未验证）；未做原生渲染与零轮探针 | 未验证 |

结论：该文件的**循环内部连接方式**被采纳为 §7.9.10 模板（角色、端口级连接链、语义约定、几何）；上述三项缺陷被明确排除在模板之外，并作为"模板使用前置"写入 §7.9.10。

### 11.7 语句树连接与跨度实测基线（`OKColor_LCH.sbs`，2026-09-22）

来源：附件 `OKColor_LCH.sbs`（sha256 `0372b50801013d2ae1be57806778a8799223042e7bd57429caaf8326362ed41f`，372065 B；work copy `E:\SD_AI\sdtext\OKColor_LCH.sbs`），SD 16.0.3 + sd_mcp_plugin 3.3.0，**只读**回读（未创建、未修改、未保存）。

| 项 | 实测结果 |
|---|---|
| 资源构成 | 1 张 `SDSBSCompGraph`（`OKColor_LCH_PJW`，5 节点）+ 15 张 `SDSBSFunctionGraph`（10–368 节点）+ Resources 目录 |
| 全包规模 | 1058 节点；95 `sequence`、109 `set`、198 `get_*` |
| 最大单图 | `find_gamut_intersection_cusp_Upper_half` 368 节点 / 43 Sequence / 43 Set / 95 Get；spanX 1568、spanY 11419、最长路径深度 47 |
| 次大单图 | `compute_max_saturation` 238 节点 / 27 Sequence / 28 Set / 46 Get；spanX 2278、spanY 6240、深度 33 |
| 连接剖面（1228 条边） | `op→op` 335、`get→op` **285**、`const→op` 163、`set→sequence` 96、`op→set` 89、`sequence→sequence` 87、`set→op` **36**、`op→control` 31、`const→control` 27、其余控制/实例边少量 |
| 行步（Sequence 主干 Y 间隔） | 中位 224、p75 288、p90 416、max 704 |
| Y/语句带 | 中位 230、p75 318、p90 688、max 1008 |
| 列步（边 dx） | 中位 160、p90 512、p99 1069、max 1553 |
| 带内 dy | 中位 0、p90 256、p99 800、max 1329 |
| 跨带边（dy>288） | 96 / 1228 = 7.8%；样本多为 `ifelse→ifelse` 控制链与 `set→sequence` 锚定（后者属需修形态） |
| 最长路径深度 | 中位 8、max 47 |
| Set 根与其 Sequence 同行 | dy 中位 8、p75 18 |
| 命名读取 | `oklab_to_lch`：6 Set（`H`/`L`/`C`/`lab.a`/`lab.l`/`lab.b`）对 11 Get，10/11 命中本地 Set 名；`toe`（3 Set/4 Get）与 `lch_to_oklab`（5 Set/6 Get）各有 1 个 Get 读取函数形参 |
| 形参读取方式 | **每张有形参的函数图都用 `Get(形参名)` 读取形参**（`find_gamut_intersection_cusp_Upper_half` 的 `a/b/L1/C1/L0/cusp`、`toe(x)`、`srgb_transfer_function(a)`、`oklab_to_lch(lab)` 等全部命中），支持 I9/I10 的形态 |
| 函数内部 Set 的可见性 | 干净调用对里**调用方没有读取被调函数的内部 Set 名**（`srgb_to_oklab` → `linear_srgb_to_oklab`、`oklab_to_srgb` → `oklab_to_linear_srgb` 均为 NONE）；但 `find_gamut_intersection_cusp` 与 `find_gamut_intersection_cusp_Upper_half` **同名各自 Set** `cusp.C`/`cusp.L`，无法据此判定可见性。**未验证**：函数内部 Set 是否泄漏到调用方作用域；因此 §7.9.11 规定循环携带状态一律显式跨界 |
| 反例（需按 W15 修） | 少数图声明了 Set 但读取仍走 DAG 直连：`linear_srgb_to_oklab` 6 Set / 仅 1 Get（spanX 4640，全包最宽）、`oklab_to_linear_srgb` 9 Set / 3 Get、`get_ST_mid` 2 Set / 2 Get。这类图可作为"语句声明但不物化读取"的反面样本 |
| 函数化与调用 | `srgb_transfer_function`、`srgb_transfer_function_inv` 各 3 个调用点；`oklab_to_srgb` 内 7 个实例、`srgb_to_oklab` 内 4 个、`oklab_to_lch` 内 2 个；复合图用 PP + 实例 + `output` 组织（即"先函数化、再组装"的实际形态） |

用途：§7.10 的归一化跨度/节点预算与"读走上游 Get"规则的数值来源；同时作为"可复用逻辑打包为 Function Graph 并被多处调用"的现行证据（A8/§7.7）。
**未验证**：该包无原生渲染对照；`band_count` 以 Set/语句根数近似（含 Ifelse/While 的图未逐语句展开）；`get('lab')`、`get('x')` 等未命中本地 Set 名的 Get 属函数形参或需按 I2 核对；跨版本数值可能变化，阈值按 §11.7 的包络解释而非精确门槛。

### 11.8 乘法节点（`mul`/`mulscalar`）实测语料（2026-09-22）

来源：当前 SD 会话内**已加载的 4 个用户包**只读回读 —— `Fabrice_Fractal_Port.sbs`（raymarching 专业图）、`OKColor_LCH.sbs`、`loop whlie.sbs` 及其 `sdtext/` 副本；SD 16.0.3 + sd_mcp_plugin 3.3.0（未创建、未修改、未保存）。

| 项 | 实测结果 |
|---|---|
| `mul` 实例数 | **437**；端口 **`a` / `b`**；**437/437 为 float1×float1**（两侧上游输出均为 `SDTypeFloat`） |
| `mulscalar` 实例数 | **24**；端口 **`a` / `scalar`**；`a` = Float2(21) / Float4(2) / Float3(1)，`scalar` 恒为 Float |
| 向量所在端口 | **24/24 都在 `a`**，无一例放在 `scalar` |
| **泛型类型陷阱** | 21/24 的 `mulscalar.a` 端口类型是 Float2，但其上游节点读回为泛型 `SDTypeFloat`（`swizzle1` / `get_float1` / `sub`）→ 端口类型与上游类型字符串**都不能单独**作为维度依据 |
| `dot` | 10 处；**端口读回 Float2 而实际上游为 Float3**（端口类型不可信的另一反例） |
| 其它算术 | `add` 223、`sub` 58、`div` 56、`pow` 12；以 float1 为主，向量维有 `add` Float3/Float4 与 `sub` Float3 的少数实例；另有 `add` 端口读回 `Float` 而实际收到 Float2 的反例 |
| 标量变体清单 | `list_node_definitions(filter_text='scalar')` 仅返回 `sbs::function::mulscalar`；无 `divscalar`/`addscalar` |
| 端口标识（16.0.3 回读） | `mul`：id `a`/`b`，标签 `A`/`B`；`mulscalar`：id `a`/`scalar`，标签 **`Vector`**/**`Scale`**；`getPropertyFromId` 只解析小写 id，标签名全部返回 None；两者输出端口均为 `unique_filter_output` |
| 同维向量乘法 | `mul` **接受同维向量**（现场确认 2026-09-22）；语料无实例属采样局限，不代表不可用 → §7.5.1 按"可用"处理 |

用途：§7.5.1 选择表与维度判定流程、N20/I40/D34/T40 的证据基础；同时解释了为什么"照端口类型或上游类型选节点"必然出现 `mul`/`mulscalar` 混用，以及为什么用标签名做端口 id 会失败。
**未验证**：`mulscalar` 是否接受标量放 `a`、向量放 `scalar`（顺序颠倒）——规范按**不可交换**处理，不做探针；端口类型读回的泛型化行为是否随 SD 版本变化。

### 11.9 角度与向量组装节点（`atan2`/`vector2`/`cartesian`）实测（2026-09-22）

来源：Adobe 节点文档（`Arc tangent 2` 词条，现场确认）+ 同一批已加载参考包的只读回读；SD 16.0.3 + sd_mcp_plugin 3.3.0（未创建、未修改、未保存）。

| 项 | 实测结果 |
|---|---|
| 官方语义 | `Arc tangent 2` 返回 2D 向量 `Vector` **与水平方向的夹角（弧度）**；**不需要像通常 atan2 那样交换 x 和 y**；是 Cartesian 函数的反函数 |
| `atan2` 端口 | 输入 id **`a`**（标签 **`Vector`**，类型 **float2**），输出 float1；`getPropertyFromId('Vector'/'vector'/'input1'/'A')` **全部返回 None** |
| `atan2` 语料 | 4 处，**全部由 `vector2` 组装后接入 `a`**，无一例直接接 swizzle |
| `vector2` 端口 | 输入 id **`componentsin`**（标签 `In`）/ **`componentslast`**（标签 `Last`），均 float1，输出 float2；语料 23 处 |
| 分量顺序 | `componentsin` = 第一个分量 = x = **水平**；`componentslast` = 最后的分量 = y = **垂直**（标签顺序 + 现场构造记录 `componentsin=p.x, componentslast=p.y/0.2` 共同确认） |
| 单参 `atan` | **不存在**（`list_node_definitions(filter_text='atan')` 只返回 `sbs::function::atan2`）→ `atan(t)` 必须用 `atan2(a = vector2(1, t))` |
| `cartesian` | 定义存在（`sbs::function::cartesian`），与 `atan2` 互为反函数；语料 **0 实例**，端口 id **未回读**，使用前必须回读或探针 |
| 被推翻的旧记录 | 旧规范与两处 case study 曾写"源码 `atan(p.x,p.y)` 需输入 `p.yx`"——按官方语义这是**错的**（会把分量对调、角度镜像）。已更正为"按（水平, 垂直）语义组装，不交换" |

用途：§7.5.2 映射表、I17、T41、§7.1 端口速查表的证据基础。
**未验证**：`cartesian` 的端口 id 与参数语义（语料无实例，未回读）；`vector2` 在 3/4 分量拼接时的逐级顺序（语料使用了 `vector3(vector2(...), ...)`，但未逐端口核对标签语义）。

**后续补充（同轮，SD 自带文档）**：`cartesian` 的端口已由 SD 自带 Python API 文档给出，**不再是未验证项**——输入 id **`rho`（标签 Length，float）**、**`theta`（标签 Angle，float）**，输出 float2，官方公式 `Length × Float2(cos(Angle), sin(Angle))`，与 `atan2` 互为反函数（T42/§7.5.2）。

### 11.10 内建函数供给与数值语义实测（2026-09-22）

来源：SD 自带文件（**只读**）+ 官方文档原文，SD 16.0.3 + sd_mcp_plugin 3.3.0（未创建、未修改、未保存）：

| 项 | 实测/原文 |
|---|---|
| 原子函数节点总数 | **85**（`list_node_definitions` 全量目录与自带文档 `[i/85]` 块一一对应） |
| 原子语义权威出处 | `<SD>\resources\documentation\pythonapi\html\_sources\pythonapi\modules\sbs_function.rst.txt`，含每定义 **Label / Description / 端口 Label 与 Types**；等价副本 `<SD>\resources\python\tests\assets\test_module.txt` |
| 内建库 Functions | `resources\packages\functions.sbs`（另有 `3d_functions.sbs`、`functions_hash.sbs`），**171** 个函数图，分组 `Functions/Math`、`Functions/Trigo`、`Functions/Transforms` 等；通过 **instance 节点**调用，输入 id = `paraminput/identifier` |
| 原子层缺失项 | `round`/`frac`/`trunc`/`sign`/`clamp`/`saturate`/`step`/`smoothstep`/`fmod` 在 85 个原子定义中 **0 命中**（只存在于库 Functions） |
| `mod` | 原子 `sbs::function::mod`，标签 **Modulo**，端口 `a`(A) / `b`(**Divisor**)，描述仅 "returns modulo of entry value: mod(A,Divisor)" → 文档**未规定**负数约定；**实测为 floor 基**：`mod(−0.25,1)=0.75`、`mod(1.25,−1)=−0.75`、`mod((−0.25,1.25),(1,1))` 逐分量（§11.11） |
| `fmod` | 库函数 `Functions/Math/fmod`，标签 Fmod，端口 `a`(A)/`b`(B)，描述 "remainder of a/b with the **same sign as a**"（截断基） |
| `round_float1` | 库函数，标签 Round Float1，端口 `input`，描述 "**Rounds up when decimal is greater or equal than 0.5**"，实现 `floor(input + 0.5)` |
| `frac` | 库函数，标签 Frac，端口 `input`，实现 `input − floor(input)`（floor 基） |
| `sign` | 库函数，标签 Sign，端口 `x`(X)，描述 "**If X == 0, returns 1**" |
| `step` | 库函数，标签 Step，端口 `a`(A)/`x`(X)，描述 "one if **x ≥ a**" |
| `saturate` / `clamp` | 库函数，端口 `input` 及 `input`/`min`/`max`；官方 "0 if lower than 0, 1 if greater than 1" / "Returns Min or Max if the input is outside of the Min/Max range" |
| `truncate_float1_decimals` | 库函数，端口 `input` / `decimals`(**int1**，默认 1） |
| `mulscalar` 官方描述 | "multiplies each component of the input **Vector** by the same scalar value **Scale**"，`a` 仅接受 float2/3/4 → 印证 T40 与"float1×float1 必须用 `mul`" |
| `mul` 官方描述 | "multiplies two **same type** values: A×B" → 印证同维要求与"接受同维向量" |
| `passthrough` | 原子层标签是 **Dot**（reroute/portal 布局节点，不影响结果）；点积是 `dot`（标签 "Dot product"） |
| `cartesian` | 输入 `rho`(Length)/`theta`(Angle)，输出 float2 |
| 查找工具 | `scripts\lookup_sd_function.py`（原子 + 库函数两模式，支持 `--impl` 打印实现图连接、`--json` 导出、`--list-groups`） |

用途：§7.5.3/N27/I41/D35/T42/T43 与分支文件 `references/SD_BUILTIN_FUNCTIONS_v2.5.0.md` 的证据基础；同时修正了"SD 没有 round/fract/trunc"这一**因只查单一供给源而产生的错误结论**。
**已核对（见 §11.12）**：库函数**内部实现图已逐节点核对**（171 函数 / 2334 节点 / 2814 边；SD 活动对象与发行包 XML **0 处不一致**），台账见 `references/SD_LIBRARY_FUNCTIONS_v2.5.0.md` 与 `references/library_functions_v2.5.0.json`。
**未验证**：`truncate_float1_decimals`、`smoothstep` 的**数值行为**未做探针实测（其实现图已在台账中逐节点核对）；库函数在非 float1 类型组合下的多态具体化未逐函数实测；`3d_functions.sbs`、`functions_hash.sbs` 未纳入本次核对。

### 11.11 原生数值实测基线（真实 cook，2026-09-22）

方法：在 SD 进程内新建**未保存临时包** → 每项探针独立 PP 合成图 → `setOutputNode` 标记输出 → `graph.compute()` 真实求值 → `exportSDGraphOutputs(graph, dir, 'bmp')`（24bit **线性**）→ 解析第 0 像素并与**两种竞争语义**的预期编码值取最近者。探针 22 项，唯一匹配距离 ≤0.002，次优候选 ≥0.0137。明细与局限见 `references/NATIVE_PROBE_RESULTS_v2.5.0.md`，脚本见 `scripts/probe_sd_semantics.py`。

| 命题 | 实测结论 |
|---|---|
| 原子 `mod` 的负数语义（此前"未文档化/未验证"） | **floor 基**：`mod(−0.25,1)=0.75`、`mod(1.25,−1)=−0.75`、向量逐分量；控制项 `mod(5.5,2)=1.5` |
| `mod` vs `fmod` | 同一输入差 1.0：`mod(−0.25,1)=0.75` 而 `fmod(−0.25,1)=−0.25`（后者符号随被除数） |
| `mul` 同维向量 | `mul((1,2),(3,4))` 逐分量 → `dot((3,8),(1,1))=11` ✓ |
| float1×float1 | `mul(3,4)=12` ✓（`mulscalar` 的 `a` 不接受 float1） |
| 混维 | `mul(float2,float1)`、`mod(float2,float1)`、`mulscalar(a=float1, scalar=float2)` 全部 **静默 0** |
| 连线校验 | 上述 4 类混维连线 `newPropertyConnectionFromId` **全部 ACCEPTED**（不报类型错） |
| `round_float1` | `round_float1(−2.5)=−2`、`(2.5)=3` → `floor(x+0.5)`（半整数向 +∞，非"远离零"） |
| `frac` / `sign` / `step` / `clamp` / `saturate` | `frac(−0.25)=0.75`；`sign(0)=1`、`sign(−3)=−1`；`step(0.5,0.5)=1`（含等号）；`clamp(−3,0,1)=0`；`saturate(2)=1` |
| 最小 While（§7.9.10 模板） | 6 次迭代累加 → **21** ✓：Init 只执行一次、`cond` 真即停、body/cond 分支私有 Get、Sequence 定序、循环后用**新建 Get** 读终值全部成立 |
| 零迭代（此前列为"未定义/有歧义"） | **有定义**：Init 执行、body 不执行、状态保留 Init 值（实测 7）并可正常读出 |
| While `__constant__`（标签 `Constant`，官方称隐式最大迭代数，−1 视为禁用） | 设为 50 被接受且不改变语义（21）；**未**验证其实际截断行为（不主动构造死循环） |
| PP 内部图与输出 | 新建 PP 需 `newPropertyGraph('SDSBSFunctionGraph')`；输出是 `setOutputNode` 标记的普通节点（无 output 类型）；`getOutputNodes()` 为权威判据 |
| 导出 | BMP 为**线性**（线性候选距离 ≤0.002，sRGB ≥0.07）；精度 ±1/255 |

由此改写的规范条目：§7.5.3 规则 1（`mod` 直接可用）、§7.5.3 规则 9–11（混维行为不可依赖、连线不校验、原生探针）、T43（`mod` 实测）、新增 T44/T45/T46、§11.10（`mod` 负数语义转入"已实测"）、SOP-0A 步骤 3 与 **SOP-0B**、WHILE 基线（零迭代与最大迭代旋钮）。

### 11.12 内建库函数实现图逐节点核对（2026-09-22）

**目的**：后续调用库函数时有一份**可信台账**，而不是"文献说它大概是 floor 基"。

**三个独立视图**：

| 视图 | 取数方式 | 说明 |
|---|---|---|
| A 活动对象 | `scripts/dump_library_functions.py`（在 Designer 进程内遍历 171 个 `SDSBSFunctionGraph`） | 真值来源：`getNodes()`、真实属性值（常量按分量精确读取）、`getPropertyConnections()` 反查边 |
| B 发行包 XML | `scripts/verify_library_functions.py parse-xml <SD>/resources/packages/functions.sbs` | 另一条代码路径：`paramNode` / `connections/connection(connRef)` / `rootnode` / `paraminput`（含声明类型 id） |
| C 真实 cook | `scripts/probe_sd_semantics.py`（§11.11，导 BMP 读像素） | 数值闭环：网表求值须与实测一致 |

**核对结果（SD 16.0.3 + `resources/packages/functions.sbs`）**：

| 项 | 数值 |
|---|---|
| 库函数图 | **171**（26 组：Math 45、colorValues 32、Transforms 10、Random 9、Ranges 9、Tonemappers 5、easing 各 3、switch 各 3、Various 7、Trigo/Parity 各 3、typeConverters 2、Cycles 1） |
| 节点 / 边 | **2334 / 2814**（两个来源节点数完全一致；XML 侧另有 1 条陈旧边，见下） |
| 逐节点差分 | **171/171 PASS，0 处不一致**——比对维度：节点集合（定义+坐标）、边集合（源节点+端口→目标节点+端口）、**每个常量（float32 归一化）**、输出节点、形参 id 顺序、嵌套调用目标、形参声明类型 |
| 数值闭环 | 15 项断言：**SDK 网表与 XML 网表求值均**与 BMP 实测一致（`frac`/`round_float1`/`fmod`/`sign`/`step`/`clamp`/`saturate`） |
| 嵌套调用 | **71** 个库函数调用其它库函数；**没有任何库函数使用 While**；全库由 **62** 种原子定义构成（`mul` 229、`sub` 138、`swizzle1` 130、`get_float1` 129、`ifelse` 95…） |
| 类型字典 | `256`→float1、`512`→float2、`1024`→float3、`2048`→float4、`16`→int1、`32`→int2、`64`→int3、`128`→int4、`4`→bool1 |
| 无描述的函数 | 58（如 `Pi`/`2Pi`/`Roughness`/`Equality_*` 等只有标签）——台账按"描述为空"标注，不替 Adobe 编语义 |

**已解释的例外（不计为不一致）**：

1. **XML 省略默认常量 90 处**：`const_*` 取 0、`swizzle*` 取恒等排列时文件不写 `funcDatas`，活动对象会显式给出默认值；差分对每个省略项都按 `ATOM_DEFAULTS` 复核（值不符即报不一致）。
2. **XML 缺 1 个节点坐标**：`NotEqual_Float3` 的一个 `get_float3` 无 `gpos`，按（定义+常量）唯一配对后其余字段照常比对。
3. **1 条陈旧连接**：`distance_vec3` 的 `instance`（目标 `length_vec3`）上有一条连向 `input_v` 的边，而目标函数只声明形参 `v` → 文件历史残留，SD 装载时忽略、不影响求值；活动对象里不可见。**结论：不要照抄文件里的边。**

**取数陷阱**（已固化在 T47）：连接方向（`getInputPropertyNode()`=源、`getOutputPropertyNode()`=消费方）、`SDValueFloatN.get()` 结构化值与 `str()` 的 6 位小数截断、float32 亚像素坐标漂移、陈旧边。

**产物**：

- `references/SD_LIBRARY_FUNCTIONS_v2.5.0.md`——人类台账：三源核对说明 + 类型字典 + **全库 171 函数索引**（形参/默认值/输出/规模/嵌套调用/描述）+ **63 个计算相关函数的逐节点网表**（`Functions/Math` 45、`Math/Trigo` 3、`Math/Parity` 3、`Ranges` 9、`typeConverters` 2、`Cycles` 1）+ 嵌套调用表 + 陷阱与复现命令。
- `references/library_functions_v2.5.0.json`——机器可读台账：171 函数的形参（id/标签/类型/默认值）、节点（定义/类型/坐标/常量/`instance_of`）、边、输出、声明输出类型、调用关系。
- 生成器：`scripts/dump_library_functions.py`（SD 内）、`scripts/verify_library_functions.py`（parse-xml / diff / eval）、`scripts/render_library_catalog.py`（渲染上述两文件）。
- 临时查询：`scripts/lookup_sd_function.py --library --name "^fmod$" --impl` **默认读该台账**（不再现解析包 XML）；`--no-catalog` 才走 XML 解析路径（会打印告警，且因文件省略默认常量可能少显数值）。该工具的 XML 解析曾把 `<paramNode>` 的 uid 读成子元素之外而输出错乱网表，已修复；修复后两条路径与活动对象视图逐行一致（`fmod`/`clamp`/`round_float1` 抽查）。

**复现**：

```text
exec(open(r'<skill>\scripts\dump_library_functions.py', encoding='utf-8').read())   # 在 Designer 内
python scripts/verify_library_functions.py parse-xml <SD>/resources/packages/functions.sbs --out xml.json
python scripts/verify_library_functions.py diff sdk.json xml.json --json diff.json --verbose   # 期望 171/171 PASS
python scripts/verify_library_functions.py eval sdk.json xml.json                              # 网表 vs 实测
python scripts/render_library_catalog.py --sdk sdk.json --xml xml.json --diff diff.json --md <md> --json <json>
```

**未验证**：非 float1 类型组合下的多态具体化未逐函数实测；`smoothstep`/`truncate_float1_decimals` 的数值行为未探针；`3d_functions.sbs`、`functions_hash.sbs` 未纳入核对；活动对象的取值精度上限是 float32（超过该分辨率的差异无法用本流程判定）。
