# 口播剪辑 · v0.2.1

[English](README.md) | **简体中文**

从口播内容分析到有声成片的剪辑技能：先判断结构和取舍，再设计字幕、镜头与声音，最后按选定模板渲染并验收。

## 功能

- 本地语音转写与逐词时间码；按语义处理重复、口误和停顿，保留完整句尾。
- 设计开头、内容顺序、镜头节奏、字幕层级、关键词贴纸、音效、转场与隐私遮挡。
- 按内容选择整套视觉模板：内置 54 套字幕与包装模板、74 种可选音效。贴纸插图可接入当前环境可用的生图工具，不绑定特定服务。
- 输出有声 MP4、剪辑计划、SRT 字幕、创作方案和 QA 记录。

## 安装

从仓库根目录复制技能目录：

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R koubo-editing "${CODEX_HOME:-$HOME/.codex}/skills/koubo-editing"
```

也可将本目录地址交给兼容 Agent 安装，或使用 `npx skills add Flow-east/Skills --skill koubo-editing`。

## 使用

提供可读取的口播视频，并说“帮我剪这条口播”或使用 `$koubo-editing`。技能先复核原话与内容结构，再制作创作方案和成片；只要求分析时不会自动渲染。生图、外部服务和付费调用须另行具备可用工具与授权。

快速预览及精细计划分别见 [`references/quickstart.md`](references/quickstart.md)、[`references/plan-format.md`](references/plan-format.md)。选择某套模板时查看 [`references/template-library.md`](references/template-library.md) 中的能力与状态。

## 环境与验证

需要 Python 3、Pillow、NumPy、FFmpeg/ffprobe；本地转写后端和模型按设备另行配置，详见 [`references/runtime.md`](references/runtime.md)。

```bash
python3 -m unittest discover -s koubo-editing/tests -v
python3 koubo-editing/scripts/template_library.py validate
python3 koubo-editing/tests/smoke_test.py
```

## 许可

原创代码和文档遵循仓库 MIT 许可；随附字体与音效遵循其各自的授权与来源记录，详见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。
