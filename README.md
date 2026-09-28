# SD Pixel Processor Agent

[中文](#中文) · [English](#english)

## 中文

这是用于 **Substance 3D Designer Pixel Processor 与 Function Graph** 的 Agent Skill。它帮助分析、创建、迁移、修复、拆分、验证和排布函数图，尤其关注 Shader 迁移、`While` 循环、`Set → Sequence → Get` 执行顺序、函数接口以及大图布局。

它不是 Substance Painter 工具，也不替代 Designer 的实际运行验证。仓库中的版本相关结论与项目实测记录有明确适用范围；换用其他 Designer 版本或项目时，应按 [SKILL.md](SKILL.md) 和对应参考资料重新探测，不能把既有测量结果当成通用 API 保证。

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
