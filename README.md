# SD Pixel Processor Agent

[中文](#中文) · [English](#english)

## 中文

这是用于 **Substance 3D Designer Pixel Processor 与 Function Graph** 的 Agent Skill。它帮助分析、创建、迁移、修复、拆分、验证和排布函数图，尤其关注 Shader 迁移、`While` 循环、`Set → Sequence → Get` 执行顺序、函数接口以及大图布局。

它不是 Substance Painter 工具，也不替代 Designer 的实际运行验证。仓库中的版本相关结论与项目实测记录有明确适用范围；换用其他 Designer 版本或项目时，应按 [SKILL.md](SKILL.md) 和对应参考资料重新探测，不能把既有测量结果当成通用 API 保证。

### 当前更新：2026-10-27.2

运行时基线仍为 `2.5.0`；`BEHAVIOR_REVISION` 单独记录行为与工具修订。本次增加大型项目分层推进、多 PP/LUT 数据契约、原 Skill 约束下的局部布局优化，以及用户选择的临时画面组装路径。

操作加固包括完整图内容快照、函数验证与产物身份绑定、依赖变更失效、持久化操作日志与写锁、帧提交检查、单包交付证据检查和安装失败恢复。入口文档改为按需加载详细规则。

**兼容性变化：** `require_verified_dependencies` 不再接受仅含函数名的集合。请按 [操作与恢复指南](references/OPERATIONAL_RECOVERY.md) 使用 `EvidenceRegistry`、当前身份映射和绑定的数值记录。安装脚本需要 Python；不在 PATH 时设置 `SD_PIXEL_AGENT_PYTHON`。

本轮安装版通过 98 项测试；发布版另增加 Git 元数据排除回归测试。原生只读检查覆盖 scalar example 的 5 个资源和大型示例包的 117 个资源。夹具中的 FTP 原生输出为已核对哈希的历史数据，不代表本轮重新渲染。检查器不等于自动布局器、崩溃恢复看门狗或宿主跨帧调度器。

### 安装与使用

把本仓库克隆到所用 Agent 的 skills 目录，目录名保持为 `sd-pixelprocessor-agent`。例如 Codex 可放在 `~/.codex/skills/sd-pixelprocessor-agent`；本项目的 Harness 环境使用 `~/.dsh/skills/sd-pixelprocessor-agent`。如果目标目录已存在，先自行确认和备份，避免覆盖本地修改。

```sh
git clone https://github.com/Ftirl/sd-pixelprocessor-agent.git /path/to/skills/sd-pixelprocessor-agent
```

随后可在对话中调用 `$sd-pixelprocessor-agent`，并描述具体的 Designer 图、目标与允许的修改范围。也可以从本仓库运行 `scripts/install.ps1`（Windows）或 `scripts/install.sh`（macOS/Linux）；安装脚本会备份并替换已有目标目录，运行前请确认目标位置。

### 仓库结构与验证

- [SKILL.md](SKILL.md)：入口、适用范围和执行约束。
- `references/`：详细规范、兼容性、原生探测和真实项目复测门槛。
- `scripts/`、`core/`：探测、布局、校验与辅助实现。
- `evals/`：行为测试；`VERSION` 与 `MANIFEST.json`：发布版本和文件哈希。

发布前在仓库根目录运行 `python scripts/eval_release.py`。部分原生探测还要求在匹配版本的 Substance 3D Designer 会话中运行；通过离线测试不代表目标项目已通过 cook 或图结构复核。仓库未附带用户的 `.sbs` 项目文件。

## English

This Agent Skill is for **Substance 3D Designer Pixel Processor and Function Graphs**. It supports analysis, creation, shader migration, repair, function extraction, validation, and layout, with particular attention to `While` loops, `Set → Sequence → Get` execution order, function interfaces, and large graphs.

It is not a Substance Painter tool or a substitute for validation in Designer. Version-specific findings and real-project retests in this repository have defined evidence limits. For a different Designer version or project, follow [SKILL.md](SKILL.md) and the relevant references to re-probe behavior; do not treat earlier measurements as universal API guarantees.

### Current update: 2026-10-27.2

The runtime baseline remains `2.5.0`; `BEHAVIOR_REVISION` identifies policy and tooling changes separately. This update adds visible layer milestones, multi-PP/LUT contracts, local layout refinement under the existing Skill rules, and an explicitly user-selected provisional visual assembly path.

Operational hardening includes graph-content snapshots, artifact-bound function evidence, dependency invalidation, durable operation journals and writer locks, frame-commit checks, portable-package evidence checks, and installation rollback. Detailed rules now load on demand.

**Migration:** `require_verified_dependencies` no longer accepts name-only sets. Use `EvidenceRegistry`, fresh identity mappings and bound numeric records as documented in [Operational recovery](references/OPERATIONAL_RECOVERY.md). Installers require Python; set `SD_PIXEL_AGENT_PYTHON` when it is not on PATH.

The installed revision passed 98 tests; this repository additionally tests exclusion of Git metadata. Native read-only checks covered 5 scalar example resources and 117 large example resources. Bundled FTP native outputs are hash-verified historical fixtures, not fresh renders. These guards are not an automatic layout optimizer, crash watchdog, or host frame scheduler.

### Install and use

Clone this repository into your agent's skills directory, keeping the folder name `sd-pixelprocessor-agent`. For example, Codex can use `~/.codex/skills/sd-pixelprocessor-agent`; this project's Harness setup uses `~/.dsh/skills/sd-pixelprocessor-agent`. If the destination already exists, inspect and back it up before replacing local changes.

```sh
git clone https://github.com/Ftirl/sd-pixelprocessor-agent.git /path/to/skills/sd-pixelprocessor-agent
```

Invoke `$sd-pixelprocessor-agent` in a conversation and provide the specific Designer graph, goal, and authorized edit scope. Alternatively, run `scripts/install.ps1` on Windows or `scripts/install.sh` on macOS/Linux from this checkout. These installers back up and replace an existing destination; check the target first.

### Repository and validation

- [SKILL.md](SKILL.md): entry point, scope, and execution constraints.
- `references/`: specification, compatibility, native probes, and real-project retest gates.
- `scripts/` and `core/`: probes, layout checks, validators, and supporting implementation.
- `evals/`: behavioral tests; `VERSION` and `MANIFEST.json`: release version and file hashes.

Run `python scripts/eval_release.py` from the repository root before a release. Some native probes must also run inside a matching Substance 3D Designer session. Passing offline tests does not establish that a target project has passed its cook or graph-structure checks. User `.sbs` project files are not included.

## Public example privacy / 公开示例脱敏

Project names, private discussion links, original local paths, source-file fingerprints and node identifiers have been removed or replaced with anonymous examples. Historical numerical results remain scoped evidence, not newly executed native checks. This applies to the current file tree; it does not erase previously published Git history.

案例名称、本地来源路径、私人讨论链接、原始文件指纹及节点标识已泛化。保留的数值为有限范围的历史验证证据，不表示重新运行原生测试。本说明仅适用于当前文件树，不代表旧提交历史已清除。
