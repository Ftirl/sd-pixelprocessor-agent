# SD 原生数值实测基线

本文件是**实测证据**，不是规则文本。规则见规范 §7.5.1 / §7.5.3 / §7.9.10 与 §11.11。
所有数字来自 **Substance Designer 16.0.3 + sd_mcp_plugin 3.3.0**，在同一进程内真实 cook 后导出像素读回，**不是看图猜测**。

**版本门控**：这些测量值是 16.0.3 的已验证基线，不自动代表 16.0.5。在 16.0.5 或其它未验证版本中，按 `COMPATIBILITY_MATRIX_v2.5.0.md` 先运行同版本探针，再把结果提升为 VERIFIED。

本文件中的数值是既有 16.0.3 原生 cook 证据的保留记录；本次打包环境没有可运行的 Designer 16.0.5，因此没有伪造或补写 16.0.5 数值。当前探针脚本在原 22 项之外新增 `coord_pos_x` 与 `coord_size_x`，但本文件不声称这两项已有 16.0.3 实测结果；依赖 `$size` 的写操作必须在目标会话运行当前探针。

## 1. 方法与可信度

历史 22 项基线的流程（由当时版本的 `scripts/probe_sd_semantics.py` 一次执行，2026-09-22）：

1. 新建**本次运行独占的未保存临时包**；不复用/清空任何已有未保存包，并在结束时只删除本次登记的探针图；
2. 每项探针独立合成图：`Pixel Processor` → `sbs::compositing::output` → 标记为 graph output；
3. PP 内部图用 `pp.newPropertyGraph(pp.getPropertyFromId('perpixel', Input), 'SDSBSFunctionGraph')` 实体化；
4. 结果用 `SDSBSFunctionGraph.setOutputNode(node, True)` 指定（**没有 output 节点类型**）；
5. `graph.compute()` 真实求值（阻塞至完成）；
6. `sd.tools.export.exportSDGraphOutputs(graph, dir, 'bmp')` 导出；
7. 解析 BMP 第 0 像素，比较**两种竞争语义**的预期编码值，取最近者并报告距离。

可信度要点：
- 导出的 BMP 为 **24bit 线性**（实测：线性候选距离 0.0005–0.0020，sRGB 候选 0.07–0.29）→ 8bit 量化误差 ≤ 1/255；
- 每项探针的**唯一匹配距离 ≤ 0.002**，次优候选距离 ≥ 0.0137；
- 负值/大批量结果一律先用仿射编码（`v*0.5+0.5`、`v/32`、`v*0.25+…`）压进 `[0,1]` 再读，解码可逆；
- 编码链本身只用已判定正确的节点（float1×float1 用 `mul`），避免"用被测对象测被测对象"。

## 2. 原子 `mod`：**floor 基（GLSL 语义）** —— 实测推翻"未验证"

| 探针 | 表达式 | 实测 8bit | 解码值 | 判定 |
|---|---|---|---|---|
| `mod_pos` | `mod(5.5, 2)` | 96 | 1.5 | 控制项：两派一致，节点工作正常 |
| `mod_neg_a` | `mod(−0.25, 1)` | 223 | **0.75** | **floor 基**（截断基应为 −0.25→0.375） |
| `mod_neg_b` | `mod(1.25, −1)` | 32 | **−0.75** | **floor 基，且符号随除数** |
| `mod_vec_neg` | `mod((−0.25,1.25),(1,1))` | 64 | dot = **1.0** | 向量**逐分量** floor 基（截断基 dot 应为 0） |

结论：`a − b*floor(a/b)`，与 GLSL `mod` 一致，**与 C/HLSL `fmod` 不同**：

| 对照 | 实测 |
|---|---|
| `mod(−0.25, 1)`（原子） | **0.75** |
| `fmod(−0.25, 1)`（库函数） | **−0.25** |

→ 迁移 GLSL `mod` 直接用原子 `mod`；迁移 C/HLSL `fmod` 用库函数 `fmod`；**二者不可互换**（同一输入差 1.0）。

**混维陷阱（实测）**：`mod(float2 A, float1 Divisor)` → **静默返回 0**（既非广播也非报错）。同维是硬要求（与 `mul` 相同）。

## 3. 维度与连线：**SD 不在连线时报类型错误，cook 行为不可依赖**

| 连线 | `newPropertyConnectionFromId` | cook 结果 |
|---|---|---|
| `mulscalar.a ← float1`（标量接 Vector） | **ACCEPTED** | 内部图整流为 0 → 输出 0 |
| `mulscalar.scalar ← float2`（向量接 Scale） | **ACCEPTED** | 同上 |
| `mul.a ← float2`、`mul.b ← float1`（同节点混维） | **ACCEPTED** | **0** |
| `mulscalar(a=float1, scalar=float2)`（顺序颠倒） | **ACCEPTED** | **0** |
| `mulscalar(a=(1,2), scalar=4)`（正确） | ACCEPTED | dot = **12** ✓ |
| `mul((1,2),(3,4))`（同维向量） | ACCEPTED | dot = **11** ✓（逐分量 (3,8)） |
| `mul(3, 4)`（float1×float1） | ACCEPTED | **12** ✓ |

结论：
1. **连线成功 ≠ 类型正确**；`newPropertyConnectionFromId` 不会因维度不符抛错。
2. 本表列出的 `mul`/`mulscalar` 混维样本结果为**静默 0**；这不是可推广到所有算子的统一语义。rain_text 的 16.0.3 实测显示混维 `add`/`sub`/`pow` 还能产生部分或恒等式外观，且结果形状跟随输入 `a`。因此无论结果是 0 还是看似合理，都必须靠 §7.5.1 的维度判定流程在创建前解决（I40）。
3. `mul` 接受同维（含向量×向量，逐分量）；float1×float1 走 `mul`；向量×标量只能 `mulscalar`(《Vector》=向量端，《Scale》=标量端)。

## 4. 库函数语义（`resources/packages/functions.sbs`）—— 实测

| 探针 | 表达式 | 实测 8bit | 解码 | 判定 |
|---|---|---|---|---|
| `round_half_neg` | `round_float1(−2.5)` | 64 | **−2** | `floor(x+0.5)`：半整数向 +∞（"远离零"应为 −3） |
| `round_pos` | `round_float1(2.5)` | 191 | **3** | 同上，正半整数向上 |
| `frac_neg` | `frac(−0.25)` | 223 | **0.75** | floor 基（`x−floor(x)`），**不是** `fmod(x,1)` |
| `fmod_neg` | `fmod(−0.25, 1)` | 96 | **−0.25** | 符号随被除数 |
| `sign_zero` | `sign(0)` | 127 | **1** | 官方"X==0 返回 1"成立，**非数学 0** |
| `sign_neg` | `sign(−3)` | 127 | **−1** | 负号正常 |
| `step_edge` | `step(a=0.5, x=0.5)` | 127 | **1** | 边界**含等号** `x ≥ a` |
| `clamp_lo` | `clamp(−3, 0, 1)` | 64 | **0** | 下限生效 |
| `saturate_hi` | `saturate(2)` | 127 | **1** | 上限生效 |

端口与资源标识（实测，9 个库函数全部可实例化）：

| 库函数 | resource identifier | 输入 id | 输出 id |
|---|---|---|---|
| `round_float1` | `round_float1` | `input` | `unique_filter_output` |
| `frac` | `frac` | `input` | `unique_filter_output` |
| `fmod` | `fmod` | `a`, `b` | `unique_filter_output` |
| `sign` | `sign` | `x` | `unique_filter_output` |
| `clamp` | `clamp` | `input`, `min`, `max` | `unique_filter_output` |
| `saturate` | `saturate` | `input` | `unique_filter_output` |
| `step` | `step` | `a`, `x` | `unique_filter_output` |
| `smoothstep` | `smoothstep` | `a`, `b`, `x` | `unique_filter_output` |
| `truncate_float1_decimals` | `truncate_float1_decimals` | `input`, `decimals` | `unique_filter_output` |

→ 库函数实例的输入 id 就是**形参名**（与 `paraminput/identifier` 一致），输出 id 实测为 `unique_filter_output`；仍须按 T39/I39 回读登记，不得推断。

## 5. 最小 While（§7.9.10 模板）—— 端到端实测

| 探针 | 构造 | 实测 | 判定 |
|---|---|---|---|
| `while_sum` | Init `Sequence(Set(acc,0),Set(i,0))`；cond `5 < i`；body `Sequence(Set(acc,Get(acc)+Get(i)+1),Set(i,Get(i)+1))`；循环后 `Sequence(while → 新建 Get(acc))` | 167 → **21** | 迭代 6 次累加 1..6=21：**Init 只跑一次、cond 为"真即停"、body 分支私有 Get、Sequence 定序、循环后用新建 Get 读终值全部成立** |
| `while_zero` | cond 首轮即为真（`lr(0,1)`） | 56 → **7** | **零迭代有定义**：Init 执行、body 不执行、状态保留 Init 值，且循环后可正常读出（此前列为"未定义/有歧义"） |
| `while_maxiter` | 同上并把 While 节点 `__constant__`（标签 `Constant`，官方称隐式最大迭代数，−1 视为禁用）设为 50 | 167 → **21** | 该属性可设且不破坏语义 |

While 节点输入 id（实测）：`init`(Init) / `cond`(Exit cond.) / `loop`(Loop body) / `__constant__`(Constant)。

## 6. 构建与验证的 API 事实（实测）

| 事实 | 说明 |
|---|---|
| 新建 PP **没有**内部图 | `pp.getReferencedResource()` 返回 None；须 `pp.newPropertyGraph(pp.getPropertyFromId('perpixel', Input), 'SDSBSFunctionGraph')` |
| PP 的 `perpixel` 属性 | label `Per pixel function`，类型 float4，`isFunctionOnly=True`；内部图就是它的 property graph |
| 图输出**不是节点类型** | 用 `setOutputNode(node, True)` 标记任意普通节点；语料实测输出节点是 `pow`、`vector4`、`instance` 等；`getOutputNodes()` 才是权威判据（`loop whlie.sbs` 的 PP 内部图 `getOutputNodes()==0` → 未标记输出，非"缺少 output 节点"） |
| 合成图输出节点 | 定义 `sbs::compositing::output`，输入 id `inputNodeOutput`；`graph.setOutputNode(node, True)` |
| **原生数值验证通路** | `graph.compute()` + `sd.tools.export.exportSDGraphOutputs(graph, dir, 'bmp')` → 24bit **线性** BMP；可在进程内完成"真实 cook 的数值验证"，无需保存工程、无需外部渲染器 |
| 插件能力边界 | `sd_mcp_plugin` 不实现 `newPropertyGraph`，因此**无法**通过 MCP 工具新建 PP 内部图；需要 SDK（`execute_sd_code`）补足 |

## 7. 局限（不得夸大）

- 8bit 量化：单值精度约 ±1/255；本文件所有判别间距 ≥ 0.06（多数 ≥ 0.25），结论不受影响；
- 仅覆盖列出的输入点，未做**全域**扫描：`mod` 的中间舍入、极大/极小值、非规格化数未覆盖；
- ~~库函数只验证了**外部语义**，未逐节点核对内部实现图~~ → **已补齐**：171 个库函数的实现图已逐节点核对（活动对象 vs 发行包 XML，171/171 一致），见 `references/SD_LIBRARY_FUNCTIONS_v2.5.0.md` 与规范 §11.12；
- `truncate_float1_decimals`、`smoothstep` 的**数值行为**未做探针实测（实现图已在台账中逐节点核对；规范中标为"未验证"）；
- `while` 的 `__constant__` 只验证"设为 50 不破坏语义"，**未**验证它与迭代上限的实际截断行为（不主动构造死循环，避免 SD 卡死）。

## 8. 复现

```
# 在 Substance Designer 内（MCP execute_sd_code 或 SD 自带 Python 控制台）
exec(open(r'<skill>\scripts\probe_sd_semantics.py', encoding='utf-8').read())
```
脚本为每次运行创建唯一的 `sd_pp_probe_*` 临时输出目录（可用 `SD_PIXEL_AGENT_PROBE_DIR` 指定父目录），从不清空既有目录；结束时仅删除本次运行登记的图。它会输出 `probe_report.json`，记录检测到的 Designer 版本与精确 `functions.sbs` 路径；**不保存任何用户工程**。
