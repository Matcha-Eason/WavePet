# WavePet

WavePet 是一个 Codex 桌宠状态追踪插件。它把 Codex 的实时工作事件转换成桌宠可以消费的状态 JSON，用来反映用户可感知的等待体验。

Codex 市场英文说明见 [`plugins/wavepet/README.md`](plugins/wavepet/README.md)。

## 能力

- 在线跟踪：根据 assistant token、thinking token、工具事件、编辑、测试、错误反馈和静默等待持续更新状态。
- 轻量预测：根据当前输出负载、思考负载、环境反馈压力、错误压力和状态平滑，判断本轮是否正在进入长输出或红温调试。
- 桌宠状态：读题理解、稳定工作、深度输出、红温调试、收束。
- 渲染提示：输出 `motion`、`tint`、`scale`、`badge`、`bubble`、`cadence_ms`，兼容多状态动画宠物和单图宠物。
- 低依赖运行：核心状态机是无第三方依赖的 Python 脚本，可以嵌入其他桌宠 renderer。

## 仓库结构

- `plugins/wavepet/`：Codex 插件根目录。
- `.agents/plugins/marketplace.json`：repo-local marketplace 入口。
- `.github/workflows/validate-wavepet.yml`：CI 校验。

## 快速测试

```bash
python3 plugins/wavepet/scripts/pet_state_engine.py --demo
python3 -m unittest discover -s plugins/wavepet/tests -v
```

## 导入方式

1. 使用仓库里的 `.agents/plugins/marketplace.json` 作为 repo-local marketplace。
2. 复制 `plugins/wavepet/` 作为本地 Codex 插件。
3. 复制 `plugins/wavepet/skills/wavepet/` 作为独立 Codex skill。
4. 将 `plugins/wavepet/scripts/pet_state_engine.py` vendor 到自己的桌宠应用。

## 与 TokenWave 的关系

TokenWave 是科研仓库，整理对话状态预测、波形建模、实验设置和结果。WavePet 是应用仓库，把其中的当前等待体验状态估计转译成 Codex 桌宠插件。
