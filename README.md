# ai4gd

**A small, host-neutral toolkit for AI-assisted Godot development.**

ai4gd 将游戏需求、按需技能、真实检查和经验回流连接起来。核心是 Python 标准库与 Markdown，
可以由 Claude Code、Codex、OpenCode、WorkBuddy、自建智能体或人直接调用；不依赖某个模型服务。

这是独立实现的 **2.0 MIT 版本**。旧本地框架的代码、角色、模板、文档镜像及 Git 历史未打包，
许可来源与边界见 [NOTICE](NOTICE.md)。

## Start

需要 Python 3.10+；验证游戏还需要单独安装 Godot。先克隆源码，不必安装依赖或后台服务：

```bash
git clone https://github.com/YuekuiBai/ai4gd.git
cd ai4gd
python -m ai4gd --help
python -m ai4gd init /path/to/game
python -m ai4gd check /path/to/game --godot /path/to/godot
```

让编码智能体读取 [SKILL.md](SKILL.md)。可选地生成一个指向源码的技能发现入口：

```bash
python -m ai4gd register --dest /path/to/host/skills
```

不会复制工具到游戏，也不会自动安装插件、注册 MCP、提交 Git 或上传游戏。
所有命令输出 JSON，成功返回 0，检查失败返回 1，输入或状态不满足返回 2。
建议直接在源码目录运行；命令行包安装不会自动携带外部技能文件，使用安装后的命令时以
`ai4gd --root /path/to/source ...` 指向完整源码。

## A task with evidence

先把验收条件写成 JSON 检查计划。命令使用 argv 数组，避免跨平台 shell 引号差异。
下面演示一个场景回归；`PYTHON` 和 `ROOT` 请替换为实际可执行文件与源码绝对路径：

```json
{
  "checks": [{
    "id": "scene-regression",
    "argv": ["PYTHON", "ROOT/examples/check_scene.py", "/path/to/game", "/path/to/godot"],
    "timeout": 90,
    "expect": "SCENE_REGRESSION_COMPLETE"
  }],
  "review_required": false
}
```

```bash
python -m ai4gd task /path/to/game input-fix begin --goal "Restore mouse capture after closing the menu" --focus input --plan /path/to/plan.json
# Read /path/to/game/.ai4gd/tasks/input-fix/context.md completely.
# After code edits, refresh, read it again, and acknowledge the returned digest.
python -m ai4gd task /path/to/game input-fix refresh
python -m ai4gd task /path/to/game input-fix ack --sha256 THE_RETURNED_SHA256
python -m ai4gd task /path/to/game input-fix run
python -m ai4gd task /path/to/game input-fix close
```

输入变动会使旧检查失效；关闭任务要求日志未被修改。失败保留全部尝试，连续两次失败后需要
研究记录和不同的下一步。界面体验另需真实交互审查，headless 通过不代表视觉合格。

示例只证明场景加载。项目应增加自己的输入、数值、存档或机制断言；不能把加载成功写成玩法成功。

## Three loops

| Loop | Flow | Completion evidence |
|---|---|---|
| Game development | Goal → selected context → implement → run → review → close | Current checks and relevant interaction review |
| Framework evolution | Observe → reproduce → bounded proposal → source change → gates → accept/rollback | Source snapshots, actual tests and a game regression |
| Game release | Export → launch artifact → validate packaging → authorized publishing → feedback | Exported build and platform-specific release evidence |

详细操作：[开发与测试](references/development.md)、[自我进化](references/evolution.md)、
[知识与 Qdrant](references/knowledge.md)、[发行闭环](references/release.md)、
[设计与迁移](references/design.md)、[贡献说明](CONTRIBUTING.md)。

## Local and cloud knowledge

```bash
python -m ai4gd knowledge learn --godot-version 4.7
python -m ai4gd knowledge learn --godot-version 4.7 --online --limit 2
python -m ai4gd knowledge vector-status --target local
```

读取网络必须显式 `--online`；变化只进入待审核状态。Qdrant 和嵌入库是可选依赖，
没有它们仍能开发、检查游戏和维护任务。云端密钥只从环境变量读取，不写进项目或报告。
首次模型下载也需要显式选择，命令见 [知识接口](references/knowledge.md)。

## Verify and contribute

```bash
python -m pip install "pytest>=8,<9"
python -m ai4gd audit --release
python -m pytest tests -q
```

设置 `GODOT_BIN` 后测试会额外运行真实 Godot 回归。GitHub 工作流覆盖 Windows/Linux 和
Python 3.10/3.12 的离线检查；工作流存在不代表云端已经执行成功，以实际运行结果为准。

MIT © 2026 YuekuiBai and contributors. Third-party runtime products and fetched
knowledge retain their own terms; they are not included in this source license.
