# 选择整套模板

从 `assets/template_targets.json` 读取 54 套风格名称与 ID；运行 `python3 <SKILL_DIR>/scripts/template_library.py eligible` 查看可用项。按内容调性、画幅、字幕结构和镜头需求选择一套，不按编号轮换，不只更换字体颜色。用户指定模板时先核对适配，不暗换。

`assets/template_contracts/<模板ID>.json` 定义该套字体角色、字幕/词标位置、动效时序、镜头配方、画幅及限制。`assets/template_catalog.json` 是入口索引；渲染时契约规则优先。`limitations` 记录某些效果的边界；方案不能把不支持的人物抠像、自动跟踪或跨镜头转场写成已执行。

分层模板计划需显式 `template_delivery:"preview"`、`scene_time_space:"output"`、`scene_captions`；时间码和可选事件见 [计划格式](plan-format.md)。仅在有正式验收记录时使用 `template_delivery:"accepted"`。任何模板均需在当前原片检查安全区、字形、尾音与镜头，不拿别人的样片构图照搬。

字体来自 `assets/fonts/manifest.json`，缺字不得以方框或任意字体静默替代。内置模板不复制外部参考视频中的事实、人物履历、商品价格和贴纸素材；需要具体插图时执行 [贴纸规则](keyword-stickers.md)。
