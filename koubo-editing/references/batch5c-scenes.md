# 第五批后四套：独立校准模板

四套均为preview校准版，非正式审美验收或官方1:1。先完成creative-brief，再选对应明确variant；音效专项已恢复为显式事件原型，旧计划仍不自动加音效，不自动加BGM/音效。

|目标|variant|状态/字体/版式|
|---|---|---|
|tpl-minimal-ins 极简Ins风|tpl-minimal-ins|Noto Sans重标题与单字斜棕贴；正常正文棕底阶梯边、蓝色小偏移；奶油蓝边词签；仅normal单句|
|tpl-vintage-classic 古典怀旧|tpl-vintage-classic|Noto Serif浅金标题、细正文半透棕卡；brush用MaShanZheng重点短句；仅单句|
|tpl-translucent-yellow 半透简黄|tpl-translucent-yellow|MaShanZheng双行黄标题、Noto Sans深灰半透小字幕normal、橙白斜体大字display；最多双句错位|
|tpl-minimal-torn-edge 极简撕边|tpl-minimal-torn-edge|Noto Serif书名号标题、normal黄白混合字号双句、compact灰透原创撕边底条；最多双句|

`scene_captions`为输出时钟，各phrase有唯一非空id。runs仅body/keyword，原话逐字保持；normal、brush、display、compact仅对应上表模板，不跨模板乱用。未知颜色/指示线/逐字reveal字段拒绝，不静默伪造词时钟。Ins标题长度过长应分行，不能无限缩小。

`scene_tags`须包含`phrase_id,text,start,end,reason`；text引用该短语原词，时间完全处于锚点短语内，side可left/right。模板自动绘制自己的词签，不复用通用图标。不得用标签暗添观点、商品卖点。标签仍走人物保护区/字幕碰撞门槛；无贴纸必要可以不加。没有scene_callouts/身份卡/媒体卡/任意注释支持。

半透简黄、极简撕边可显式用`scene_canvas.kind=circle`，现有中心/半径/背景参数加可选`feather`（画面宽度0.002–0.04），必须`reason`与非空`composition_review`。这是固定遮罩，不会缩小源人物，也不自动跟踪；会遮掉圆外内容，因此不能默认套真人、不为打码省事使用、不裁必要人物/手势。示例只在无真人图表验证；实际素材必须重新复核构图。其它两套不支持circle。

参考限制：Ins约3秒、怀旧约4秒；原不规则字形、Hi/指物跟踪圈、怀旧打字机和模糊横移转场、逐字出现和上下分屏仍未复原。替代字体许可及哈希由现有font manifest记录；稳定原创阶梯/撕边不是官方贴纸资产。技术验证与常速視听、用户逐套审美是独立状态。
