# While / Set / Get 官方语义基线

更新时间：2026-09-22。
用途：为 `sd-pixelprocessor-agent` 提供 While、Set/Get/Sequence、循环格式降级、While 连接规划和 Pixel Processor 的官方语义基线。项目实测若与本文件冲突，先视为当前结构/环境异常，不直接覆盖官方已明确行为。

## 1. Adobe 官方已明确

### 1.1 Sequence

Adobe `Control nodes`：Sequence 确保一部分图先于另一部分计算；这对变量创建、读取和更新的状态控制是关键。`In` 先执行，`Last` 后执行，Sequence 输出来自后者。

### 1.2 Set / Get

Adobe `Using the Set/Sequence nodes`：Set 创建/更新变量，Sequence 用于确保 Set 完整执行后再计算后续分支。Sequence 可以链式使用，以保证先设置变量、后更新、再读取最终值。

Adobe `Variables / Get`：Get 按类型读取当前作用域变量；在复杂控制流中必须注意 Set/Get 顺序，Designer 可报告 `Get before Set`。由 Set 创建的变量可能不出现在 Get 下拉列表中，但可手动输入名字，前提是类型与作用域正确。

### 1.3 While

Adobe `Control nodes`：

- Init 在第一次迭代前执行一次；
- Exit Cond. 每轮重新计算；`Exit Cond. == True` 表示停止；
- Loop Body 每轮重新计算；
- 循环结束后，While 输出 Loop Body 最后一次迭代的结果；
- 变量在迭代之间保留，并可在 Exit Cond. 中访问；
- Max iterations 与 Exit Cond. 谁先满足谁终止；`-1` 可取消迭代上限，但可能导致无限循环和 Designer 无响应；该旋钮是 While 节点的 `__constant__` 属性（标签 `Constant`），**实测设为有限值（50）被接受且不改变语义**（§11.11）；
- 连接到 Exit Cond. 与 Loop Body 分支的节点不能同时连接到图的其它分支。

### 1.4 Pixel Processor

Adobe `Pixel processor`：Pixel Processor 为每个输出像素并行执行同一个 Function Graph；每个像素不知道邻居的计算结果。因此 While 状态属于当前像素这一次函数执行，不是跨像素共享状态。

### 1.5 官方 Loop 使用场景

Adobe Substance 3D Designer 13.0 发布说明说明 loops 用于 Function Graph，主要使用位置包括 Pixel Processor、FX-Map、Value Processor。Adobe Substance 3D 官方视频 `While Loops in Substance 3D Designer` 也展示了 Pixel Processor 中的 While 使用。

## 2. Skill 派生硬规则

这些规则是对官方语义的工程化落地：

1. `Set x = expr` 后，变量 x 的版本在 Set 处切断；后续语句通过新的同类型 `Get("x")` 读取，不复用 Set 前 RHS 数据线。
2. `x += y` 的 RHS 必须先 `Get("x")`；Set 更新后若同一 block 还读取 x，先用 Sequence 保证 Set 完成，再新建 Get。
3. Exit Cond / Loop Body 计算闭包按 branch-private 处理。需要相同常量、Get、运算或 Function 实例时，在另一分支/环外新建独立节点，不共享节点实例跨分支。
4. 环外取得循环状态：先用 Sequence 或明确数据依赖证明 While 已完整执行，再新建 Get(state)。这与“把 Body 内部节点跨线到外部”不同，后者禁止。
5. While 直接输出只代表最后一次 Body 返回值。零次迭代时的直接输出值官方未说明；**已实测（§11.11 / `NATIVE_PROBE_RESULTS_v2.5.0.md`）**：Cond 首轮即为真时 Init 仍执行一次、Body 不执行、状态保留 Init 值，且循环后经 `Sequence(while → 新建 Get)` 能正常读出该值（实测 7）——**零迭代有定义**；仍依赖该行为时应按 SOP-0B 在当前环境复测。
6. 源码中的一切循环格式都降级为结构化 While；固定次数、编译期常量次数不默认 unroll。展开只在显式例外下允许（用户明确要求 / 当前环境已证明引擎阻塞 / 交付目标要求无 While），并记录 `LOOP_UNROLL_EXCEPTION:<reason>`。
7. 两个循环读写同名状态时，必须用 Sequence 明确整段循环之间的执行顺序。
8. Adobe 引擎允许 `Max iterations = -1` 取消上限；这是引擎能力。Agent 安全策略默认使用有限可解释上限，仅当退出条件有可证明界限或用户明确要求时允许 `-1`，并记录风险。
9. 除非已有记录的 `LOOP_UNROLL_EXCEPTION`，一个源码循环对应一个 While；一轮迭代 = loop 闭包的一次执行，不是一批复制节点。嵌套循环每级一个 While。
10. `do-while` 必须保留"至少执行一轮"：Init 建立 `firstPass` 标志（推荐，体只建一份）或 Init 内复制一轮体。
11. `break` 用出口标志并入 Exit Cond（`not C or brk`），并把 break 之后的语句包进 `ifelse`；`continue` 用标志包住其后的语句；**`for` 的增量必须留在 continue 包装之外**，否则计数器不更新会产生死循环。
12. 每个循环单独推导 `Max iterations`：静态界用界值；非 1 步长/浮点界用可证明上界；动态界用可解释安全帽；`for(;;)` + break 同样必须给出可证明上界或保守帽。
13. While 三输入 `init`/`cond`/`loop` 必须在交付前断言各有**实际源连接**；端口存在不等于接好。
14. 端口名 `init`/`cond`/`loop`/`__constant__` 是固定的，但类型多态；类型必须按实例回读核实，不能按定义默认值推断。
15. `__constant__`（Max iterations）是节点属性而不是连线；它不构成 While 的第四个数据子区域，但必须记录取值与来源。
16. 新建或修复 While 时默认按 spec §7.9.10 的**标准连接模板**（角色固定、tail Get 独立、常量私有、三子区域齐全）实现；偏离必须逐项记录理由。

## 3. 循环格式降级与 While 连接规划

### 3.1 格式 → While（摘要）

| 源码格式 | SD While 表达要点 |
|---|---|
| `while (C)` | Cond = `not C`；初值在 Init；体在 loop |
| `for (i=a; C; S)` | Init `Set i=a`；Cond `not C`；loop 尾部 `Set i=S` |
| `do { B } while (C)` | Init 加 `firstPass=true`；Cond `not firstPass and not C`；loop 尾部 `Set firstPass=false` |
| `break` | Init `Set brk=false`；Cond `not C or brk`；break 处 `Set brk=true` + 其后语句包 ifelse |
| `continue` | `Set cont=true` + 其余语句包 `ifelse(not cont, ...)`；`for` 的增量在包装之外 |
| 嵌套循环 | 每级一个 While；内层 While 是外层 loop 闭包中的一条语句 |
| 多出口 | 每个出口一个标志，全部并入 Cond 的或组合 |
| `for(;;)` | 无 Cond → 由 break 标志导出，且必须给有限上限 |

完整格式清单（含空体、宏展开、非 1 步长、多出口）与端口级规划见 `SD_PixelProcessor_AGENT_SPEC_v2.5.0.md` §7.9。

### 3.2 While 端口与连接规划（16.0.3 实测）

| 项 | 实测结果 |
|---|---|
| 定义 id | `sbs::function::while` |
| 输入端口 | `init`、`cond`、`loop`、`__constant__`（Max iterations，int1） |
| 输出端口 | `unique_filter_output` |
| 端口类型 | 多态：同一实例 `init`/`cond` 为 bool、`loop` 与输出为 float；类型必须按实例核实 |

规划顺序与断言：

1. `init`：单语句或 Sequence 根；初始化全部携带状态；不放每轮才该执行的语句。
2. `cond`：纯判定闭包、bool、True 停止；移植继续条件必须取反；不写状态，不与 loop 共享节点。
3. `loop`：单语句或 Sequence 根，按源码顺序；尾部放增量 Set。
4. `__constant__`：默认有限、可解释；`-1` 仅按 W7 的“可证明退出界 / 用户明确要求”例外使用，并记录其为引擎无限上限模式。
5. 闭包 branch-private：Cond/Body 节点不得同时连接其它分支；需要同值就新建节点。
6. 环外读状态：先证明 While 已完成，优先走 While/显式纯值路径；若使用 Get 必须验证该作用域确实读取到循环写入；禁止跨接 Body 内部节点。
7. 交付前断言三输入各有实际源连接、`cond` 为 bool、上限有限（对应 spec I34–I36）。
8. 端口 id 与类型来自实例回读，不按定义默认值推断。

当前环境观测到的既有实例形态：图 `loop01` 节点 `1582207887`，`__constant__ = 32`，`init`/`loop` 由 Sequence 驱动、`cond` 由比较节点驱动（该图语义未在本会话验证）。

### 3.3 标准连接模板（推荐，16.0.3 实测）

完整模板（角色清单、端口级连接链、语义约定、几何、建图顺序、模板使用前置）见 spec **§7.9.10**；此处只给骨架：

```text
while.init <- init_seq            # sequence(seqin=set(初值) -> seqlast=set(初值))
while.cond <- cmp                # bool；边界常量接 a、活状态接 b（lr: A<B）
while.loop <- body_seq           # sequence(seqin=inner_seq, seqlast=get_tail)
inner_seq: set(x)=f(get_x, ...) -> set(y)=g(get_y, ...)
```

模板要点（新建 While 默认照搬）：

1. Init 只放初值，RHS 不含循环自身状态的 Get。
2. cond 只读不写，且与 loop 闭包不共用 Get 实例。
3. Body 顺序用（可嵌套）Sequence 表达；每个 `set.value` 起手用新建 Get；同一 block 再次读同一变量时**再新建** Get。
4. Body 主干 `seqlast` 放读取"本轮结束后状态"的独立 Get，作为 While 直接输出（不需要时明确记为未使用）。
5. 同一数值在不同语句/分支用独立常量节点。
6. 三个子区域（init 上、cond 同行左侧、loop 下）不得为压缩高度而打散。
7. 模板使用前置：存在最终输出节点（`getOutputNodes()` 非空；PP 内部图的输出由 `SDSBSFunctionGraph.setOutputNode(node, True)` **标记任意普通节点**实现，不存在 "output 节点类型"，见 T45）、无悬空 Get、PP 已接入复合图目标输出——三条缺一即不得声称该 While 可交付。

### 2A. 最小 While 模板端到端实测（16.0.3，真实 cook）

`scripts/probe_sd_semantics.py` 的两项探针（§11.11）：

| 探针 | 构造 | 结果 |
|---|---|---|
| `while_sum` | Init `Sequence(Set(acc,0), Set(i,0))`；Cond `lr(5.0, Get(i))`；Body `Sequence(Set(acc, Get(acc)+Get(i)+1), Set(i, Get(i)+1))`；循环后 `Sequence(While → 新建 Get(acc))` | 实测 **21** = 1+2+3+4+5+6 → Init 仅一次、`cond` **真即停**、cond/body 分支私有 Get、Sequence 定序、循环后用**新建 Get** 读终值**全部成立** |
| `while_zero` | Cond 首轮为真（`lr(0,1)`），Init `Set(acc,7)` | 实测 **7** → 零迭代有定义（见 §2 规则 5） |

即：§7.9.10 模板与本节规则 1–15 在**真实求值**下成立，不再是纯静态推演。

## 4. 不再作为通用规则的历史结论

Accretion 首次实跑曾出现“While 携带逐像素状态失败”的最小复现。由于：

- Adobe 官方明确支持 Pixel Processor 中的 Function Graph loops；
- 官方说明变量会跨迭代保留；
- 同一轮调试曾存在 `mulscalar` 误用导致诊断污染；

该结果只保留为 16.0.3 特定实验的历史异常。未来任务只有在遵守官方规则后仍发生异常时，才运行最小能力探针。

同样，历史上的“`$size` 在 While 内为 0”和“嵌套 While 必然返回 0”已撤回，不能复用。`Morphing Abstract_text1` 的 16.0.3 回测还测到内层 Body 更新外层携带状态后，两轮外层迭代的编码结果约为 22（预期 22）；这是该图的正例，不代表任意跨作用域 Get/Set 都可靠。详见 `MORPHING_RETEST_GATES.md` P2。

## 5. 参考资料

- Adobe Experience League — Control nodes  
  https://experienceleague.adobe.com/en/docs/substance-3d-designer/using/substance-function-graphs/nodes-reference-for-substance-function-graphs/atomic-function-nodes/control-nodes
- Adobe Experience League — Using the Set/Sequence nodes  
  https://experienceleague.adobe.com/en/docs/substance-3d-designer/using/substance-function-graphs/fx-maps/using-substance-function-graphs-in-fx-maps/using-the-set-sequence-nodes
- Adobe Experience League — Variables / Get nodes  
  https://experienceleague.adobe.com/en/docs/substance-3d-designer/using/substance-function-graphs/nodes-reference-for-substance-function-graphs/atomic-function-nodes/get-nodes
- Adobe Experience League — Get a variable value  
  https://experienceleague.adobe.com/en/docs/substance-3d-designer/using/substance-function-graphs/variables/get-a-variable-value
- Adobe Experience League — Pixel processor  
  https://experienceleague.adobe.com/en/docs/substance-3d-designer/using/substance-graphs/nodes-reference-for-substance-graphs/atomic-nodes/pixel-processor
- Adobe Substance 3D official YouTube — While Loops in Substance 3D Designer  
  https://www.youtube.com/watch?v=Ggoy8G90oDI
- Adobe Community announcement — Designer 13.0.0 / Substance Engine v9 loops  
  https://community.adobe.com/announcements-48/designer-13-0-0-spline-and-path-nodes-portals-loops-etc-big-update-for-material-artists-626105


## Runtime safety

Official While semantics remain the structural baseline, but generated graphs must also satisfy the field-verified runtime overlay:

- `SAFETY_INVARIANT_002`: a Loop Body must not consume a Sequence produced outside that body; this pattern has hung the Designer main thread in a real project.
- Within a body, Set/read-after-write ordering uses body-private Sequence. A post-Set value is carried by that statement Sequence output; do not assume a bare same-name Get returns the new value.
- Values entering the body are reconstructed as body-private pure values/formals/constants/verified loop-local reads.
- A While/Sequence/control node is not used as a marked final Function/PP output; bridge through a pure identity operator.
