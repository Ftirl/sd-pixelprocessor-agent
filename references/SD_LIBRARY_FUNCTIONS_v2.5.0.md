# SD 内建库函数台账 v2.5.0（逐节点核对）

> 生成：`scripts/render_library_catalog.py`　数据：SD 活动对象 + 发行包 XML + 真实 cook 实测
> 机器可读版：`references/library_functions_v2.5.0.json`　核对器：`scripts/verify_library_functions.py`

## 1. 这份台账为什么可信（三源一致）

| 视图 | 取数方式 | 结果 |
|---|---|---|
| A. SD 活动对象 | `scripts/dump_library_functions.py` 在 Designer 进程内遍历 `SDSBSFunctionGraph`：节点定义、真实属性值、`getInputPropertyNode()` 源端反查边 | **171 函数 / 2334 节点 / 2814 边** |
| B. 发行包 XML | `scripts/verify_library_functions.py parse-xml` 独立解析 `resources/packages/functions.sbs`（uid 引用、`paramNode`/`connections`/`rootnode`） | **171 函数 / 2334 节点 / 2814 边** |
| C. 真实 cook | `scripts/probe_sd_semantics.py` 在 PP 里真实求值并导出 BMP 读像素 | 与 A、B 的网表求值逐项一致 |

**逐节点差分结果：171/171 函数 PASS，0 处不一致。** 每个函数都比对了：节点集合（定义+坐标）、边集合（源节点+端口→目标节点+端口）、每个常量（float32 精度）、输出节点、形参 id 顺序、嵌套调用目标。

已解释的例外（不计为不一致）：

- **XML 省略默认常量 90 处**：`const_*`/`swizzle*` 取默认值（0 / 恒等排列）时文件不写 `funcDatas`，SD 侧会显式给出默认值。差分对每个省略项都按 `ATOM_DEFAULTS` 复核。
- **XML 无坐标 1 处**：`NotEqual_Float3` 的一个 `get_float3` 没有 `gpos`，按（定义+常量）唯一匹配。
- **陈旧连接 1 处**：`distance_vec3` 的 `instance`（目标 `length_vec3`）上有一条连向 `input_v` 的边，而目标函数只声明了 ['v'] —— 文件里的历史残留，SD 装载时忽略，不影响求值。

**数值闭环（网表求值 vs BMP 实测）**：SDK 网表 15/15，XML 网表同样通过。

| 函数 | 输入 | 网表值 | 实测值 | 依据 |
|---|---|---|---|---|
| `frac` | `{"input": -0.25}` | 0.75 | 0.75 | floor-based; fmod(x,1) would be -0.25 |
| `frac` | `{"input": 1.25}` | 0.25 | 0.25 |  |
| `round_float1` | `{"input": -2.5}` | -2 | -2 | floor(x+0.5), half-up toward +inf |
| `round_float1` | `{"input": 2.5}` | 3 | 3 |  |
| `round_float1` | `{"input": 2.4}` | 2 | 2 |  |
| `fmod` | `{"a": -0.25, "b": 1.0}` | -0.25 | -0.25 | sign follows the dividend |
| `fmod` | `{"a": 1.25, "b": -1.0}` | 0.25 | 0.25 |  |
| `sign` | `{"x": 0.0}` | 1 | 1 | documented X==0 -> 1 |
| `sign` | `{"x": -3.0}` | -1 | -1 |  |
| `step` | `{"a": 0.5, "x": 0.5}` | 1 | 1 | inclusive x >= a |
| `step` | `{"a": 0.5, "x": 0.49}` | 0 | 0 |  |
| `clamp` | `{"input": -3.0, "min": 0.0, "max": 1.0}` | 0 | 0 |  |
| `clamp` | `{"input": 2.0, "min": 0.0, "max": 1.0}` | 1 | 1 |  |
| `saturate` | `{"input": 2.0}` | 1 | 1 |  |
| `saturate` | `{"input": -1.0}` | 0 | 0 |  |

**使用限制**（保持诚实）：

- 数值来自 SD 的**单精度**值（本台账按 float32 归一化比较）；XML 与 SDK 的差异若超过 float32 分辨率会记为不一致。
- 坐标（`pos`）来自活动对象；XML 缺坐标的个别节点已注明。
- 台账是 16.0.3 + 该发行包的内容；换版本用同样两条命令重新生成后差分即可。

## 2. 类型字典（发行包 type id → 名称）

| type id | 名称 |
|---|---|
| 4 | bool1 |
| 16 | int1 |
| 32 | int2 |
| 64 | int3 |
| 128 | int4 |
| 256 | float1 |
| 512 | float2 |
| 1024 | float3 |
| 2048 | float4 |

## 3. 全库索引（171 个函数）

| identifier | group | label | 形参（id:类型=默认） | 输出 | 节点 | 边 | 调用 | 描述 |
|---|---|---|---|---|---|---|---|---|
| `Wave` | Functions/Cycles | Wave | Amplitude:float1=1, Frequency:float1=1, greaterThanZero:bool1=False | float1 | 9 | 10 | — | This function returns a Float1 value that oscillates over $time. It has Amplitude and Frequency inputs. |
| `2Pi` | Functions/Math | 2 Pi | — | float1 | 1 | 0 | — | — |
| `Curve_Function` | Functions/Math | Curve | curve:float1=0, input:float1=0 | float1 | 29 | 36 | — | -1 : ease out 0 : linear 1 : ease in |
| `Equality_Boolean` | Functions/Math | Equality boolean | A:bool1=False, B:bool1=False | bool1 | 7 | 8 | — | — |
| `Equality_Float2` | Functions/Math | Equality Float2 | A:float2=0,0, B:float2=0,0 | bool1 | 9 | 10 | — | — |
| `Equality_Float3` | Functions/Math | Equality Float3 | A:float3=0,0,0, B:float3=0,0,0 | bool1 | 9 | 10 | `Equality_Float2` | — |
| `Equality_Float4` | Functions/Math | Equality Float4 | A:float4=0,0,0,0, B:float4=0,0,0,0 | bool1 | 9 | 10 | `Equality_Float2` | — |
| `Ln` | Functions/Math | Ln | a:float1=0 | float1 | 5 | 4 | — | The Ln function returns the Natural logarithm value of entry. |
| `NotEqual_Boolean` | Functions/Math | Not equal boolean | A:bool1=False, B:bool1=False | bool1 | 4 | 3 | `Equality_Boolean` | — |
| `NotEqual_Float2` | Functions/Math | Not equal Float2 | A:float2=0,0, B:float2=0,0 | bool1 | 4 | 3 | `Equality_Float2` | — |
| `NotEqual_Float3` | Functions/Math | Not equal Float3 | A:float3=0,0,0, B:float3=0,0,0 | bool1 | 4 | 3 | `Equality_Float3` | — |
| `NotEqual_Float4` | Functions/Math | Not equal Float4 | A:float4=0,0,0,0, B:float4=0,0,0,0 | bool1 | 4 | 3 | `Equality_Float4` | — |
| `Pi` | Functions/Math | Pi | — | float1 | 1 | 0 | — | — |
| `Pow` | Functions/Math | Pow (Deprecated) | x:float1=0, n:float1=0 | float1 | 11 | 12 | — | Returns x^n.  This function is now deprecated as the engine v9 provides an atomic Pow function. |
| `Roughness` | Functions/Math | Roughness | Roughness:float1=0, CurrentLevel:int1=0, TotalLevel:int1=0, GlobalOpacity:float1=0 | float1 | 24 | 28 | — | — |
| `average_float1` | Functions/Math | Average Float1 | a:float1=1, b:float1=1 | float1 | 5 | 4 | — | Returns the average value of A and B. |
| `average_float2` | Functions/Math | Average Float2 | a:float2=1,1, b:float2=1,1 | float2 | 5 | 4 | — | Returns the average value of A and B. |
| `average_float3` | Functions/Math | Average Float3 | a:float3=1,1,1, b:float3=1,1,1 | float3 | 5 | 4 | — | Returns the average value of A and B. |
| `average_float4` | Functions/Math | Average Float4 | a:float4=1,1,1,1, b:float4=1,1,1,1 | float4 | 5 | 4 | — | Returns the average value of A and B. |
| `clamp` | Functions/Math | Clamp | input:float1=1, min:float1=1, max:float1=1 | float1 | 5 | 4 | — | Returns Min or Max if the input is outside of the Min/Max range. |
| `cross_product` | Functions/Math | Cross product | a:float3=1,1,1, b:float3=1,1,1 | float3 | 9 | 10 | — | Returns the cross product of two three-component vectors |
| `cross_product_vec2` | Functions/Math | Cross product Vec2 | a:float2=1,1, b:float2=1,1 | float1 | 11 | 12 | — | Returns the cross product of two two-component vectors |
| `distance_vec2` | Functions/Math | Distance Float2 | a:float2=1,1, b:float2=1,1 | float1 | 4 | 3 | `length_vec2` | Returns the Euclidean distance between two points (in 2D). |
| `distance_vec3` | Functions/Math | Distance Float3 | a:float3=1,1,1, b:float3=1,1,1 | float1 | 4 | 3 | `length_vec3` | Returns the Euclidean distance between two points. |
| `divide_float2` | Functions/Math | Scalar division Float2 | input:float2=1,1, scalar:float1=1 | float2 | 7 | 8 | — | Divide a float 2 by a given scalar. |
| `divide_float3` | Functions/Math | Scalar division Float3 | input:float3=1,1,1, scalar:float1=1 | float3 | 10 | 13 | — | Divide a float 3 by a given scalar. |
| `divide_float4` | Functions/Math | Scalar division Float4 | input:float4=1,1,1,1, scalar:float1=1 | float4 | 13 | 18 | — | Divide a float 4 by a given scalar. |
| `fmod` | Functions/Math | Fmod | a:float1=1, b:float1=1 | float1 | 11 | 13 | `frac` | Returns the remainder of a/b with the same sign as a. |
| `frac` | Functions/Math | Frac | input:float1=1 | float1 | 3 | 3 | — | Returns the fractional portion of a scalar. |
| `length_vec2` | Functions/Math | Length Float2 | v:float2=1,1 | float1 | 3 | 3 | — | Returns scalar Euclidean length of a vector float2. |
| `length_vec3` | Functions/Math | Length Float3 | v:float3=1,1,1 | float1 | 3 | 3 | — | Returns scalar Euclidean length of a vector float3. |
| `merge_float3` | Functions/Math | Merge Float3 | x:float1=1, y:float1=1, z:float1=1 | float3 | 5 | 4 | — | Combines 3 float into a vector 3. |
| `merge_float4` | Functions/Math | Merge Float4 | x:float1=1, y:float1=1, z:float1=1, w:float1=1 | float4 | 7 | 6 | — | Combines 4 float into a vector 4. |
| `normalize_vec2` | Functions/Math | Normalize Vec2 | input:float2=1,1 | float2 | 6 | 7 | — | Normalizes a Vec2. |
| `normalize_vec3` | Functions/Math | Normalize Vec3 | input:float3=1,1,1 | float3 | 6 | 7 | — | Normalizes a Vec3. |
| `normalize_vec4` | Functions/Math | Normalize Vec4 | input:float4=1,1,1,1 | float4 | 6 | 7 | — | Normalizes a Vec4. |
| `oneminus` | Functions/Math | One minus | x:float1=1 | float1 | 3 | 2 | — | Returns one minus x (1 - x). |
| `orthogonal_vec2` | Functions/Math | Orthogonal Vec2 | input:float2=1,1 | float2 | 4 | 3 | — | Returns an orthognal vector of the input vec2. |
| `reflect` | Functions/Math | Reflect | i:float3=1,1,1, n:float3=1,1,1 | float3 | 7 | 8 | — | Returns the reflectiton vector given an incidence vector and a normal vector. |
| `round_float1` | Functions/Math | Round Float1 | input:float1=1 | float1 | 4 | 3 | — | Rounds a Float 1. Rounds up when decimal is greater or equal than 0.5 |
| `saturate` | Functions/Math | Saturate | input:float1=1 | float1 | 5 | 4 | — | - Returns 0 if input is lower than 0. - Returns 1 if input is greater than 1. |
| `saturate_float2` | Functions/Math | Saturate Float2 | input:float2=1,1 | float2 | 6 | 6 | `saturate` | For each vector component: - Returns 0 if input is lower than 0. - Returns 1 if input is greater than 1. |
| `sign` | Functions/Math | Sign | x:float1=1 | float1 | 6 | 5 | — | Returns the sign of a scalar. If X == 0, returns 1. |
| `smoothstep` | Functions/Math | Smoothstep | a:float1=1, b:float1=1, x:float1=1 | float1 | 13 | 15 | `saturate` | Smooth interpolation between A and B in function of X. |
| `step` | Functions/Math | Step | a:float1=1, x:float1=1 | float1 | 6 | 5 | — | Returns one if x is greater than or equal to a, and zero otherwise. |
| `truncate_float1_decimals` | Functions/Math | Truncate Float1 | input:float1=1, decimals:int1=1 | float1 | 11 | 13 | `Pow` | Truncates a Float1's to a specific amount of decimals. |
| `EvenCount` | Functions/Math/Parity | Even count | Input:float1=0 | float1 | 5 | 4 | — | Returns the count of even numbers contained in the input. |
| `OddCount` | Functions/Math/Parity | Odd count | Input:float1=0 | float1 | 5 | 4 | — | Returns the count of odd numbers contained in the input. |
| `ParityTest` | Functions/Math/Parity | Parity test | Input:float1=0 | bool1 | 10 | 11 | — | Returns true if the input is a even number. |
| `acos` | Functions/Math/Trigo | acos | x:float1=1 | float1 | 6 | 5 | `Pi`, `asin` | Returns the arc cosine of entry value: acos(x). |
| `asin` | Functions/Math/Trigo | asin | x:float1=1 | float1 | 22 | 27 | — | Returns the arc sine of entry value: asin(x). |
| `deg_to_rad` | Functions/Math/Trigo | Degrees to radians | deg:float1=0 | float1 | 5 | 4 | `Pi` | Converts an angle input from degrees to radians, which is the most commonly used in Substance. For GUI only needs, it is recommended to use the Angle Editor along with a Float1 value type. Use this function in another when you need to convert angle value types. |
| `Degrees_to_Turn` | Functions/Random | Degrees to turns | input:float1=0 | float1 | 3 | 2 | — | This function converts a degree floating value (0 to 360] to turns (0 to 1). |
| `Discrete_[A,B]` | Functions/Random | Random discrete [a, b] | A:float1=0, B:float1=1, Probability:float1=0.5 | float1 | 7 | 6 | — | — |
| `GlobalRandom` | Functions/Random | Global random | Input:float1=0, Seed:int1=0 | float1 | 136 | 171 | — | This Pseudo-Random function generates a floating  random value between 0 and the entry value. The seed value is local to the function (same inputs will always give the same results). |
| `Uniform_F2_[A,B[` | Functions/Random | Random uniform Float2 [a,b[ | A2:float2=0,0, B2:float2=1,1 | float2 | 9 | 10 | — | — |
| `Uniform_F3_[A,B[` | Functions/Random | Random uniform Float3 [a,b[ | A:float3=0,0,0, B:float3=1,1,1 | float3 | 12 | 14 | — | — |
| `Uniform_F4_[A,B[` | Functions/Random | Random uniform Float4 [a, b[ | A:float4=0,0,0,0, B:float4=1,1,1,1 | float4 | 15 | 18 | — | — |
| `Uniform_[-1,1[` | Functions/Random | Random uniform [-1, 1[ | — | float1 | 4 | 3 | — | This function returns a floating random value between -1 and 1. |
| `Uniform_[A,B[` | Functions/Random | Random uniform [a, b[ | A:float1=0, B:float1=1 | float1 | 5 | 5 | — | This function returns a floating random value between value A and value B. |
| `normal_distribution` | Functions/Random | Normal distribution | radius:float1=1, uniform_random:float2=1,1 | float2 | 16 | 16 | `2Pi` | Converts a Vec2 Uniform Random value into a Normal Distribution. Resulting range is [-radius, radius]. |
| `Height_Balance_Fn` | Functions/Ranges | Height balance | Depth_Balance:float1=0 | float4 | 16 | 22 | — | This function returns a float4 in which : X is minimum of the Higher Y is maximum of the Higher Z is minimum of the Lower W is maximum of the Lower The input goes from -1.0 to 1.0. A 0 value input returns a balanced output of 0.0 ; 0.5 ; 0.5 ; 1.0. |
| `[-1_1]_to_[0_1]` | Functions/Ranges | [-1, 1] to [0,1] | Input:float1=0 | float1 | 5 | 4 | — | — |
| `[0,1]_to_[0,1,0]` | Functions/Ranges | [0,1] to [0,1,0] | input:float1=1 | float1 | 7 | 7 | — | Moves centre of gradient to middle 0.5, expands range. Good for bi-directional gradient. |
| `[0_1]_to_[-1_1]` | Functions/Ranges | [0, 1] to [-1, 1] | Input:float1=0 | float1 | 5 | 4 | — | — |
| `[0_1]_to_[1_0]` | Functions/Ranges | [0, 1] to [1, 0] | Input:float1=0 | float1 | 5 | 4 | — | — |
| `[a,b]_to_[0,1]` | Functions/Ranges | [a,b] to [0,1] | X:float1=1, A:float1=1, B:float1=1 | float1 | 9 | 10 | — | Returns position of input X, between min a, max b as a float between 0 and 1.Works as a reverse linear interpolation. |
| `negateFloat` | Functions/Ranges | Negate Float1 (Deprecated) | Input:float1=0 | float1 | 3 | 2 | — | — |
| `sawtooth_wave` | Functions/Ranges | Sawtooth wave | x:float1=1 | float1 | 11 | 13 | — | Repeats range to  [0,1], like texture coordinate tiling. Modulo adjusted to peak at 1, instead of back to 0. |
| `triangle_wave` | Functions/Ranges | Triangle wave | input:float1=1 | float1 | 7 | 6 | `oneminus` | repeats gradient range from 0 to 1 back to 0, giving a mirrored effect, like a sawtooth function, at every whole number. |
| `tonemap_ACES` | Functions/Tonemappers | ACES tonemapper | input:float3=1,1,1 | float3 | 29 | 35 | `merge_float3` | — |
| `tonemap_AgX` | Functions/Tonemappers | AgX tonemapper | input:float3=1,1,1, slope:float3=1,1,1, power:float3=1,1,1, offset:float3=1,1,1, saturation:float1=1 | float3 | 44 | 52 | `tonemap_AgX_approx`, `tonemap_AgX_look` | — |
| `tonemap_AgX_approx` | Functions/Tonemappers | tonemap_AgX_approx | input:float3=1,1,1 | float3 | 25 | 34 | — | Sub function for the AgX tonemapper. |
| `tonemap_AgX_look` | Functions/Tonemappers | tonemap_AgX_look | input:float3=1,1,1, offset:float3=1,1,1, slope:float3=1,1,1, power:float3=1,1,1, saturation:float1=1 | float3 | 14 | 15 | — | Sub function for the AgX tonemapper. |
| `tonemap_Hejl` | Functions/Tonemappers | Hejl tonemapper | input:float3=1,1,1 | float3 | 35 | 45 | — | — |
| `Directional_Offset` | Functions/Transforms | Directional offset | Direction:float1=0, Distance:float1=0 | float2 | 9 | 10 | `deg_to_rad`, `turnsToDegrees` | This function returns a float2 ranging from (-1.0, -1.0) to (1.0, 1.0), based on its Direction and Distance inputs. The Direction is calibrated to the left, same as every filters in Substance. |
| `MatrixMultiply` | Functions/Transforms | Matrix multiply | MatrixA:float4=1,0,0,1, MatrixB:float4=1,0,0,1 | float4 | 25 | 38 | — | This function returns a Float4 Transform Matrix that is the Matrix product of its two Matrix intputs. It is useful for combining a Rotation Matrix and a Scale Matrix. |
| `RotationMatrix` | Functions/Transforms | Rotation matrix | RotationW:float1=0 | float4 | 10 | 12 | `deg_to_rad`, `turnsToDegrees` | This function returns a Float4 Transform Matrix that spins as its RotationW changes. The RotationW is expected in #Turns. |
| `ScaleMatrix` | Functions/Transforms | Scale matrix | ScaleUV:float2=100,100 | float4 | 10 | 12 | — | This function returns a Float4 Transform Matrix that scales as its ScaleUV changes. |
| `TileMatrix` | Functions/Transforms | Tile matrix | tiles_xy:float2=100,100 | float4 | 7 | 8 | — | This function returns a Float4 Transform Matrix that tiles in function of the X/Y input. |
| `carthesian_to_polar` | Functions/Transforms | Cartesian to polar | input:float3=1,1,1 | float2 | 20 | 23 | `2Pi`, `Pi`, `oneminus` | — |
| `matrix_invert` | Functions/Transforms | Matrix invert | matrix22:float4=1,1,1,1 | float4 | 13 | 15 | — | Inverts a 2x2 matrix. |
| `polar_to_carthesian` | Functions/Transforms | Polar to cartesian | input:float2=1,1 | float3 | 18 | 21 | `Pi` | — |
| `rotate_vec2` | Functions/Transforms | Rotate Vec2 | vec2:float2=1,1, angle:float1=1, pivot:float2=1,1 | float2 | 17 | 21 | `2Pi` | Rotates a Vec2 around a Pivot. |
| `rotate_vec2_rad` | Functions/Transforms | Rotate Vec2 (Radian) | vec2:float2=1,1, angle:float1=1 | float2 | 10 | 13 | — | Rotates a Vec2 given an angle value [0, 2Pi]. |
| `compute_total_number` | Functions/Various | compute_total_number | tile_multiplier:int1=1 | int1 | 33 | 39 | — | — |
| `disorder` | Functions/Various | Disorder | disorder_radius:float1=1, disorder_angle:float1=1 | float2 | 12 | 12 | — | — |
| `disorder_anim` | Functions/Various | disorder_anim | disorder_angle:float1=1, speed:float1=1 | float2 | 15 | 14 | — | — |
| `disorder_v2` | Functions/Various | disorder_v2 | disorder_radius:float1=1, disorder_angle:float1=1 | float2 | 10 | 10 | — | — |
| `non_square_expansion_uv_scale` | Functions/Various | Non-square expansion UV scale | position:float2=1,1, non_square_expansion:bool1=True | float2 | 21 | 28 | — | Scale UVs and maintain the [0, 1] square in the center in function of the image size ratio. |
| `non_square_output_size` | Functions/Various | Non-square output size | scale:int1=1, output_size:int2=1,1, non_square:bool1=False | int2 | 70 | 87 | — | Mainly used in FX-Map noises: Computes: - render_region - tiling_region - xy_difference - xy_ratio  To be used along with an Iterate node to duplicate the noise in function of the Image Ratio. |
| `non_square_output_size_v2` | Functions/Various | Non-square output size | scale:float1=1, output_size:int2=1,1, non_square:bool1=False, tile_offset:float2=1,1 | int2 | 99 | 126 | — | Mainly used in FX-Map noises: Computes: - render_region (float4) - tiling_region (float4) - xy_difference (float) - xy_ratio (float2) - total_number (int)  To be used along with an Iterate node to duplicate the noise in function of the Image Ratio. |
| `HCLtoRGB` | Functions/colorValues | HCL to RGB | hcl:float3=1,1,1 | float3 | 64 | 101 | `RGB_lightness_luma_rec601` | — |
| `HSItoRGB` | Functions/colorValues | HSI to RGB | hsi:float3=1,1,1 | float3 | 71 | 110 | — | — |
| `HSLtoRGB` | Functions/colorValues | HSL to RGB | HSL:float3=0,0,0 | float3 | 43 | 52 | — | — |
| `HSVtoRGB` | Functions/colorValues | HSV to RGB | hsv:float3=1,1,1 | float3 | 64 | 102 | — | — |
| `RGB_chroma_2_polar` | Functions/colorValues | RGB chroma 2 polar | rgb:float3=1,1,1 | float1 | 20 | 25 | — | — |
| `RGB_chroma_hexagonal` | Functions/colorValues | RGB chroma hexagonal | rgb:float3=1,1,1 | float1 | 9 | 13 | — | — |
| `RGB_hue_2_polar` | Functions/colorValues | RGB hue 2 polar | rgb:float3=1,1,1 | float1 | 28 | 31 | `Pi` | — |
| `RGB_hue_hexagonal` | Functions/colorValues | RGB hue hexagonal | rgb:float3=1,1,1 | float1 | 36 | 55 | — | — |
| `RGB_lightness_average` | Functions/colorValues | RGB lightness average | rgb:float3=1,1,1 | float1 | 8 | 9 | — | — |
| `RGB_lightness_bihexcone` | Functions/colorValues | RGB lightness bi-hexcone | rgb:float3=1,1,1 | float1 | 11 | 15 | — | — |
| `RGB_lightness_hexcone` | Functions/colorValues | RGB lightness hexcone | rgb:float3=1,1,1 | float1 | 6 | 7 | — | — |
| `RGB_lightness_luma_rec601` | Functions/colorValues | RGB lightness luma Rec. 601 | rgb:float3=1,1,1 | float1 | 12 | 13 | — | — |
| `RGB_lightness_luma_rec709` | Functions/colorValues | RGB lightness luma Rec. 709 | rgb:float3=1,1,1 | float1 | 12 | 13 | — | — |
| `RGB_saturation_HSI` | Functions/colorValues | RGB saturation HSI | rgb:float3=1,1,1 | float1 | 14 | 17 | `RGB_lightness_average` | — |
| `RGB_saturation_HSL` | Functions/colorValues | RGB saturation HSL | rgb:float3=1,1,1 | float1 | 15 | 16 | `RGB_chroma_hexagonal`, `RGB_lightness_bihexcone` | — |
| `RGB_saturation_HSV` | Functions/colorValues | RGB saturation HSV | rgb:float3=1,1,1 | float1 | 8 | 9 | `RGB_chroma_hexagonal`, `RGB_lightness_hexcone` | — |
| `RGBtoHCL` | Functions/colorValues | RGB to HCL | rgb:float3=1,1,1 | float3 | 6 | 7 | `RGB_chroma_hexagonal`, `RGB_hue_hexagonal`, `RGB_lightness_luma_rec601` | — |
| `RGBtoHSI` | Functions/colorValues | RGB to HSI | rgb:float3=1,1,1 | float3 | 6 | 7 | `RGB_hue_2_polar`, `RGB_lightness_average`, `RGB_saturation_HSI` | — |
| `RGBtoHSL` | Functions/colorValues | RGB to HSL | RGB:float3=0,0,0 | float3 | 47 | 76 | `average_float1` | — |
| `RGBtoHSV` | Functions/colorValues | RGB to HSV | rgb:float3=1,1,1 | float3 | 6 | 7 | `RGB_hue_hexagonal`, `RGB_lightness_hexcone`, `RGB_saturation_HSV` | — |
| `Random_Color` | Functions/colorValues | Random color | RGB:float3=0,0,0, RGB_Randomness:float3=0,0,0 | float3 | 29 | 37 | — | — |
| `Random_Luminosity` | Functions/colorValues | Random luminosity | RGB:float3=0,0,0, Luminosity_Randomness:float1=0 | float3 | 16 | 20 | — | — |
| `acescg_to_linear_srgb` | Functions/colorValues | ACEScg to linear sRGB | input:float3=1,1,1 | float3 | 8 | 9 | `merge_float3` | — |
| `directionToNormal` | Functions/colorValues | Direction to normal | Direction:float1=0, slopeAngle:float1=0, yUp:bool1=False | float4 | 25 | 27 | `[-1_1]_to_[0_1]`, `deg_to_rad`, `turnsToDegrees` | This function returns a Normal Map color that matches the directions provided. |
| `hsl_offset` | Functions/colorValues | HSL offset | rgb:float3=1,1,1, hue:float1=1, saturation:float1=1, lightness:float1=1 | float3 | 16 | 17 | `HSLtoRGB`, `RGBtoHSL` | Offsets and RGBA value by adding hue, saturation or lightness inputs. Returns the adjusted value as RGBA. |
| `linear_srgb_to_acescg` | Functions/colorValues | Linear sRGB to ACEScg | input:float3=1,1,1 | float3 | 8 | 9 | `merge_float3` | — |
| `linear_to_sRGB_luminance` | Functions/colorValues | Linear to sRGB (Luminance) | input:float1=1 | float1 | 14 | 15 | — | — |
| `linear_to_sRGB_rgb` | Functions/colorValues | Linear to sRGB | input:float3=1,1,1 | float3 | 9 | 10 | `linear_to_sRGB_luminance` | — |
| `sRGB_to_linear_luminance` | Functions/colorValues | sRGB to linear (Luminance) | input:float1=1 | float1 | 14 | 15 | — | — |
| `sRGB_to_linear_rgb` | Functions/colorValues | sRGB to linear | input:float3=1,1,1 | float3 | 9 | 10 | `sRGB_to_linear_luminance` | — |
| `temperature_to_rgb` | Functions/colorValues | Temperature to RGB | temperature:float1=1 | float3 | 22 | 23 | `temperature_to_rgb_fit` | Converts a temperature in Kelvin to RGB values. |
| `temperature_to_rgb_fit` | Functions/colorValues | Temperature to RGB fit | input:float1=1, a:float1=1, b:float1=1, c:float1=1, d:float1=1 | float1 | 11 | 12 | `Pow` | — |
| `ease_in_circ` | Functions/easings/circ | Ease in circ | input:float1=1 | float1 | 5 | 5 | `oneminus` | Changes the transition of a 0- 1 range to ease in with a circular function. |
| `ease_in_out_circ` | Functions/easings/circ | Ease in out circ | input:float1=1 | float1 | 22 | 26 | `oneminus` | Changes the transition of a 0- 1 range to ease in and out with a circular function. |
| `ease_out_circ` | Functions/easings/circ | Ease out circ | input:float1=1 | float1 | 6 | 6 | `oneminus` | Changes the transition of a 0- 1 range to ease out with a circular function. |
| `ease_in_cubic` | Functions/easings/cubic | Ease in cubic | input:float1=1 | float1 | 3 | 4 | — | Changes the transition of a 0- 1 range to ease in with a cubic function. |
| `ease_in_out_cubic` | Functions/easings/cubic | Ease in out cubic | input:float1=1 | float1 | 17 | 23 | `oneminus` | Changes the transition of a 0- 1 range to ease in and out with a cubic function. |
| `ease_out_cubic` | Functions/easings/cubic | Ease out cubic | input:float1=1 | float1 | 5 | 6 | `oneminus` | Changes the transition of a 0- 1 range to ease out with a cubic function. |
| `ease_in_expo` | Functions/easings/expo | Ease in expo | input:float1=1 | float1 | 8 | 10 | — | Changes the transition of a 0- 1 range to ease in with an exponential function. |
| `ease_in_out_expo` | Functions/easings/expo | Ease in out expo | input:float1=1 | float1 | 25 | 31 | — | Changes the transition of a 0- 1 range to ease in and out with an exponential function. |
| `ease_out_expo` | Functions/easings/expo | Ease out expo | input:float1=1 | float1 | 8 | 9 | `oneminus` | Changes the transition of a 0- 1 range to ease out with an exponential function. |
| `ease_in_out_quad` | Functions/easings/quad | Ease in out quad | input:float1=1 | float1 | 13 | 19 | `oneminus` | Changes the transition of a 0- 1 range to ease in and out with a quadratic function. |
| `ease_in_quad` | Functions/easings/quad | Ease in quad | input:float1=1 | float1 | 2 | 2 | — | Changes the transition of a 0- 1 range to ease in with a quadratic function. |
| `ease_out_quad` | Functions/easings/quad | Ease out quad | input:float1=1 | float1 | 4 | 4 | `oneminus` | Changes the transition of a 0- 1 range to ease out with a quadratic function. |
| `ease_in_out_quart` | Functions/easings/quart | Ease in out quart | input:float1=1 | float1 | 19 | 27 | `oneminus` | Changes the transition of a 0- 1 range to ease in and out with a quart function. |
| `ease_in_quart` | Functions/easings/quart | Ease in quart | input:float1=1 | float1 | 4 | 6 | — | Changes the transition of a 0- 1 range to ease in with a quart function. |
| `ease_out_quart` | Functions/easings/quart | Ease out quart | input:float1=1 | float1 | 6 | 8 | `oneminus` | Changes the transition of a 0- 1 range to ease out with a quart function. |
| `ease_in_out_quint` | Functions/easings/quint | Ease in out quint | input:float1=1 | float1 | 21 | 31 | `oneminus` | Changes the transition of a 0- 1 range to ease in and out with a quint function. |
| `ease_in_quint` | Functions/easings/quint | Ease in quint | input:float1=1 | float1 | 5 | 8 | — | Changes the transition of a 0- 1 range to ease in with a quint function. |
| `ease_out_quint` | Functions/easings/quint | Ease out quint | input:float1=1 | float1 | 7 | 10 | `oneminus` | Changes the transition of a 0- 1 range to ease out with a quint function. |
| `ease_in_out_sine` | Functions/easings/sine | Ease in out sine | input:float1=1 | float1 | 9 | 8 | `Pi` | Changes the transition of a 0- 1 range to ease in and out with a sine function. |
| `ease_in_sine` | Functions/easings/sine | Ease in sine | input:float1=1 | float1 | 7 | 6 | `Pi`, `oneminus` | Changes the transition of a 0- 1 range to ease in with a sine function. |
| `ease_out_sine` | Functions/easings/sine | Ease out sine | input:float1=1 | float1 | 6 | 5 | `Pi` | Changes the transition of a 0- 1 range to ease out with a sine function. |
| `switch_float1_2_inputs` | Functions/switch/Float1 | Switch Float1 2 inputs | input_selection:int1=1, value_1:float1=1, value_2:float1=1 | float1 | 6 | 5 | — | Allows to switch between two Float1 using an Integer1 value. |
| `switch_float1_4_inputs` | Functions/switch/Float1 | Switch Float1 4 inputs | input_selection:int1=1, value_1:float1=1, value_2:float1=1, value_3:float1=1, value_4:float1=1 | float1 | 11 | 13 | `switch_float1_2_inputs` | Allows to switch between four Float1 using an Integer1 value. |
| `switch_float1_8_inputs` | Functions/switch/Float1 | Switch Float1 8 inputs | input_selection:int1=1, value_1:float1=1, value_2:float1=1, value_3:float1=1, value_4:float1=1, value_5:float1=1, value_6:float1=1, value_7:float1=1, value_8:float1=1 | float1 | 15 | 17 | `switch_float1_4_inputs` | Allows to switch between height Float1 using an Integer1 value. |
| `switch_float2_2_inputs` | Functions/switch/Float2 | Switch Float2 2 inputs | input_selection:int1=1, value_1:float2=1,1, value_2:float2=1,1 | float2 | 6 | 5 | — | Allows to switch between two Float2 using an Integer1 value. |
| `switch_float2_4_inputs` | Functions/switch/Float2 | Switch Float2 4 inputs | input_selection:int1=1, value_1:float2=1,1, value_2:float2=1,1, value_3:float2=1,1, value_4:float2=1,1 | float2 | 11 | 13 | `switch_float2_2_inputs` | Allows to switch between four Float2 using an Integer1 value. |
| `switch_float2_8_inputs` | Functions/switch/Float2 | Switch Float2 8 inputs | input_selection:int1=1, value_1:float2=1,1, value_2:float2=1,1, value_3:float2=1,1, value_4:float2=1,1, value_5:float2=1,1, value_6:float2=1,1, value_7:float2=1,1, value_8:float2=1,1 | float2 | 15 | 17 | `switch_float2_4_inputs` | Allows to switch between height Float2 using an Integer1 value. |
| `switch_float3_2_inputs` | Functions/switch/Float3 | Switch Float3 2 inputs | input_selection:int1=1, value_1:float3=1,1,1, value_2:float3=1,1,1 | float3 | 6 | 5 | — | Allows to switch between two Float3 using an Integer1 value. |
| `switch_float3_4_inputs` | Functions/switch/Float3 | Switch Float3 4 inputs | input_selection:int1=1, value_1:float3=1,1,1, value_2:float3=1,1,1, value_3:float3=1,1,1, value_4:float3=1,1,1 | float3 | 11 | 13 | `switch_float3_2_inputs` | Allows to switch between four Float3 using an Integer1 value. |
| `switch_float3_8_inputs` | Functions/switch/Float3 | Switch Float3 8 inputs | input_selection:int1=1, value_1:float3=1,1,1, value_2:float3=1,1,1, value_3:float3=1,1,1, value_4:float3=1,1,1, value_5:float3=1,1,1, value_6:float3=1,1,1, value_7:float3=1,1,1, value_8:float3=1,1,1 | float3 | 15 | 17 | `switch_float3_4_inputs` | Allows to switch between height Float3 using an Integer1 value. |
| `switch_float4_2_inputs` | Functions/switch/Float4 | Switch Float4 2 inputs | input_selection:int1=1, value_1:float4=1,1,1,1, value_2:float4=1,1,1,1 | float4 | 6 | 5 | — | Allows to switch between two Float4 using an Integer1 value. |
| `switch_float4_4_inputs` | Functions/switch/Float4 | Switch Float4 4 inputs | input_selection:int1=1, value_1:float4=1,1,1,1, value_2:float4=1,1,1,1, value_3:float4=1,1,1,1, value_4:float4=1,1,1,1 | float4 | 11 | 13 | `switch_float4_2_inputs` | Allows to switch between four Float4 using an Integer1 value. |
| `switch_float4_8_inputs` | Functions/switch/Float4 | Switch Float4 8 inputs | input_selection:int1=1, value_1:float4=1,1,1,1, value_2:float4=1,1,1,1, value_3:float4=1,1,1,1, value_4:float4=1,1,1,1, value_5:float4=1,1,1,1, value_6:float4=1,1,1,1, value_7:float4=1,1,1,1, value_8:float4=1,1,1,1 | float4 | 15 | 17 | `switch_float4_4_inputs` | Allows to switch between height Float4 using an Integer1 value. |
| `switch_integer1_2_inputs` | Functions/switch/Integer1 | Switch Integer1 2 inputs | input_selection:int1=1, value_1:int1=1, value_2:int1=1 | int1 | 6 | 5 | — | Allows to switch between two Integer1 using an Integer1 value. |
| `switch_integer1_4_inputs` | Functions/switch/Integer1 | Switch Integer1 4 inputs | input_selection:int1=1, value_1:int1=1, value_2:int1=1, value_3:int1=1, value_4:int1=1 | int1 | 11 | 13 | `switch_integer1_2_inputs` | Allows to switch between four Integer1 using an Integer1 value. |
| `switch_integer1_8_inputs` | Functions/switch/Integer1 | Switch Integer1 8 inputs | input_selection:int1=1, value_1:int1=1, value_2:int1=1, value_3:int1=1, value_4:int1=1, value_5:int1=1, value_6:int1=1, value_7:int1=1, value_8:int1=1 | int1 | 15 | 17 | `switch_integer1_4_inputs` | Allows to switch between height Integer1 using an Integer1 value. |
| `switch_integer2_2_inputs` | Functions/switch/Integer2 | Switch Integer2 2 inputs | input_selection:int1=1, value_1:int2=1,1, value_2:int2=1,1 | int2 | 6 | 5 | — | Allows to switch between two Integer2 using an Integer1 value. |
| `switch_integer2_4_inputs` | Functions/switch/Integer2 | Switch Integer2 4 inputs | input_selection:int1=1, value_1:int2=1,1, value_2:int2=1,1, value_3:int2=1,1, value_4:int2=1,1 | int2 | 11 | 13 | `switch_integer2_2_inputs` | Allows to switch between four Integer2 using an Integer1 value. |
| `switch_integer2_8_inputs` | Functions/switch/Integer2 | Switch Integer2 8 inputs | input_selection:int1=1, value_1:int2=1,1, value_2:int2=1,1, value_3:int2=1,1, value_4:int2=1,1, value_5:int2=1,1, value_6:int2=1,1, value_7:int2=1,1, value_8:int2=1,1 | int2 | 15 | 17 | `switch_integer2_4_inputs` | Allows to switch between height Integer2 using an Integer1 value. |
| `switch_integer3_2_inputs` | Functions/switch/Integer3 | Switch Integer3 2 inputs | input_selection:int1=1, value_1:int3=1,1,1, value_2:int3=1,1,1 | int3 | 6 | 5 | — | Allows to switch between two Integer3 using an Integer1 value. |
| `switch_integer3_4_inputs` | Functions/switch/Integer3 | Switch Integer3 2 inputs | input_selection:int1=1, value_1:int3=1,1,1, value_2:int3=1,1,1, value_3:int3=1,1,1, value_4:int3=1,1,1 | int3 | 11 | 13 | `switch_integer3_2_inputs` | Allows to switch between four Integer3 using an Integer1 value. |
| `switch_integer3_8_inputs` | Functions/switch/Integer3 | Switch Integer3 2 inputs | input_selection:int1=1, value_1:int3=1,1,1, value_2:int3=1,1,1, value_3:int3=1,1,1, value_4:int3=1,1,1, value_5:int3=1,1,1, value_6:int3=1,1,1, value_7:int3=1,1,1, value_8:int3=1,1,1 | int3 | 15 | 17 | `switch_integer3_4_inputs` | Allows to switch between height Integer3 using an Integer1 value. |
| `switch_integer4_2_inputs` | Functions/switch/Integer4 | Switch Integer4 2 inputs | input_selection:int1=1, value_1:int4=1,1,1,1, value_2:int4=1,1,1,1 | int4 | 6 | 5 | — | Allows to switch between two Integer4 using an Integer1 value. |
| `switch_integer4_4_inputs` | Functions/switch/Integer4 | Switch Integer4 4 inputs | input_selection:int1=1, value_1:int4=1,1,1,1, value_2:int4=1,1,1,1, value_3:int4=1,1,1,1, value_4:int4=1,1,1,1 | int4 | 11 | 13 | `switch_integer4_2_inputs` | Allows to switch between four Integer4 using an Integer1 value. |
| `switch_integer4_8_inputs` | Functions/switch/Integer4 | Switch Integer4 8 inputs | input_selection:int1=1, value_1:int4=1,1,1,1, value_2:int4=1,1,1,1, value_3:int4=1,1,1,1, value_4:int4=1,1,1,1, value_5:int4=1,1,1,1, value_6:int4=1,1,1,1, value_7:int4=1,1,1,1, value_8:int4=1,1,1,1 | int4 | 15 | 17 | `switch_integer4_4_inputs` | Allows to switch between height Integer4 using an Integer1 value. |
| `booleanToFloat1` | Functions/typeConverters | Boolean to Float1 | Boolean:bool1=False | float1 | 4 | 3 | — | This function converts a boolean type value to a float1 value. If True returns 1.0, else 0.0 |
| `turnsToDegrees` | Functions/typeConverters | Turns to degrees | turns:float1=0 | float1 | 3 | 2 | — | — |

## 4. 计算相关函数的逐节点网表

`n{i}` = 网表中的节点序号；`port<-n{src}` 表示该输入端口由此节点驱动。`instance_of` 表示该节点调用另一个库函数（网表可递归展开）。

### Functions/Math（45）

#### `2Pi` — 2 Pi

- 形参：—
- 输出：`float1`（网表节点 n0）
- 规模：1 节点 / 0 边

```text
    n0   const_float1                float1   consts={"__constant__": "6.28318548"}
    out = n0
```

#### `Curve_Function` — Curve

- 形参：curve:float1=0, input:float1=0
- 输出：`float1`（网表节点 n27）
- 描述：-1 : ease out 0 : linear 1 : ease in
- 规模：29 节点 / 36 边

```text
    n0   sqrt                        float1   a<-n5
    n1   const_float1                float1   consts={"__constant__": "1"}
    n2   get_float1                  float1   consts={"__constant__": "curve"}
    n3   get_float1                  float1   consts={"__constant__": "input"}
    n4   mul                         float1   a<-n3 b<-n3
    n5   sub                         float1   a<-n1 b<-n4
    n6   const_float1                float1   consts={"__constant__": "1"}
    n7   sub                         float1   a<-n6 b<-n0
    n8   mul                         float1   a<-n7 b<-n2
    n9   add                         float1   a<-n8 b<-n12
    n10  const_float1                float1   consts={"__constant__": "1"}
    n11  sub                         float1   a<-n10 b<-n2
    n12  mul                         float1   a<-n3 b<-n11
    n13  mul                         float1   a<-n23 b<-n28
    n14  add                         float1   a<-n18 b<-n13
    n15  sqrt                        float1   a<-n22
    n16  const_float1                float1   consts={"__constant__": "1"}
    n17  sub                         float1   a<-n23 b<-n16
    n18  mul                         float1   a<-n15 b<-n24
    n19  mul                         float1   a<-n17 b<-n17
    n20  const_float1                float1   consts={"__constant__": "1"}
    n21  const_float1                float1   consts={"__constant__": "1"}
    n22  sub                         float1   a<-n21 b<-n19
    n23  get_float1                  float1   consts={"__constant__": "input"}
    n24  neg                         float1   a<-n2
    n25  lr                          bool1    a<-n2 b<-n26
    n26  const_float1                float1   consts={"__constant__": "0"}
    n27  ifelse                      float1   condition<-n25 ifpath<-n14 elsepath<-n9
    n28  add                         float1   a<-n20 b<-n2
    out = n27
```

#### `Equality_Boolean` — Equality boolean

- 形参：A:bool1=False, B:bool1=False
- 输出：`bool1`（网表节点 n3）
- 规模：7 节点 / 8 边

```text
    n0   get_bool                    bool1    consts={"__constant__": "A"}
    n1   get_bool                    bool1    consts={"__constant__": "B"}
    n2   and                         bool1    a<-n0 b<-n1
    n3   or                          bool1    a<-n2 b<-n6
    n4   not                         bool1    a<-n0
    n5   not                         bool1    a<-n1
    n6   and                         bool1    a<-n4 b<-n5
    out = n3
```

#### `Equality_Float2` — Equality Float2

- 形参：A:float2=0,0, B:float2=0,0
- 输出：`bool1`（网表节点 n8）
- 规模：9 节点 / 10 边

```text
    n0   get_float2                  float2   consts={"__constant__": "A"}
    n1   get_float2                  float2   consts={"__constant__": "B"}
    n2   eq                          bool1    a<-n3 b<-n4
    n3   swizzle1                    float1   consts={"__constant__": 0}  vector<-n0
    n4   swizzle1                    float1   consts={"__constant__": 0}  vector<-n1
    n5   eq                          bool1    a<-n6 b<-n7
    n6   swizzle1                    float1   consts={"__constant__": 1}  vector<-n0
    n7   swizzle1                    float1   consts={"__constant__": 1}  vector<-n1
    n8   and                         bool1    a<-n2 b<-n5
    out = n8
```

#### `Equality_Float3` — Equality Float3

- 形参：A:float3=0,0,0, B:float3=0,0,0
- 输出：`bool1`（网表节点 n8）
- 规模：9 节点 / 10 边；调用 `Equality_Float2`

```text
    n0   get_float3                  float3   consts={"__constant__": "A"}
    n1   get_float3                  float3   consts={"__constant__": "B"}
    n2   swizzle2                    float2   consts={"__constant__": "0,1"}  vector<-n0
    n3   swizzle2                    float2   consts={"__constant__": "0,1"}  vector<-n1
    n4   swizzle1                    float1   consts={"__constant__": 2}  vector<-n0
    n5   instance                    bool1    instance_of=Equality_Float2           A<-n2 B<-n3
    n6   swizzle1                    float1   consts={"__constant__": 2}  vector<-n1
    n7   eq                          bool1    a<-n4 b<-n6
    n8   and                         bool1    a<-n5 b<-n7
    out = n8
```

#### `Equality_Float4` — Equality Float4

- 形参：A:float4=0,0,0,0, B:float4=0,0,0,0
- 输出：`bool1`（网表节点 n8）
- 规模：9 节点 / 10 边；调用 `Equality_Float2`

```text
    n0   get_float4                  float4   consts={"__constant__": "A"}
    n1   get_float4                  float4   consts={"__constant__": "B"}
    n2   swizzle2                    float2   consts={"__constant__": "0,1"}  vector<-n0
    n3   swizzle2                    float2   consts={"__constant__": "2,3"}  vector<-n0
    n4   swizzle2                    float2   consts={"__constant__": "0,1"}  vector<-n1
    n5   swizzle2                    float2   consts={"__constant__": "2,3"}  vector<-n1
    n6   instance                    bool1    instance_of=Equality_Float2           A<-n2 B<-n4
    n7   instance                    bool1    instance_of=Equality_Float2           A<-n3 B<-n5
    n8   and                         bool1    a<-n6 b<-n7
    out = n8
```

#### `Ln` — Ln

- 形参：a:float1=0
- 输出：`float1`（网表节点 n2）
- 描述：The Ln function returns the Natural logarithm value of entry.
- 规模：5 节点 / 4 边

```text
    n0   get_float1                  float1   consts={"__constant__": "a"}
    n1   log                         float1   a<-n0
    n2   div                         float1   a<-n1 b<-n4
    n3   const_float1                float1   consts={"__constant__": "1"}
    n4   exp                         float1   a<-n3
    out = n2
```

#### `NotEqual_Boolean` — Not equal boolean

- 形参：A:bool1=False, B:bool1=False
- 输出：`bool1`（网表节点 n3）
- 规模：4 节点 / 3 边；调用 `Equality_Boolean`

```text
    n0   get_bool                    bool1    consts={"__constant__": "A"}
    n1   get_bool                    bool1    consts={"__constant__": "B"}
    n2   instance                    bool1    instance_of=Equality_Boolean          A<-n0 B<-n1
    n3   not                         bool1    a<-n2
    out = n3
```

#### `NotEqual_Float2` — Not equal Float2

- 形参：A:float2=0,0, B:float2=0,0
- 输出：`bool1`（网表节点 n3）
- 规模：4 节点 / 3 边；调用 `Equality_Float2`

```text
    n0   get_float2                  float2   consts={"__constant__": "A"}
    n1   get_float2                  float2   consts={"__constant__": "B"}
    n2   instance                    bool1    instance_of=Equality_Float2           A<-n0 B<-n1
    n3   not                         bool1    a<-n2
    out = n3
```

#### `NotEqual_Float3` — Not equal Float3

- 形参：A:float3=0,0,0, B:float3=0,0,0
- 输出：`bool1`（网表节点 n3）
- 规模：4 节点 / 3 边；调用 `Equality_Float3`

```text
    n0   get_float3                  float3   consts={"__constant__": "A"}
    n1   get_float3                  float3   consts={"__constant__": "B"}
    n2   instance                    bool1    instance_of=Equality_Float3           A<-n0 B<-n1
    n3   not                         bool1    a<-n2
    out = n3
```

#### `NotEqual_Float4` — Not equal Float4

- 形参：A:float4=0,0,0,0, B:float4=0,0,0,0
- 输出：`bool1`（网表节点 n3）
- 规模：4 节点 / 3 边；调用 `Equality_Float4`

```text
    n0   get_float4                  float4   consts={"__constant__": "A"}
    n1   get_float4                  float4   consts={"__constant__": "B"}
    n2   instance                    bool1    instance_of=Equality_Float4           A<-n0 B<-n1
    n3   not                         bool1    a<-n2
    out = n3
```

#### `Pi` — Pi

- 形参：—
- 输出：`float1`（网表节点 n0）
- 规模：1 节点 / 0 边

```text
    n0   const_float1                float1   consts={"__constant__": "3.14159274"}
    out = n0
```

#### `Pow` — Pow (Deprecated)

- 形参：x:float1=0, n:float1=0
- 输出：`float1`（网表节点 n9）
- 描述：Returns x^n.  This function is now deprecated as the engine v9 provides an atomic Pow function.
- 规模：11 节点 / 12 边

```text
    n0   get_float1                  float1   consts={"__constant__": "n"}
    n1   get_float1                  float1   consts={"__constant__": "x"}
    n2   pow2                        float1   a<-n4
    n3   log                         float1   a<-n1
    n4   mul                         float1   a<-n7 b<-n0
    n5   log                         float1   a<-n6
    n6   const_float1                float1   consts={"__constant__": "2"}
    n7   div                         float1   a<-n3 b<-n5
    n8   const_float1                float1   consts={"__constant__": "0"}
    n9   ifelse                      float1   condition<-n10 ifpath<-n8 elsepath<-n2
    n10  lreq                        bool1    a<-n1 b<-n8
    out = n9
```

#### `Roughness` — Roughness

- 形参：Roughness:float1=0, CurrentLevel:int1=0, TotalLevel:int1=0, GlobalOpacity:float1=0
- 输出：`float1`（网表节点 n14）
- 规模：24 节点 / 28 边

```text
    n0   get_float1                  float1   consts={"__constant__": "Roughness"}
    n1   const_float1                float1   consts={"__constant__": "0"}
    n2   ifelse                      float1   condition<-n16 ifpath<-n9 elsepath<-n6
    n3   eq                          bool1    a<-n0 b<-n1
    n4   const_float1                float1   consts={"__constant__": "1"}
    n5   const_float1                float1   consts={"__constant__": "1"}
    n6   div                         float1   a<-n19 b<-n21
    n7   sub                         float1   a<-n5 b<-n0
    n8   ifelse                      float1   condition<-n3 ifpath<-n11 elsepath<-n2
    n9   div                         float1   a<-n12 b<-n10
    n10  tofloat                     float1   value<-n15
    n11  const_float1                float1   consts={"__constant__": "1"}
    n12  const_float1                float1   consts={"__constant__": "1"}
    n13  get_float1                  float1   consts={"__constant__": "GlobalOpacity"}
    n14  mul                         float1   a<-n13 b<-n8
    n15  get_integer1                int1     consts={"__constant__": "TotalLevel"}
    n16  eq                          bool1    a<-n0 b<-n4
    n17  get_integer1                int1     consts={"__constant__": "CurrentLevel"}
    n18  tofloat                     float1   value<-n17
    n19  mul                         float1   a<-n7 b<-n22
    n20  const_float1                float1   consts={"__constant__": "1"}
    n21  sub                         float1   a<-n20 b<-n23
    n22  pow                         float1   a<-n0 b<-n18
    n23  pow                         float1   a<-n0 b<-n10
    out = n14
```

#### `average_float1` — Average Float1

- 形参：a:float1=1, b:float1=1
- 输出：`float1`（网表节点 n4）
- 描述：Returns the average value of A and B.
- 规模：5 节点 / 4 边

```text
    n0   add                         float1   a<-n2 b<-n3
    n1   const_float1                float1   consts={"__constant__": "0.5"}
    n2   get_float1                  float1   consts={"__constant__": "a"}
    n3   get_float1                  float1   consts={"__constant__": "b"}
    n4   mul                         float1   a<-n0 b<-n1
    out = n4
```

#### `average_float2` — Average Float2

- 形参：a:float2=1,1, b:float2=1,1
- 输出：`float2`（网表节点 n3）
- 描述：Returns the average value of A and B.
- 规模：5 节点 / 4 边

```text
    n0   get_float2                  float2   consts={"__constant__": "a"}
    n1   get_float2                  float2   consts={"__constant__": "b"}
    n2   add                         float2   a<-n0 b<-n1
    n3   mulscalar                   float2   a<-n2 scalar<-n4
    n4   const_float1                float1   consts={"__constant__": "0.5"}
    out = n3
```

#### `average_float3` — Average Float3

- 形参：a:float3=1,1,1, b:float3=1,1,1
- 输出：`float3`（网表节点 n1）
- 描述：Returns the average value of A and B.
- 规模：5 节点 / 4 边

```text
    n0   add                         float3   a<-n3 b<-n4
    n1   mulscalar                   float3   a<-n0 scalar<-n2
    n2   const_float1                float1   consts={"__constant__": "0.5"}
    n3   get_float3                  float3   consts={"__constant__": "a"}
    n4   get_float3                  float3   consts={"__constant__": "b"}
    out = n1
```

#### `average_float4` — Average Float4

- 形参：a:float4=1,1,1,1, b:float4=1,1,1,1
- 输出：`float4`（网表节点 n1）
- 描述：Returns the average value of A and B.
- 规模：5 节点 / 4 边

```text
    n0   add                         float4   a<-n3 b<-n4
    n1   mulscalar                   float4   a<-n0 scalar<-n2
    n2   const_float1                float1   consts={"__constant__": "0.5"}
    n3   get_float4                  float4   consts={"__constant__": "a"}
    n4   get_float4                  float4   consts={"__constant__": "b"}
    out = n1
```

#### `clamp` — Clamp

- 形参：input:float1=1, min:float1=1, max:float1=1
- 输出：`float1`（网表节点 n3）
- 描述：Returns Min or Max if the input is outside of the Min/Max range.
- 规模：5 节点 / 4 边

```text
    n0   get_float1                  float1   consts={"__constant__": "input"}
    n1   get_float1                  float1   consts={"__constant__": "max"}
    n2   get_float1                  float1   consts={"__constant__": "min"}
    n3   max                         float1   a<-n2 b<-n4
    n4   min                         float1   a<-n0 b<-n1
    out = n3
```

#### `cross_product` — Cross product

- 形参：a:float3=1,1,1, b:float3=1,1,1
- 输出：`float3`（网表节点 n4）
- 描述：Returns the cross product of two three-component vectors
- 规模：9 节点 / 10 边

```text
    n0   get_float3                  float3   consts={"__constant__": "a"}
    n1   get_float3                  float3   consts={"__constant__": "b"}
    n2   mul                         float3   a<-n3 b<-n5
    n3   swizzle3                    float3   consts={"__constant__": "1,2,0"}  vector<-n0
    n4   sub                         float3   a<-n2 b<-n7
    n5   swizzle3                    float3   consts={"__constant__": "2,0,1"}  vector<-n1
    n6   swizzle3                    float3   consts={"__constant__": "2,0,1"}  vector<-n0
    n7   mul                         float3   a<-n6 b<-n8
    n8   swizzle3                    float3   consts={"__constant__": "1,2,0"}  vector<-n1
    out = n4
```

#### `cross_product_vec2` — Cross product Vec2

- 形参：a:float2=1,1, b:float2=1,1
- 输出：`float1`（网表节点 n7）
- 描述：Returns the cross product of two two-component vectors
- 规模：11 节点 / 12 边

```text
    n0   mul                         float1   a<-n5 b<-n4
    n1   swizzle1                    float1   consts={"__constant__": 0}  vector<-n2
    n2   passthrough                 float2   input<-n9
    n3   swizzle1                    float1   consts={"__constant__": 1}  vector<-n6
    n4   swizzle1                    float1   consts={"__constant__": 1}  vector<-n2
    n5   swizzle1                    float1   consts={"__constant__": 0}  vector<-n6
    n6   passthrough                 float2   input<-n10
    n7   sub                         float1   a<-n8 b<-n0
    n8   mul                         float1   a<-n3 b<-n1
    n9   get_float2                  float2   consts={"__constant__": "a"}
    n10  get_float2                  float2   consts={"__constant__": "b"}
    out = n7
```

#### `distance_vec2` — Distance Float2

- 形参：a:float2=1,1, b:float2=1,1
- 输出：`float1`（网表节点 n3）
- 描述：Returns the Euclidean distance between two points (in 2D).
- 规模：4 节点 / 3 边；调用 `length_vec2`

```text
    n0   get_float2                  float2   consts={"__constant__": "a"}
    n1   get_float2                  float2   consts={"__constant__": "b"}
    n2   sub                         float2   a<-n1 b<-n0
    n3   instance                    float1   instance_of=length_vec2               v<-n2
    out = n3
```

#### `distance_vec3` — Distance Float3

- 形参：a:float3=1,1,1, b:float3=1,1,1
- 输出：`float1`（网表节点 n2）
- 描述：Returns the Euclidean distance between two points.
- 规模：4 节点 / 3 边；调用 `length_vec3`

```text
    n0   get_float3                  float3   consts={"__constant__": "a"}
    n1   get_float3                  float3   consts={"__constant__": "b"}
    n2   instance                    float1   instance_of=length_vec3               v<-n3
    n3   sub                         float3   a<-n1 b<-n0
    out = n2
```

#### `divide_float2` — Scalar division Float2

- 形参：input:float2=1,1, scalar:float1=1
- 输出：`float2`（网表节点 n6）
- 描述：Divide a float 2 by a given scalar.
- 规模：7 节点 / 8 边

```text
    n0   div                         float1   a<-n1 b<-n5
    n1   swizzle1                    float1   consts={"__constant__": 0}  vector<-n2
    n2   get_float2                  float2   consts={"__constant__": "input"}
    n3   swizzle1                    float1   consts={"__constant__": 1}  vector<-n2
    n4   div                         float1   a<-n3 b<-n5
    n5   get_float1                  float1   consts={"__constant__": "scalar"}
    n6   vector2                     float2   componentsin<-n0 componentslast<-n4
    out = n6
```

#### `divide_float3` — Scalar division Float3

- 形参：input:float3=1,1,1, scalar:float1=1
- 输出：`float3`（网表节点 n9）
- 描述：Divide a float 3 by a given scalar.
- 规模：10 节点 / 13 边

```text
    n0   div                         float1   a<-n1 b<-n4
    n1   swizzle1                    float1   consts={"__constant__": 0}  vector<-n8
    n2   swizzle1                    float1   consts={"__constant__": 1}  vector<-n8
    n3   div                         float1   a<-n2 b<-n4
    n4   get_float1                  float1   consts={"__constant__": "scalar"}
    n5   vector2                     float2   componentsin<-n0 componentslast<-n3
    n6   div                         float1   a<-n7 b<-n4
    n7   swizzle1                    float1   consts={"__constant__": 2}  vector<-n8
    n8   get_float3                  float3   consts={"__constant__": "input"}
    n9   vector3                     float3   componentsin<-n5 componentslast<-n6
    out = n9
```

#### `divide_float4` — Scalar division Float4

- 形参：input:float4=1,1,1,1, scalar:float1=1
- 输出：`float4`（网表节点 n12）
- 描述：Divide a float 4 by a given scalar.
- 规模：13 节点 / 18 边

```text
    n0   div                         float1   a<-n1 b<-n4
    n1   swizzle1                    float1   consts={"__constant__": 0}  vector<-n10
    n2   swizzle1                    float1   consts={"__constant__": 1}  vector<-n10
    n3   div                         float1   a<-n2 b<-n4
    n4   get_float1                  float1   consts={"__constant__": "scalar"}
    n5   vector2                     float2   componentsin<-n0 componentslast<-n3
    n6   div                         float1   a<-n7 b<-n4
    n7   swizzle1                    float1   consts={"__constant__": 2}  vector<-n10
    n8   div                         float1   a<-n9 b<-n4
    n9   swizzle1                    float1   consts={"__constant__": 3}  vector<-n10
    n10  get_float4                  float4   consts={"__constant__": "input"}
    n11  vector2                     float2   componentsin<-n6 componentslast<-n8
    n12  vector4                     float4   componentsin<-n5 componentslast<-n11
    out = n12
```

#### `fmod` — Fmod

- 形参：a:float1=1, b:float1=1
- 输出：`float1`（网表节点 n7）
- 描述：Returns the remainder of a/b with the same sign as a.
- 规模：11 节点 / 13 边；调用 `frac`

```text
    n0   get_float1                  float1   consts={"__constant__": "a"}
    n1   get_float1                  float1   consts={"__constant__": "b"}
    n2   instance                    float1   instance_of=frac                      input<-n4
    n3   div                         float1   a<-n0 b<-n1
    n4   abs                         float1   a<-n3
    n5   mul                         float1   a<-n2 b<-n6
    n6   abs                         float1   a<-n1
    n7   ifelse                      float1   condition<-n8 ifpath<-n10 elsepath<-n5
    n8   lr                          bool1    a<-n0 b<-n9
    n9   const_float1                float1   consts={"__constant__": "0"}
    n10  neg                         float1   a<-n5
    out = n7
```

#### `frac` — Frac

- 形参：input:float1=1
- 输出：`float1`（网表节点 n1）
- 描述：Returns the fractional portion of a scalar.
- 规模：3 节点 / 3 边

```text
    n0   get_float1                  float1   consts={"__constant__": "input"}
    n1   sub                         float1   a<-n0 b<-n2
    n2   floor                       float1   a<-n0
    out = n1
```

#### `length_vec2` — Length Float2

- 形参：v:float2=1,1
- 输出：`float1`（网表节点 n1）
- 描述：Returns scalar Euclidean length of a vector float2.
- 规模：3 节点 / 3 边

```text
    n0   dot                         float1   a<-n2 b<-n2
    n1   sqrt                        float1   a<-n0
    n2   get_float2                  float2   consts={"__constant__": "v"}
    out = n1
```

#### `length_vec3` — Length Float3

- 形参：v:float3=1,1,1
- 输出：`float1`（网表节点 n2）
- 描述：Returns scalar Euclidean length of a vector float3.
- 规模：3 节点 / 3 边

```text
    n0   get_float3                  float3   consts={"__constant__": "v"}
    n1   dot                         float1   a<-n0 b<-n0
    n2   sqrt                        float1   a<-n1
    out = n2
```

#### `merge_float3` — Merge Float3

- 形参：x:float1=1, y:float1=1, z:float1=1
- 输出：`float3`（网表节点 n0）
- 描述：Combines 3 float into a vector 3.
- 规模：5 节点 / 4 边

```text
    n0   vector3                     float3   componentsin<-n1 componentslast<-n4
    n1   vector2                     float2   componentsin<-n2 componentslast<-n3
    n2   get_float1                  float1   consts={"__constant__": "x"}
    n3   get_float1                  float1   consts={"__constant__": "y"}
    n4   get_float1                  float1   consts={"__constant__": "z"}
    out = n0
```

#### `merge_float4` — Merge Float4

- 形参：x:float1=1, y:float1=1, z:float1=1, w:float1=1
- 输出：`float4`（网表节点 n5）
- 描述：Combines 4 float into a vector 4.
- 规模：7 节点 / 6 边

```text
    n0   vector2                     float2   componentsin<-n1 componentslast<-n2
    n1   get_float1                  float1   consts={"__constant__": "x"}
    n2   get_float1                  float1   consts={"__constant__": "y"}
    n3   get_float1                  float1   consts={"__constant__": "z"}
    n4   vector2                     float2   componentsin<-n3 componentslast<-n6
    n5   vector4                     float4   componentsin<-n0 componentslast<-n4
    n6   get_float1                  float1   consts={"__constant__": "w"}
    out = n5
```

#### `normalize_vec2` — Normalize Vec2

- 形参：input:float2=1,1
- 输出：`float2`（网表节点 n5）
- 描述：Normalizes a Vec2.
- 规模：6 节点 / 7 边

```text
    n0   get_float2                  float2   consts={"__constant__": "input"}
    n1   dot                         float1   a<-n0 b<-n0
    n2   sqrt                        float1   a<-n1
    n3   const_float1                float1   consts={"__constant__": "1"}
    n4   div                         float1   a<-n3 b<-n2
    n5   mulscalar                   float2   a<-n0 scalar<-n4
    out = n5
```

#### `normalize_vec3` — Normalize Vec3

- 形参：input:float3=1,1,1
- 输出：`float3`（网表节点 n4）
- 描述：Normalizes a Vec3.
- 规模：6 节点 / 7 边

```text
    n0   dot                         float1   a<-n5 b<-n5
    n1   sqrt                        float1   a<-n0
    n2   const_float1                float1   consts={"__constant__": "1"}
    n3   div                         float1   a<-n2 b<-n1
    n4   mulscalar                   float3   a<-n5 scalar<-n3
    n5   get_float3                  float3   consts={"__constant__": "input"}
    out = n4
```

#### `normalize_vec4` — Normalize Vec4

- 形参：input:float4=1,1,1,1
- 输出：`float4`（网表节点 n4）
- 描述：Normalizes a Vec4.
- 规模：6 节点 / 7 边

```text
    n0   dot                         float1   a<-n5 b<-n5
    n1   sqrt                        float1   a<-n0
    n2   const_float1                float1   consts={"__constant__": "1"}
    n3   div                         float1   a<-n2 b<-n1
    n4   mulscalar                   float4   a<-n5 scalar<-n3
    n5   get_float4                  float4   consts={"__constant__": "input"}
    out = n4
```

#### `oneminus` — One minus

- 形参：x:float1=1
- 输出：`float1`（网表节点 n1）
- 描述：Returns one minus x (1 - x).
- 规模：3 节点 / 2 边

```text
    n0   get_float1                  float1   consts={"__constant__": "x"}
    n1   sub                         float1   a<-n2 b<-n0
    n2   const_float1                float1   consts={"__constant__": "1"}
    out = n1
```

#### `orthogonal_vec2` — Orthogonal Vec2

- 形参：input:float2=1,1
- 输出：`float2`（网表节点 n0）
- 描述：Returns an orthognal vector of the input vec2.
- 规模：4 节点 / 3 边

```text
    n0   mul                         float2   a<-n1 b<-n2
    n1   swizzle2                    float2   consts={"__constant__": "1,0"}  vector<-n3
    n2   const_float2                float2   consts={"__constant__": "1,-1"}
    n3   get_float2                  float2   consts={"__constant__": "input"}
    out = n0
```

#### `reflect` — Reflect

- 形参：i:float3=1,1,1, n:float3=1,1,1
- 输出：`float3`（网表节点 n2）
- 描述：Returns the reflectiton vector given an incidence vector and a normal vector.
- 规模：7 节点 / 8 边

```text
    n0   get_float3                  float3   consts={"__constant__": "i"}
    n1   get_float3                  float3   consts={"__constant__": "n"}
    n2   sub                         float3   a<-n0 b<-n4
    n3   dot                         float1   a<-n1 b<-n0
    n4   mulscalar                   float3   a<-n5 scalar<-n3
    n5   mulscalar                   float3   a<-n1 scalar<-n6
    n6   const_float1                float1   consts={"__constant__": "2"}
    out = n2
```

#### `round_float1` — Round Float1

- 形参：input:float1=1
- 输出：`float1`（网表节点 n3）
- 描述：Rounds a Float 1. Rounds up when decimal is greater or equal than 0.5
- 规模：4 节点 / 3 边

```text
    n0   get_float1                  float1   consts={"__constant__": "input"}
    n1   const_float1                float1   consts={"__constant__": "0.5"}
    n2   add                         float1   a<-n0 b<-n1
    n3   floor                       float1   a<-n2
    out = n3
```

#### `saturate` — Saturate

- 形参：input:float1=1
- 输出：`float1`（网表节点 n4）
- 描述：- Returns 0 if input is lower than 0. - Returns 1 if input is greater than 1.
- 规模：5 节点 / 4 边

```text
    n0   const_float1                float1   consts={"__constant__": "0"}
    n1   get_float1                  float1   consts={"__constant__": "input"}
    n2   const_float1                float1   consts={"__constant__": "1"}
    n3   min                         float1   a<-n1 b<-n2
    n4   max                         float1   a<-n0 b<-n3
    out = n4
```

#### `saturate_float2` — Saturate Float2

- 形参：input:float2=1,1
- 输出：`float2`（网表节点 n0）
- 描述：For each vector component: - Returns 0 if input is lower than 0. - Returns 1 if input is greater than 1.
- 规模：6 节点 / 6 边；调用 `saturate`

```text
    n0   vector2                     float2   componentsin<-n2 componentslast<-n1
    n1   instance                    float1   instance_of=saturate                  input<-n3
    n2   instance                    float1   instance_of=saturate                  input<-n4
    n3   swizzle1                    float1   consts={"__constant__": 1}  vector<-n5
    n4   swizzle1                    float1   consts={"__constant__": 0}  vector<-n5
    n5   get_float2                  float2   consts={"__constant__": "input"}
    out = n0
```

#### `sign` — Sign

- 形参：x:float1=1
- 输出：`float1`（网表节点 n2）
- 描述：Returns the sign of a scalar. If X == 0, returns 1.
- 规模：6 节点 / 5 边

```text
    n0   get_float1                  float1   consts={"__constant__": "x"}
    n1   const_float1                float1   consts={"__constant__": "0"}
    n2   ifelse                      float1   condition<-n5 ifpath<-n3 elsepath<-n4
    n3   const_float1                float1   consts={"__constant__": "1"}
    n4   const_float1                float1   consts={"__constant__": "-1"}
    n5   gteq                        bool1    a<-n0 b<-n1
    out = n2
```

#### `smoothstep` — Smoothstep

- 形参：a:float1=1, b:float1=1, x:float1=1
- 输出：`float1`（网表节点 n7）
- 描述：Smooth interpolation between A and B in function of X.
- 规模：13 节点 / 15 边；调用 `saturate`

```text
    n0   get_float1                  float1   consts={"__constant__": "x"}
    n1   get_float1                  float1   consts={"__constant__": "a"}
    n2   get_float1                  float1   consts={"__constant__": "b"}
    n3   sub                         float1   a<-n0 b<-n1
    n4   div                         float1   a<-n3 b<-n5
    n5   sub                         float1   a<-n2 b<-n1
    n6   mul                         float1   a<-n12 b<-n12
    n7   mul                         float1   a<-n6 b<-n9
    n8   const_float1                float1   consts={"__constant__": "3"}
    n9   sub                         float1   a<-n8 b<-n11
    n10  const_float1                float1   consts={"__constant__": "2"}
    n11  mul                         float1   a<-n10 b<-n12
    n12  instance                    float1   instance_of=saturate                  input<-n4
    out = n7
```

#### `step` — Step

- 形参：a:float1=1, x:float1=1
- 输出：`float1`（网表节点 n3）
- 描述：Returns one if x is greater than or equal to a, and zero otherwise.
- 规模：6 节点 / 5 边

```text
    n0   get_float1                  float1   consts={"__constant__": "a"}
    n1   get_float1                  float1   consts={"__constant__": "x"}
    n2   gteq                        bool1    a<-n1 b<-n0
    n3   ifelse                      float1   condition<-n2 ifpath<-n4 elsepath<-n5
    n4   const_float1                float1   consts={"__constant__": "1"}
    n5   const_float1                float1   consts={"__constant__": "0"}
    out = n3
```

#### `truncate_float1_decimals` — Truncate Float1

- 形参：input:float1=1, decimals:int1=1
- 输出：`float1`（网表节点 n8）
- 描述：Truncates a Float1's to a specific amount of decimals.
- 规模：11 节点 / 13 边；调用 `Pow`

```text
    n0   get_float1                  float1   consts={"__constant__": "input"}
    n1   mul                         float1   a<-n0 b<-n6
    n2   const_float1                float1   consts={"__constant__": "10"}
    n3   floor                       float1   a<-n1
    n4   div                         float1   a<-n3 b<-n6
    n5   get_integer1                int1     consts={"__constant__": "decimals"}
    n6   instance                    float1   instance_of=Pow                       x<-n2 n<-n7
    n7   tofloat                     float1   value<-n5
    n8   ifelse                      float1   condition<-n9 ifpath<-n0 elsepath<-n4
    n9   lreq                        bool1    a<-n5 b<-n10
    n10  const_int1                  int1     consts={"__constant__": 0}
    out = n8
```

### Functions/Math/Trigo（3）

#### `acos` — acos

- 形参：x:float1=1
- 输出：`float1`（网表节点 n1）
- 描述：Returns the arc cosine of entry value: acos(x).
- 规模：6 节点 / 5 边；调用 `Pi`, `asin`

```text
    n0   get_float1                  float1   consts={"__constant__": "x"}
    n1   sub                         float1   a<-n2 b<-n3
    n2   mul                         float1   a<-n4 b<-n5
    n3   instance                    float1   instance_of=asin                      x<-n0
    n4   instance                    float1   instance_of=Pi
    n5   const_float1                float1   consts={"__constant__": "0.5"}
    out = n1
```

#### `asin` — asin

- 形参：x:float1=1
- 输出：`float1`（网表节点 n18）
- 描述：Returns the arc sine of entry value: asin(x).
- 规模：22 节点 / 27 边

```text
    n0   const_float1                float1   consts={"__constant__": "-0.0187292993"}
    n1   const_float1                float1   consts={"__constant__": "1.57072878"}
    n2   const_float1                float1   consts={"__constant__": "0.0742610022"}
    n3   const_float1                float1   consts={"__constant__": "-0.212114394"}
    n4   get_float1                  float1   consts={"__constant__": "x"}
    n5   abs                         float1   a<-n4
    n6   mul                         float1   a<-n5 b<-n0
    n7   add                         float1   a<-n6 b<-n2
    n8   mul                         float1   a<-n5 b<-n7
    n9   add                         float1   a<-n8 b<-n3
    n10  mul                         float1   a<-n5 b<-n9
    n11  add                         float1   a<-n10 b<-n1
    n12  sub                         float1   a<-n13 b<-n5
    n13  const_float1                float1   consts={"__constant__": "1"}
    n14  sqrt                        float1   a<-n12
    n15  const_float1                float1   consts={"__constant__": "1.57079637"}
    n16  mul                         float1   a<-n14 b<-n11
    n17  sub                         float1   a<-n15 b<-n16
    n18  ifelse                      float1   condition<-n19 ifpath<-n17 elsepath<-n21
    n19  gteq                        bool1    a<-n4 b<-n20
    n20  const_float1                float1   consts={"__constant__": "0"}
    n21  sub                         float1   a<-n16 b<-n15
    out = n18
```

#### `deg_to_rad` — Degrees to radians

- 形参：deg:float1=0
- 输出：`float1`（网表节点 n3）
- 描述：Converts an angle input from degrees to radians, which is the most commonly used in Substance. For GUI only needs, it is recommended to use the Angle Editor along with a Float1 value type. Use this function in another when you need to convert angle value types.
- 规模：5 节点 / 4 边；调用 `Pi`

```text
    n0   get_float1                  float1   consts={"__constant__": "deg"}
    n1   div                         float1   a<-n4 b<-n2
    n2   const_float1                float1   consts={"__constant__": "180"}
    n3   mul                         float1   a<-n0 b<-n1
    n4   instance                    float1   instance_of=Pi
    out = n3
```

### Functions/Math/Parity（3）

#### `EvenCount` — Even count

- 形参：Input:float1=0
- 输出：`float1`（网表节点 n4）
- 描述：Returns the count of even numbers contained in the input.
- 规模：5 节点 / 4 边

```text
    n0   get_float1                  float1   consts={"__constant__": "Input"}
    n1   floor                       float1   a<-n0
    n2   const_float1                float1   consts={"__constant__": "2"}
    n3   div                         float1   a<-n1 b<-n2
    n4   ceil                        float1   a<-n3
    out = n4
```

#### `OddCount` — Odd count

- 形参：Input:float1=0
- 输出：`float1`（网表节点 n4）
- 描述：Returns the count of odd numbers contained in the input.
- 规模：5 节点 / 4 边

```text
    n0   get_float1                  float1   consts={"__constant__": "Input"}
    n1   floor                       float1   a<-n0
    n2   const_float1                float1   consts={"__constant__": "2"}
    n3   div                         float1   a<-n1 b<-n2
    n4   floor                       float1   a<-n3
    out = n4
```

#### `ParityTest` — Parity test

- 形参：Input:float1=0
- 输出：`bool1`（网表节点 n0）
- 描述：Returns true if the input is a even number.
- 规模：10 节点 / 11 边

```text
    n0   gt                          bool1    a<-n9 b<-n8
    n1   floor                       float1   a<-n2
    n2   mul                         float1   a<-n5 b<-n3
    n3   const_float1                float1   consts={"__constant__": "0.25"}
    n4   const_float1                float1   consts={"__constant__": "1"}
    n5   add                         float1   a<-n7 b<-n4
    n6   get_float1                  float1   consts={"__constant__": "Input"}
    n7   add                         float1   a<-n6 b<-n6
    n8   sub                         float1   a<-n2 b<-n1
    n9   const_float1                float1   consts={"__constant__": "0.5"}
    out = n0
```

### Functions/Ranges（9）

#### `Height_Balance_Fn` — Height balance

- 形参：Depth_Balance:float1=0
- 输出：`float4`（网表节点 n4）
- 描述：This function returns a float4 in which : X is minimum of the Higher Y is maximum of the Higher Z is minimum of the Lower W is maximum of the Lower The input goes from -1.0 to 1.0. A 0 value input returns a balanced output of 0.0 ; 0.5 ; 0.5 ; 1.0.
- 规模：16 节点 / 22 边

```text
    n0   get_float1                  float1   consts={"__constant__": "Depth_Balance"}
    n1   const_float1                float1   consts={"__constant__": "1"}
    n2   const_float1                float1   consts={"__constant__": "0"}
    n3   vector2                     float2   componentsin<-n12 componentslast<-n13
    n4   vector4                     float4   componentsin<-n3 componentslast<-n7
    n5   const_float1                float1   consts={"__constant__": "1"}
    n6   const_float1                float1   consts={"__constant__": "0"}
    n7   vector2                     float2   componentsin<-n15 componentslast<-n14
    n8   add                         float1   a<-n1 b<-n0
    n9   sub                         float1   a<-n6 b<-n0
    n10  add                         float1   a<-n2 b<-n0
    n11  sub                         float1   a<-n5 b<-n0
    n12  max                         float1   a<-n10 b<-n2
    n13  min                         float1   a<-n8 b<-n1
    n14  min                         float1   a<-n11 b<-n5
    n15  max                         float1   a<-n9 b<-n6
    out = n4
```

#### `[-1_1]_to_[0_1]` — [-1, 1] to [0,1]

- 形参：Input:float1=0
- 输出：`float1`（网表节点 n4）
- 规模：5 节点 / 4 边

```text
    n0   get_float1                  float1   consts={"__constant__": "Input"}
    n1   const_float1                float1   consts={"__constant__": "1"}
    n2   const_float1                float1   consts={"__constant__": "2"}
    n3   add                         float1   a<-n0 b<-n1
    n4   div                         float1   a<-n3 b<-n2
    out = n4
```

#### `[0,1]_to_[0,1,0]` — [0,1] to [0,1,0]

- 形参：input:float1=1
- 输出：`float1`（网表节点 n6）
- 描述：Moves centre of gradient to middle 0.5, expands range. Good for bi-directional gradient.
- 规模：7 节点 / 7 边

```text
    n0   get_float1                  float1   consts={"__constant__": "input"}
    n1   mul                         float1   a<-n0 b<-n2
    n2   const_float1                float1   consts={"__constant__": "2"}
    n3   sub                         float1   a<-n1 b<-n4
    n4   const_float1                float1   consts={"__constant__": "1"}
    n5   abs                         float1   a<-n3
    n6   sub                         float1   a<-n4 b<-n5
    out = n6
```

#### `[0_1]_to_[-1_1]` — [0, 1] to [-1, 1]

- 形参：Input:float1=0
- 输出：`float1`（网表节点 n4）
- 规模：5 节点 / 4 边

```text
    n0   get_float1                  float1   consts={"__constant__": "Input"}
    n1   const_float1                float1   consts={"__constant__": "1"}
    n2   const_float1                float1   consts={"__constant__": "2"}
    n3   mul                         float1   a<-n0 b<-n2
    n4   sub                         float1   a<-n3 b<-n1
    out = n4
```

#### `[0_1]_to_[1_0]` — [0, 1] to [1, 0]

- 形参：Input:float1=0
- 输出：`float1`（网表节点 n4）
- 规模：5 节点 / 4 边

```text
    n0   get_float1                  float1   consts={"__constant__": "Input"}
    n1   const_float1                float1   consts={"__constant__": "1"}
    n2   const_float1                float1   consts={"__constant__": "-1"}
    n3   mul                         float1   a<-n0 b<-n2
    n4   add                         float1   a<-n3 b<-n1
    out = n4
```

#### `[a,b]_to_[0,1]` — [a,b] to [0,1]

- 形参：X:float1=1, A:float1=1, B:float1=1
- 输出：`float1`（网表节点 n6）
- 描述：Returns position of input X, between min a, max b as a float between 0 and 1.Works as a reverse linear interpolation.
- 规模：9 节点 / 10 边

```text
    n0   get_float1                  float1   consts={"__constant__": "X"}
    n1   sub                         float1   a<-n5 b<-n2
    n2   get_float1                  float1   consts={"__constant__": "A"}
    n3   div                         float1   a<-n1 b<-n8
    n4   get_float1                  float1   consts={"__constant__": "B"}
    n5   max                         float1   a<-n0 b<-n2
    n6   min                         float1   a<-n7 b<-n3
    n7   const_float1                float1   consts={"__constant__": "1"}
    n8   sub                         float1   a<-n4 b<-n2
    out = n6
```

#### `negateFloat` — Negate Float1 (Deprecated)

- 形参：Input:float1=0
- 输出：`float1`（网表节点 n2）
- 规模：3 节点 / 2 边

```text
    n0   get_float1                  float1   consts={"__constant__": "Input"}
    n1   const_float1                float1   consts={"__constant__": "-1"}
    n2   mul                         float1   a<-n0 b<-n1
    out = n2
```

#### `sawtooth_wave` — Sawtooth wave

- 形参：x:float1=1
- 输出：`float1`（网表节点 n3）
- 描述：Repeats range to  [0,1], like texture coordinate tiling. Modulo adjusted to peak at 1, instead of back to 0.
- 规模：11 节点 / 13 边

```text
    n0   get_float1                  float1   consts={"__constant__": "x"}
    n1   mod                         float1   a<-n0 b<-n2
    n2   const_float1                float1   consts={"__constant__": "1"}
    n3   ifelse                      float1   condition<-n6 ifpath<-n8 elsepath<-n1
    n4   const_float1                float1   consts={"__constant__": "1"}
    n5   gt                          bool1    a<-n10 b<-n4
    n6   eq                          bool1    a<-n1 b<-n7
    n7   const_float1                float1   consts={"__constant__": "0"}
    n8   ifelse                      float1   condition<-n5 ifpath<-n9 elsepath<-n10
    n9   const_float1                float1   consts={"__constant__": "1"}
    n10  abs                         float1   a<-n0
    out = n3
```

#### `triangle_wave` — Triangle wave

- 形参：input:float1=1
- 输出：`float1`（网表节点 n5）
- 描述：repeats gradient range from 0 to 1 back to 0, giving a mirrored effect, like a sawtooth function, at every whole number.
- 规模：7 节点 / 6 边；调用 `oneminus`

```text
    n0   get_float1                  float1   consts={"__constant__": "input"}
    n1   mod                         float1   a<-n0 b<-n2
    n2   const_float1                float1   consts={"__constant__": "2"}
    n3   sub                         float1   a<-n1 b<-n4
    n4   const_float1                float1   consts={"__constant__": "1"}
    n5   instance                    float1   instance_of=oneminus                  x<-n6
    n6   abs                         float1   a<-n3
    out = n5
```

### Functions/typeConverters（2）

#### `booleanToFloat1` — Boolean to Float1

- 形参：Boolean:bool1=False
- 输出：`float1`（网表节点 n3）
- 描述：This function converts a boolean type value to a float1 value. If True returns 1.0, else 0.0
- 规模：4 节点 / 3 边

```text
    n0   get_bool                    bool1    consts={"__constant__": "Boolean"}
    n1   const_float1                float1   consts={"__constant__": "0"}
    n2   const_float1                float1   consts={"__constant__": "1"}
    n3   ifelse                      float1   condition<-n0 ifpath<-n2 elsepath<-n1
    out = n3
```

#### `turnsToDegrees` — Turns to degrees

- 形参：turns:float1=0
- 输出：`float1`（网表节点 n2）
- 规模：3 节点 / 2 边

```text
    n0   get_float1                  float1   consts={"__constant__": "turns"}
    n1   const_float1                float1   consts={"__constant__": "360"}
    n2   mul                         float1   a<-n0 b<-n1
    out = n2
```

### Functions/Cycles（1）

#### `Wave` — Wave

- 形参：Amplitude:float1=1, Frequency:float1=1, greaterThanZero:bool1=False
- 输出：`float1`（网表节点 n6）
- 描述：This function returns a Float1 value that oscillates over $time. It has Amplitude and Frequency inputs.
- 规模：9 节点 / 10 边

```text
    n0   get_float1                  float1   consts={"__constant__": "$time"}
    n1   sin                         float1   a<-n4
    n2   get_float1                  float1   consts={"__constant__": "Amplitude"}
    n3   get_float1                  float1   consts={"__constant__": "Frequency"}
    n4   mul                         float1   a<-n3 b<-n0
    n5   mul                         float1   a<-n2 b<-n1
    n6   ifelse                      float1   condition<-n8 ifpath<-n7 elsepath<-n5
    n7   add                         float1   a<-n2 b<-n5
    n8   get_bool                    bool1    consts={"__constant__": "greaterThanZero"}
    out = n6
```

## 5. 嵌套调用（库函数调用库函数，71 个）

| 调用者 | 调用 |
|---|---|
| `Directional_Offset` | `deg_to_rad`, `turnsToDegrees` |
| `Equality_Float3` | `Equality_Float2` |
| `Equality_Float4` | `Equality_Float2` |
| `HCLtoRGB` | `RGB_lightness_luma_rec601` |
| `NotEqual_Boolean` | `Equality_Boolean` |
| `NotEqual_Float2` | `Equality_Float2` |
| `NotEqual_Float3` | `Equality_Float3` |
| `NotEqual_Float4` | `Equality_Float4` |
| `RGB_hue_2_polar` | `Pi` |
| `RGB_saturation_HSI` | `RGB_lightness_average` |
| `RGB_saturation_HSL` | `RGB_chroma_hexagonal`, `RGB_lightness_bihexcone` |
| `RGB_saturation_HSV` | `RGB_chroma_hexagonal`, `RGB_lightness_hexcone` |
| `RGBtoHCL` | `RGB_chroma_hexagonal`, `RGB_hue_hexagonal`, `RGB_lightness_luma_rec601` |
| `RGBtoHSI` | `RGB_hue_2_polar`, `RGB_lightness_average`, `RGB_saturation_HSI` |
| `RGBtoHSL` | `average_float1` |
| `RGBtoHSV` | `RGB_hue_hexagonal`, `RGB_lightness_hexcone`, `RGB_saturation_HSV` |
| `RotationMatrix` | `deg_to_rad`, `turnsToDegrees` |
| `acescg_to_linear_srgb` | `merge_float3` |
| `acos` | `Pi`, `asin` |
| `carthesian_to_polar` | `2Pi`, `Pi`, `oneminus` |
| `deg_to_rad` | `Pi` |
| `directionToNormal` | `[-1_1]_to_[0_1]`, `deg_to_rad`, `turnsToDegrees` |
| `distance_vec2` | `length_vec2` |
| `distance_vec3` | `length_vec3` |
| `ease_in_circ` | `oneminus` |
| `ease_in_out_circ` | `oneminus` |
| `ease_in_out_cubic` | `oneminus` |
| `ease_in_out_quad` | `oneminus` |
| `ease_in_out_quart` | `oneminus` |
| `ease_in_out_quint` | `oneminus` |
| `ease_in_out_sine` | `Pi` |
| `ease_in_sine` | `Pi`, `oneminus` |
| `ease_out_circ` | `oneminus` |
| `ease_out_cubic` | `oneminus` |
| `ease_out_expo` | `oneminus` |
| `ease_out_quad` | `oneminus` |
| `ease_out_quart` | `oneminus` |
| `ease_out_quint` | `oneminus` |
| `ease_out_sine` | `Pi` |
| `fmod` | `frac` |
| `hsl_offset` | `HSLtoRGB`, `RGBtoHSL` |
| `linear_srgb_to_acescg` | `merge_float3` |
| `linear_to_sRGB_rgb` | `linear_to_sRGB_luminance` |
| `normal_distribution` | `2Pi` |
| `polar_to_carthesian` | `Pi` |
| `rotate_vec2` | `2Pi` |
| `sRGB_to_linear_rgb` | `sRGB_to_linear_luminance` |
| `saturate_float2` | `saturate` |
| `smoothstep` | `saturate` |
| `switch_float1_4_inputs` | `switch_float1_2_inputs` |
| `switch_float1_8_inputs` | `switch_float1_4_inputs` |
| `switch_float2_4_inputs` | `switch_float2_2_inputs` |
| `switch_float2_8_inputs` | `switch_float2_4_inputs` |
| `switch_float3_4_inputs` | `switch_float3_2_inputs` |
| `switch_float3_8_inputs` | `switch_float3_4_inputs` |
| `switch_float4_4_inputs` | `switch_float4_2_inputs` |
| `switch_float4_8_inputs` | `switch_float4_4_inputs` |
| `switch_integer1_4_inputs` | `switch_integer1_2_inputs` |
| `switch_integer1_8_inputs` | `switch_integer1_4_inputs` |
| `switch_integer2_4_inputs` | `switch_integer2_2_inputs` |
| `switch_integer2_8_inputs` | `switch_integer2_4_inputs` |
| `switch_integer3_4_inputs` | `switch_integer3_2_inputs` |
| `switch_integer3_8_inputs` | `switch_integer3_4_inputs` |
| `switch_integer4_4_inputs` | `switch_integer4_2_inputs` |
| `switch_integer4_8_inputs` | `switch_integer4_4_inputs` |
| `temperature_to_rgb` | `temperature_to_rgb_fit` |
| `temperature_to_rgb_fit` | `Pow` |
| `tonemap_ACES` | `merge_float3` |
| `tonemap_AgX` | `tonemap_AgX_approx`, `tonemap_AgX_look` |
| `triangle_wave` | `oneminus` |
| `truncate_float1_decimals` | `Pow` |

## 6. 调用要点与陷阱

- 实例节点的输入端口 id **就是目标函数的形参 id**（如 `fmod` 的 `a`/`b`、`clamp` 的 `input`/`min`/`max`）；输出端口恒为 `unique_filter_output`。
- 形参默认值可用但不显式：不接线时取形参默认值（见 §3 的「=默认」列）。
- 库函数是**多态**的：同一函数按调用方类型工作（`Function` 实例的输出 id 与类型必须回读，不要假设）。
- 库函数内部可能调用其它库函数（§5），递归展开后最终只由原子节点组成；全库用到的原子定义共 62 种，**没有任何库函数使用 While**。
- 文件里可能存在历史残留连接（如 §1 的 `input_v`）：以活动对象为准，不要照抄 XML 的边。

## 7. 重新生成 / 抽查任意函数

```
# 1) 在 Designer 进程内导出活动对象视图（读库包，不保存任何工程）
exec(open(r'<skill>\scripts\dump_library_functions.py', encoding='utf-8').read())
# 2) 独立解析发行包 XML 并与活动对象逐节点差分
python scripts/verify_library_functions.py parse-xml <SD>/resources/packages/functions.sbs --out xml.json
python scripts/verify_library_functions.py diff sdk.json xml.json --json diff.json --verbose
python scripts/verify_library_functions.py eval sdk.json xml.json     # 网表求值 vs 实测值
# 3) 重新渲染本台账
python scripts/render_library_catalog.py --sdk sdk.json --xml xml.json --diff diff.json --md <md> --json <json>
# 4) 只想查单个函数
python scripts/lookup_sd_function.py --library --name "^fmod$" --impl
```
