# SD 内建函数供给与语义参考

**用途**：这是主规范 §7.5.1–§7.5.3 的**查找分支**。凡是需要"某个数学函数在 SD 里到底叫什么、端口是什么、语义和源码语言是否一致"时，**先查本文件，再查源头**；不要凭习惯或其它节点工具的直觉推断。

**适用范围**：Substance 3D Designer 16.0.3 + sd_mcp_plugin 3.3.0，只读核实。

**本次回测增补**：当前原子定义没有 `sbs::function::length` 或 `sbs::function::lt`；库函数另有 `length_vec2/3`。向量长度可先查库接口，或用已核验类型的 `sqrt(dot(v,v))`；小于比较可在核验 `gt` 端口后交换操作数构造 `gt(a=y,b=x)`。这些是 16.0.3 当前供应源的结论，不跨版本推断；详见 `MORPHING_RETEST_GATES.md`。

---

## 1. 两个供给源（必须分清）

| 供给源 | 内容 | 数量 | 使用方式 | 语义/端口出处 |
|---|---|---|---|---|
| **A. 原子函数节点** | `sbs::function::*`，节点搜索里直接可建 | **85** 个定义 | `create_node(definition_id='sbs::function::mod')` | SD 自带 Python API 文档（见 §2.1） |
| **B. 内建库 Functions** | 图书馆 **Functions** 分类下的函数图资源（`Functions/Math`、`Functions/Trigo`、`Functions/Transforms`…） | **171** 个函数图 | 通过 **instance 节点**调用；输入 id 来自其形参名 | `resources\packages\functions.sbs`（见 §2.2） |

**关键事实**：`round`、`frac`、`trunc`、`sign`、`clamp`、`saturate`、`step`、`smoothstep`、`fmod`、`truncate_float1_decimals`、`normalize_vec2/3/4`、`rotate_vec2`、`polar_to_carthesian`、`carthesian_to_polar` 等**都不是原子节点**，只存在于 B。反过来 `mod`、`floor`、`ceil`、`atan2`、`cartesian`、`lerp`、`min`、`max`、`pow`、`sqrt`、`log`、`exp`、`log2`、`pow2`、`abs`、`neg`、`div`、`dot`、`rand` 等只存在于 A（B 里是另一套封装）。**两边都要查**，不能只查一边就下结论"SD 没有这个函数"。

> **权威台账**：B 侧 171 个函数的**内部实现图已逐节点核对**（活动对象 vs 发行包 XML，171/171 一致），全库索引与 63 个计算相关函数的逐节点网表见 `references/SD_LIBRARY_FUNCTIONS_v2.5.0.md`，机器可读版见 `references/library_functions_v2.5.0.json`（规范 §11.12/N28/T47）。本文件的语义表与陷阱表是它的**摘要视图**。

> 本文件修正过一次真实错误：早期规范据原子目录断言"SD 没有 round/fract/trunc"，漏掉了供给源 B。凡"某函数不存在"的结论，必须**两个源都查过**才允许写。

## 2. 查找入口（用哪个命令/文件）

### 2.1 原子节点语义：SD 自带的 Python API 文档（权威原文）

```
<SD 安装目录>\resources\documentation\pythonapi\html\_sources\pythonapi\modules\sbs_function.rst.txt
```

- 共 85 个 `[i/85] 'sbs::function::NAME'` 块，每块含 **Label / Description / 各端口 Label 与 Types**。
- 官方帮助里的原句就在这里，例如 atan2："The **Arc tangent 2** function returns the angle in radians between the 2D vector **Vector** and the horizontal. (No need to switch x and y as in the usual atan2 function.) … It is the reciprocal of the **Cartesian** function"。
- 原始等价副本：`<SD 安装目录>\resources\python\tests\assets\test_module.txt`（同一批定义，行 ~2400 起）。

### 2.2 库函数语义与实现：内建包 `functions.sbs`

```
<SD 安装目录>\resources\packages\functions.sbs        # 图书馆 Functions 分类
<SD 安装目录>\resources\packages\3d_functions.sbs     # 3D 相关函数
<SD 安装目录>\resources\packages\functions_hash.sbs   # 哈希函数
```

XML 结构（只读解析即可，**禁止手改**）：

```
package > content > group(Functions) > content > group(Math|Trigo|Transforms|…) > content
        > function(identifier=NAME)
             > attributes      : label / author="Adobe" / tags / description
             > paraminputs     : paraminput > identifier（=实例输入 id）/ attributes>label / type / defaultValue
             > type            : 输出类型（256=float1, 512=float2, 1024=float3, 2048=float4, 16=int1, 1=bool）
             > paramValue > dynamicValue > paramNodes > paramNode
                  > function（原子节点名）+ connections（identifier=端口, connRef=源 UID）= 实现图
```

因此**库函数的实例端口 id = 其 `paraminput` 的 `identifier`**，不是标签。例：`clamp` 是 `input`/`min`/`max`；`fmod` 是 `a`/`b`；`sign` 是 `x`；`truncate_float1_decimals` 是 `input`/`decimals`。

### 2.3 现成工具（优先用）

```powershell
$py = 'C:\Program Files\Adobe\Adobe Substance 3D Designer\plugins\pythonsdk\python.exe'

# 原子节点：官方描述 + 端口
& $py scripts\lookup_sd_function.py --name '^(mod|floor|ceil|lerp|atan2|cartesian)$'

# 库函数：描述 + 形参 + 实现连接
& $py scripts\lookup_sd_function.py --library --name '^(fmod|frac|round_float1|sign|clamp|saturate|step|smoothstep)$' --impl

# 全量导出（供检索/建表）
& $py scripts\lookup_sd_function.py --all --json atomic_functions.json
& $py scripts\lookup_sd_function.py --library --all --json library_functions.json
& $py scripts\lookup_sd_function.py --library --list-groups
```

运行环境：脚本仅用标准库，可用 `plugins\pythonsdk\python.exe` 或任一 Python 3；可用 `--source` / `--install` 指定路径。SD 内的等价入口：图书馆面板 **Functions** 分类；MCP `get_library_nodes`（只列已加载用户包，内建 Functions 可能不出现，故本文件以文件路径为准）。

## 3. 重点区域：`mod` / `fmod` / `round` / `frac` / `trunc`（最易出错）

### 3.1 供给与官方语义（已核实）

| 源码意图 | SD 供给 | 标识 | 形参/端口 | 官方描述（原文） |
|---|---|---|---|---|
| GLSL `mod(x,y)`（floor 基，结果符号随 y） | A：原子 `mod` | `sbs::function::mod`，标签 **Modulo** | `a`(A) / `b`(**Divisor**) | 文档只写 "mod(A,Divisor)"；**实测 floor 基**：`mod(−0.25,1)=0.75`、`mod(1.25,−1)=−0.75`（§11.11 / `NATIVE_PROBE_RESULTS_v2.5.0.md`） |
| C/HLSL `fmod(x,y)`（截断基，结果符号随 x） | B：库函数 `fmod` | `Functions/Math/fmod`，标签 **Fmod** | `a`(A) / `b`(B) | "Returns the remainder of a/b with the **same sign as a**" |
| 取小数部分 `fract`/`frac` | B：库函数 `frac` | `Functions/Math/frac`，标签 **Frac** | `input` | "Returns the fractional portion of a scalar"（实现 = `input − floor(input)`） |
| `round(x)` | B：库函数 `round_float1` | `Functions/Math/round_float1`，标签 **Round Float1** | `input` | "Rounds a Float 1. **Rounds up when decimal is greater or equal than 0.5**"（实现 = `floor(input + 0.5)`） |
| 截断到小数位 | B：库函数 `truncate_float1_decimals` | 标签 **Truncate Float1** | `input` / `decimals`(**int1**, 默认 1) | "Truncates a Float1's to a specific amount of decimals" |

### 3.2 强制映射规则

1. **GLSL `mod(x,y)`**：**直接用原子 `mod`**（端口 `a`=被除数、`b`=Divisor）。官方描述虽未规定负数行为，但**实测为 floor 基**：`mod(−0.25,1)=0.75`、`mod(1.25,−1)=−0.75`、向量逐分量同规则，与 GLSL `mod` 一致（§11.11）。只有在**当前环境实测与该结论不符**时才改用显式构造 `x − y*floor(x/y)`（`div`→`floor`→`mul`→`sub`），并把差异记入报告。
   要点：`mod` 是**同维多态**节点——`mod(float2 A, float1 Divisor)` **静默返回 0**（不广播、不报错），向量除标量必须显式广播成同维（如 `vector2(b,b)`）。
2. **C/HLSL `fmod(x,y)`**：**用库函数 `fmod`**（`a`=被除数、`b`=除数），其官方语义"符号随 a"就是 C 语义。**不要**用原子 `mod` 代替 `fmod`——两者在负数上不同，这是本区域最高频的错误。
3. **`round(x)`**：优先实例化 `round_float1`。其语义是 **`floor(x+0.5)`（半整数向 +∞ 取整）**。若源码语言规定"半整数远离零"或"银行家取整"，负数半整数处结果不同 → 必须显式构造（例如按符号分支：`ifelse(x<0, −floor(−x+0.5), floor(x+0.5))` 实现远离零），并在报告中说明约定来源。
4. **`frac`/`fract`**：优先实例化 `frac`，语义 = `input − floor(input)`（floor 基）。**注意**：这与"结果符号随被除数"的 C `fmod(x,1)` 在负数上不同（`frac(-0.25)=0.75`，`fmod(-0.25,1)=-0.25`）。
5. **`trunc`（向零截断）在 SD 无现成函数**：用 `ifelse(x < 0, ceil(x), floor(x))` 显式构造；若只需"截到 N 位小数"，直接用 `truncate_float1_decimals`（`decimals` 为 int1）。
6. **`sign(x)`**：优先实例化 `sign`，但**官方语义为 `x==0` 返回 `1`**（不是 0）。GLSL `sign(0)=0`、C `sign` 多实现也不同 → 需要严格数学符号时显式构造 `ifelse(x<0, -1, ifelse(x>0, 1, 0))`。
7. **`clamp`/`saturate`/`step`/`smoothstep`**：均优先实例化库函数，不要手搓：
   - `clamp`：`input` / `min` / `max`（三个 float1 形参）。
   - `saturate`：`input`；官方 "Returns 0 if input is lower than 0. Returns 1 if input is greater than 1"。
   - `step`：`a`(A) / `x`(X)，官方 "one if **x is greater than or equal to a**, and zero otherwise" —— 与 GLSL/HLSL `step(edge,x)` 的参数顺序一致，但**语义边界是 `x ≥ a`**，写反会整段反向。
   - `smoothstep`：`a`(A) / `b`(B) / `x`(X)，与 GLSL `smoothstep(a,b,x)` 同序。

### 3.3 实例化与连接规则

- 库函数走 **instance 节点**：先按反射/库引用创建实例，再按 §7.1/I10 用**形参名**作为输入端口 id 连接；不得用标签（`Input`/`Min`/`Max`/`X`/`A`/`B`/`Decimals` 都不是端口 id）。
- 库函数实例同样要登记进表达式/布局表并按其端口类型核对（T39/I39）；实例的输出端口名来自被调函数的输出，**不一定是 `unique_filter_output`**，必须回读。
- 库函数内部实现可能引用其它库函数（例：`smoothstep` 的实现里有 `instance`）；**不要**假设它是纯原子组合，也不要依赖其内部节点名。
- **只有当前会话能取到活 resource 且首调用点数值通过时**才优先复用库函数。此文件中的 `functions.sbs` 解析证明存在性/实现，不证明 MCP 可达；`get_library_nodes` 可能只枚举用户包。可尝试 Adobe SDK 官方实例示例中的 `loadUserPackage`/`findResourceFromUrl` 路径，但该路径对本安装的 `functions.sbs` 尚未原生验证。不可达时记 `LIBRARY_INSTANCE_UNREACHABLE:<尝试与结果>`，对照 Adobe 实现显式构造并用独立 oracle 验证；不要因不可达而声称该函数不存在。跨包 formal 值在首调用点验证前仍是未验证（`REAL_PROJECT_VALIDATION.md`）。

### 3.4 GLSL 常用函数可用性速查（16.0.3；仍须查当前图）

| 源码族 | 已核实供应 | 处置边界 |
|---|---|---|
| `floor/ceil/abs/min/max/pow/sqrt/exp/log/log2/mod/dot/sin/cos/tan/lerp` | 原子 | `mix` 对应 `lerp(a,b,x)`；同维与语义另判 |
| `frac/clamp/saturate/step/smoothstep/round/sign/fmod` | 库 Functions | 实例可达性必须现场确认；否则记录并显式构造+oracle |
| `length`、`normalize` | 库内有按维度命名的版本 | 无匹配原子；核对 vecN 版本与形参，或构造并验证零向量边界 |
| `cross` | 已查库项为 `cross_product_vec2` | 不可当作 vec3 cross；vec3 需求显式分量构造并验证方向/右手系 |
| `asin/acos` | 本项目两源未找到 | 对 `[-1,1]` 域可由 `atan2` 与 `sqrt(max(0,1-x²))` 构造主值；端口次序按 §7.5.2，边界数值验证 |
| `transpose/inverse/matrixCompMult` | 本项目两源未找到直接节点 | 按矩阵维度逐项降级，不能仅凭名称推断 |
| `texture/texelFetch/dFdx/dFdy` | 不是当前 PP Function 原子/库调用的直接替代 | 按采样/导数语义另设计，标未映射直到验证 |

该表是**优先检索清单而非全集**；`distance/reflect/refract` 等未在本项目完成两源与语义核对，不填“没有”。凡版本或资源包变化，重跑查找与当前图定义门。

## 4. 陷阱速查

| 陷阱 | 事实 | 后果 |
|---|---|---|
| "SD 没有 round/frac/trunc/sign/clamp" | 原子层确实没有，但库函数有 | 误判为需手搓或无法实现；结论错误 |
| 用原子 `mod` 代替 `fmod` | 实测：`mod(−0.25,1)=0.75` 而 `fmod(−0.25,1)=−0.25`，同一输入差 1.0 | 负数输入结果错，且不报错 |
| 把库函数接到混维输入（如 `mod(float2, float1)`） | 这类多态节点要求**同维**；SD **不在连线时报错** | 静默 0（整段失效），无任何提示 |
| `round` 当成"四舍五入远离零" | `round_float1` = `floor(x+0.5)` | 负数半整数差 1 |
| `sign(0)` 当成 0 | 官方：`x==0` 返回 **1** | 分支/归一化在 0 处抖动 |
| `frac` 当成 `fmod(x,1)` | `frac` 是 floor 基 | 负数结果差 1 |
| 用标签当端口 id | 库函数端口 id 是形参 `identifier`（小写/短名） | 连线失败或崩溃（T40/T41 同族） |
| 把 `passthrough` 当成点积 | 原子层标签 `Dot` 的是**布局用 reroute** 节点；点积是 `dot`（标签 "Dot product"） | 用错节点，结果无意义 |
| `mulscalar` 接 float1 | 官方：`a` 只接受 float2/3/4 | 静默返回 0（T33） |
| `lerp` 端口顺序 | `a` / `b` / `x`，`x` 是权重 | 权重与被插值量写反 |

## 5. 未验证 / 需探针

- ~~**原子 `mod` 的负数语义**（floor 基还是截断基）~~ → **已实测为 floor 基**（§11.11 / `NATIVE_PROBE_RESULTS_v2.5.0.md`）：见 §3.2 规则 1。
- **`mod`/`mul` 等同一族多态节点的"混维静默 0"**：已实测（`mod(float2,float1)`、`mul(float2,float1)` 均为 0）；但**其它多态节点**（`swizzle`/`gradient` 类）是否同样静默，未逐项实测 → 用到时按 SOP-0B 取证。
- ~~**`fmod` 库函数实现细节**~~ → **已逐节点核对**：`fmod(a,b) = ifelse(a < 0, −(frac(|a/b|)·|b|), frac(|a/b|)·|b|)`（11 节点；其中 `frac` 是嵌套 instance）。全库 171 个函数的实现图核对结果见 `references/SD_LIBRARY_FUNCTIONS_v2.5.0.md`（规范 §11.12）。
- **库函数的类型宽度**：本文件核实的条目形参/输出多为 **float1**；`normalize_vec2/3/4`、`cross_product`、`distance_vec2/3`、`saturate_float2`、`average_float*`、`divide_float2/3/4`、`Equality_*` 等按维度分开提供，使用前必须核对其形参与输出维度（用 `--library --name <名>` 查）。
- **库函数实例在只读环境下的可创建性**：本文件基于文件解析与官方文档；实际通过 MCP 创建内建库函数实例（依赖包解析）尚未在本会话实测。

## 6. 报告要求

用到本文件时，报告中必须包含**数值语义选择表**（I41）：

| 源码表达式 | 语义类别 | 判定依据 | 选用供给（原子/库函数/显式构造） | 端口绑定 | 与源码差异（若有） |
|---|---|---|---|---|---|

任何"SD 不支持 X"的结论必须标注两个供给源都已查证；任何未探针的语义假定必须在报告中标为未验证。

## Sequence-derived multiplication rule

The normal `mulscalar(vector, scalar)` selection remains valid for ordinary pure expressions. **Do not apply it to a Sequence-derived vector.** Field testing found `mulscalar(Sequence(float4), const)` unreliable; broadcast the scalar to the vector dimension and use same-dimension `mul`.
