# 口播剪辑（koubo-editing）

面向中文口播视频的**内容判断 + 视听设计 + 实际成片**技能。不是某个剪辑产品的官方插件，也不保证复刻其原始模板。

## 能做什么

- 本地转写/逐词时间码，对照原声做语义精剪，记录保留、删除与不确定内容；不擅自改写原话、截断句尾。
- 先设计开头钩子、内容结构、镜头节奏、是否需要音效/转场/隐私遮挡，再选择适配的完整模板。
- 在布局安全区内编排标题、字幕、关键词、贴纸和镜头运动；按语义选用内置音效，而非逐句加声。
- 输出有声音的 MP4、剪辑计划、字幕、创作方案和 QA 记录，区分技术通过与人工内容/审美验收。

内置 **54 套参考样本驱动的校准模板**，供预览和逐套审美核对；当前并非 54 套都已获用户最终视觉验收。模板研究借鉴过开拍提供的示例，但字体和动画为原创实现或附带授权的替代素材，**不包含官方模板工程、预览视频或官方音效**。内置 74 种已记录来源与 CC0 状态的常用音效；具体选用仍需结合语义和试听。

## 安装与使用

```bash
# 从仓库根目录执行
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R koubo-editing "${CODEX_HOME:-$HOME/.codex}/skills/koubo-editing"
```

对 Agent 说“帮我剪这条口播视频”或显式使用 `$koubo-editing`。传入可读取的本地视频；转写模型、素材以及用户视频**不随技能打包**。缺模型时按 `references/runtime.md` 选择本机后端，不会自动上传音频到第三方。贴纸生图是可选步骤；Nexora 仅在单独安装 `nexora-imagegen` 且得到相应外发和额度授权后使用。

需要 Python 3、Pillow、NumPy、FFmpeg/ffprobe；转写后端（MLX Whisper / faster-whisper / Whisper）按设备和模型另行安装。具体输入格式和命令见 `SKILL.md`、`references/runtime.md` 和 `references/plan-format.md`。

## 验证

```bash
python3 -m unittest discover -s koubo-editing/tests -v
python3 koubo-editing/scripts/template_library.py validate
python3 koubo-editing/tests/smoke_test.py
```

测试通过仅验证实现边界，不能代替具体视频的听校、隐私检查或用户审美验收。

## 素材与许可

技能原创代码及文档遵循仓库 MIT 许可；`assets/fonts` 下字体各遵循随附的 SIL OFL 文件和 `manifest.json`，`assets/sfx` 下素材按照 `catalog.json` 记录的 CC0 1.0 来源提供。详见 [第三方素材说明](THIRD_PARTY_NOTICES.md)。发布包不包含用户原始视频、转写、账号凭据或本机模型。
