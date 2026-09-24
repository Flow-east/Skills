# 运行与故障定位

所有脚本使用已加载技能目录的绝对路径。Python 3 + Pillow + NumPy；FFmpeg/ffprobe 必需。建议先检测本机已有依赖，缺失再在经授权的局部环境安装，不修改全局默认配置。

```bash
python3 <SKILL_DIR>/scripts/transcribe_audio.py --doctor
python3 <SKILL_DIR>/scripts/transcribe_audio.py /absolute/video.mp4 \
  --backend mlx --model /absolute/local-mlx-model --out-dir /absolute/project/asr-v1
python3 <SKILL_DIR>/scripts/make_cut_plan.py /absolute/project/asr-v1/raw.json \
  --decisions /absolute/project/editorial.json --out /absolute/project/plan.json
python3 <SKILL_DIR>/scripts/render_template.py /absolute/project/plan.json \
  --out-dir /absolute/project/render-v1
python3 <SKILL_DIR>/scripts/build_dynamic_ass.py /absolute/project/plan.json \
  --out /absolute/project/captions.ass
```

默认不下载模型，不把语音传第三方。`--allow-download` 仅在已得到所需授权、确定目标模型后使用。三个后端显式选择：mlx 使用 MLX 模型目录，faster 使用 CTranslate2 模型目录，whisper 使用 .pt 文件；不能在失败后把一种模型目录静默传给另一种后端。实际后端、实际模型、音频摘要和错误都记入 status.json。

Mac 沙箱可能限制 Metal；出现 `No Metal device available`，应申请本地执行权限后再运行同一模型，不能据此断言整台电脑没 GPU。无权限时再说明替代后端，不能隐藏故障原因。

输出：`compiled_plan.json`（帧量化映射）、`base.mp4`（裁剪音画）、`visual.mp4`（无声中间画面，不交付）、`sound.wav`、`final.mp4`（交付预览）、`captions.srt`、抽帧、`qa.json`、日志。`rendered_awaiting_review` 是渲染成功等待内容/审美校对，不是最终通过。
