# CRATE AT DUSK 回测门槛（Designer 16.0.3）

来源：用户提供的 `E:/SD_AI/CRATE AT DUSK/docs/SKILL_ITERATION_ISSUES.md`。以下是一次项目的实测与处置，不是所有版本/图类型的引擎定律。原文的“建议”不自动成为操作授权；跨包资源获取、删除探针图和原图改写仍按当前任务权限执行。

## 时间双通道：`$time` 与 `iTime` 共存

- `$time` 是系统 float 变量，Adobe 文档说明它在 Designer 内不能像普通参数那样改变，但 Substance Player 等 Engine 宿主可用它驱动动画；Player 的时间轴仅在图使用 `$time` 时出现。**不得为了 Designer 逐帧测试而删掉 `$time`，也不得宣称它在 Player 无用。** 来源：[Adobe 系统变量](https://experienceleague.adobe.com/en/docs/substance-3d-designer/using/substance-function-graphs/variables/system-variables)、[Player 时间轴](https://helpx.adobe.com/substance-3d-player/desktop/user-interface/the-user-interface.html)。
- 自定义 `iTime` 是手动/逐帧 cook 的显式输入，保留可设置、可回读的参数通路；它不是 `$time` 的同名别称，也不能自动取代 Player 的系统时间。推荐将二者接到一个明确选择器（如 `useManualTime ? iTime : $time`），正常播放默认 `$time`，验证时选 `iTime`。源代码只引用选出的 `effectiveTime`，避免函数间一部分读系统时间、一部分读手动时间。
- IR/报告记 `time_mode`、`$time` Get 身份、`iTime` 参数身份/连接、选择器默认值与每次 cook 的有效时间。用非零且不同的两个时间分别验证两路，不能用“`$time` 在 Designer 读 0”证明 Player 不可用；也不能凭 `getInputIdentifiers()==[]` 判 `iTime` 不存在（见 Morphing 回测）。未知版本/宿主对两路可用性仍须实际 probe。

## 构造和类型（01、02、06、14）

- **补充结构回查（用户复核）**：CRATE 的 `build/cadscene6.py` 第 8–14 行明确选择“下方语句直接使用上一条 `Set` 节点输出”，第 130/152/161/168/206 行等实际以 `S_T`、`S_CA`、`S_CAMP` 等 Set 句柄作为后续算子输入；Sequence 主干直到第 438–444 行才创建。故“有 18 条 Set 且有 Sequence”只说明存在两类节点，**不证明跨语句依赖按 Statement 模式读取**。参考包少量 `set→op` 统计亦不能授权把整张主图改成跨带 Set-DAG。
- 在用户选 A 的 Statement 图，预期形态为 `Set(x) → 同一输出可达 Sequence 链的先执行 In 路径；下方消费带 fresh typed Get("x") → 本带表达式 → 该链的后执行 Last 路径`。Get 通过名字/作用域解析，**不是把 Sequence 物理连入 Get 端口**；“Get 连上 Sequence”指它的输出经消费者接到后分支。逐边核对真实端口、两路径与输出可达性，不能凭上下位置/同名判断；再以非零/变化值验证名称、类型与作用域。旧同名 Get=0 记录未证明这条后分支路径实际存在，先修缺线再考虑异常；拓扑正确仍失败则记录待决冲突，不能静默退回 Set/RHS 直连。经用户同意且数值验证的 Sequence-value transport 可作显式例外。
- IR 中每个 `sequence_ordered_get` 记录 `set_node/get_node/sequence_node/output_nodes/wiring_edges`，逐边核验 `In` 与 `Last` 两分支和输出闭包；缺少 Get→消费者→`Last` 时标 `RS_GET_SEQUENCE_TOPOLOGY` 并先修线。人工四布尔摘要不能代替真实边回读。
- 静态审计逐条比对 `source_statement`/`target_statement`：跨语句 `Set`/旧 RHS/表达式 → 下方普通算子，即使整张图另有 Sequence 主干，也判 `RS_CROSS_STATEMENT_DAG`；`Set→自己的 Sequence` 与 Sequence 主干链不误报。`mode=statement` 的 IR 缺少 `statement_edges` 审计即 `RS_STATEMENT_EDGE_AUDIT_MISSING`。见 `scripts/runtime_semantics.py::validate_ir`。当前 CRATE 项目目录在本次 skill 迭代中仅被读取，**未改写现有工程图或构建脚本**。

- I42：把每个 `vec2/3/4`、`ivecN`、swizzle 构造的源分量与目标端口逐项登记。`vectorN.componentsin` 接前 N−1 个有序分量，`componentslast` 接最后一个；`v3(v2(x,z),y)` 不等于 `(x,y,z)`。非对称分量用例必须能区分每一对交换，不能只测近似相等的分量。纯快照检查器：`scripts/project_validation.py::check_vector_slots`。
- I43：每个 `get_floatN` 的 N 要等于**本作用域**的正式形参、Set 或已验证系统变量声明维度，且 Get 名称必须声明；维度不匹配在 16.0.3 可静默读 0。先运行 `check_get_dimensions` 再跑数值 oracle；其输入是回读后解析好作用域的 `formals/sets/builtins/gets` 快照，不能拿静态 PASS 代替运行时顺序/遮蔽检查。
- I16：在 IR 中登记每个 GLSL 标量广播，显式降级为同维常量/向量后再连 `add/sub/div/min/max/pow/mod`。`vecN*scalar` 优先按 §7.5.1 使用正确 `mulscalar`，但 Sequence-derived 向量遵 RS6 用同维 `mul`；`lerp(a,b,x)` 的 `x` 本为权重标量，不应过度广播。扫描普通二元算术的两侧解析维度，不同维直接 FAIL，即使 SDK 接受连接。
- I44：枚举每个矩阵/旋转在源码的**所有应用点**（位置、法线、软法线、光线、UV 等），IR 中逐点映射和用非对称输入独立数值测试。CRATE 的 `cubeRot` 被用于三处，漏掉顶点位置时轮廓仍近似正确，却造成大面积内部偏差。不要凭 `T=0` 推断变换是单位阵；该项目 `rotZ(0.3)` 仍非单位阵。`check_transform_application_coverage` 检查应用点 ID 的覆盖。

## 函数供应、根与循环（03–05、08、11–12）

- Adobe 原子节点定义表与 Functions 库是两种供应，不是“有库函数文档 = 当前会话已拿到活 resource”。先在当前包/版本查实际可实例化的 resource，创建一个最小实例并回读端口与调用点值。Adobe SDK 的 `loadUserPackage(...); findResourceFromUrl(...)` 只是**候选路径**（[SDK 实例示例](https://adobedocs.github.io/designer-python-api/guides/examples/instance/)），本项目未证明 `functions.sbs` 在当前 MCP 会话可达；不能写成已验证操作。不可达时可记录 `LIBRARY_INSTANCE_UNREACHABLE:<实际尝试>`，按 Adobe 定义显式构造并以独立 oracle 验证，不得空称“优先库函数”已落实。跨包 formal 的真实值仍须在首个调用点测试（`REAL_PROJECT_VALIDATION.md`）。
- GLSL 常用函数先查 `SD_BUILTIN_FUNCTIONS_v2.5.0.md` 的可用性表及当前图定义/资源，再做语义选择。`normalize`/`cross`/`asin`/`acos` 不应猜原子 id；该项目查 16.0.3 两源后，`normalize` 见库，`cross` 的现有库项是 vec2 而非通用 vec3，`asin`/`acos` 两源未找到。缺失只能按所需域构造、处理边界并数值验证；不要把项目未找到推成未来版本不存在。
- 16.0.3 的普通 Function Graph 曾出现 `while` 直接 marked root：`getOutputNodes()` 有值而调用方全 0；经纯算子组装为 float4 后恢复。Function 根默认经类型保真的纯算子桥接，并在首调用点验证；`while/sequence/set` 直根若要保留，必须当前会话最小探针 + 调用点数值证据。不要误并入 PP float2/float3 根限制。
- 若目标类型系统不能表示固定循环的迭代载体（例：仅进行 `A[i]` 数组下标赋值且无数组类型），可记 `LOOP_UNROLL_EXCEPTION:TYPE_SYSTEM_NO_ARRAY`，静态展开各轮并保留语句/求值顺序；不得声称完全遵循 While 规范。能表达载体的循环仍默认 While，不得借本例普遍展开。
- Expression 模式（包括 A 方案内真正纯表达式的 Function Graph）无 Statement band 语义；`nodes_per_statement` 与 `Y_per_statement` 记 `N/A(expression)`，用节点数、最大表达式深度、每层宽度/扇出及 `X_per_level` 做结构复核，不因 1 带高比值强加 Set/Sequence。16.0.3 的 `dot(float3,float3)` 在本项目按非对称值正确返回 float1；不可信的是多态端口的维度读回，不是 `dot` 节点整体不可用。

## 单元用例、诊断与证据（07、09–10、13、15–17）

- 分支函数的 `BRANCH_COVERAGE` 从源码控制流生成：每个 `if` 真/假、每条 `return`、每个三元分支，及关键边界至少一个**判别**用例；未覆盖项单列，不靠手挑几个“看起来合理”的样本升级 PASS。CRATE 的外层 `q.x<6 && q.y<6` 守卫漏译，角板例恰巧通过。`check_branch_coverage` 只检查已列路径覆盖，不自动证明分支用例确有判别力。
- 改图诊断抽头（SOP-0C）须在授权范围内。先保存真实 marked-root 对象/身份与图指纹；从根沿**真实输入边反向追溯**目标节点，禁止仅凭位置、类型或同名定义猜节点。优先独立诊断图并联调用；需临时换输出时，确认类型由上游声明固定，或保留确定多态类型的下游消费路径。`min/max/add/ifelse/swizzle` 等直接换为唯一根可能改变类型解析，读数不是原值。
- 抽头到 BMP 必须记录每个“源分量 → 中间 swizzle → BMP 通道”的 1:1 映射，并做已知常量/均值量级自检。单条抽头结果只能提出假设；写入根因结论前须有**不经过同一抽头**的独立证据（另一数据路径或真实成图分区统计）。CRATE 两次错误抽头都曾支持错误的“立方体缺失”诊断；实图掩码召回最终反证。
- 临时节点/图记所有权与清理清单；恢复保存的根对象，删除临时资源后回读资源表与逻辑指纹。MCP 请求超时/中止后写入可能留存、批内 delete 可能未持久化，先只读检查再独立清理；≤20 cook/批是该项目的操作建议，不是平台保证。
- 验收 oracle 单位表优先**当次从活模块重算**。缓存表必须有生成源码哈希和表文件哈希，并与当次文件实算匹配；任一不匹配只可 cross-check。`check_oracle_provenance` 是文件哈希门，无法代替源码分支完整性或运行命令复现。
- BMP 数值抽头的量化误差须换算回原值。8-bit direct 编码的一 LSB 为 `1/255`；`enc=0.5+v/(2S)` 仿射编码的一 LSB 为 `2S/255`。先记录值域、`enc`、`dec`、容差及下游量化步长；若容差接近下游台阶，函数 PASS 不能解释一个量化级的残差。被测值严格落在 `(0,1)` 且离端点留出量化余量时优先 direct；零/一边界另测，有负数/越界则仿射但不得裁切。`check_probe_precision` 用较保守的“容差 ≤ 下游步长/4”作为高精度归因门，不是原生引擎定律。
