# 第六批前四套：简洁与萌趣分层模板

四套都是preview校准版，不是官方1:1或正式审美验收。先完成creative-brief，再选明确variant；音效专项已恢复为显式事件原型，旧计划仍不自动加音效。

|目标|variant|独立状态与版式|
|---|---|---|
|tpl-minimal-yellow-white 简洁黄白|tpl-minimal-yellow-white|Smiley Sans斜体两行标题；normal半透白窄条，display白/浅黄大字；单句；无符号词签|
|tpl-crayon-cute 彩蜡萌趣|tpl-crayon-cute|ZCOOL快乐体粉黄白三层描边；normal/display，最多双句错位；云团词签和原创星形|
|tpl-playful-pink-yellow QQ萌趣|tpl-playful-pink-yellow|Noto Sans黄粉双行粗标题；normal圆润厚边、hand手写短句；最多双句；原创双叹号|
|tpl-energy-cartoon 元气卡通|tpl-energy-cartoon|多色逐字漫画标题；normal白黑厚字、arc轻弧形重点句；最多双句；心/星/箭头/爆点原创几何|

`scene_captions`按输出时间，每个phrase必须有唯一id。runs仅body/keyword，原话逐字保持。模板只接受表中状态，不接受任意颜色、pointer、underline或伪造逐字reveal时间。长句需要语义分句，不能缩成小字塞入。

`scene_tags`必须含`phrase_id,text,start,end,reason`，文本引用活跃短语，时间完全位于该短语内，side为left/right。彩蜡、QQ、元气可选`symbol=star|heart|arrow|burst|exclaim`，且必须有`symbol_reason`；简洁黄白禁止符号。符号是本地原创几何，不加载参考商品贴纸。可选显式`x,y`必须成对且为0–1坐标，仍通过画布、字幕和人物保护区碰撞检查。

不得因参考出现母婴用品、服装、保险身份、点赞收藏分享，就向新视频添加这些事实或贴纸。是否使用符号由原口播语义和画面空间决定；没有必要可以完全不加。

元气卡通可显式使用轻`vignette`，但真实口播默认不做人像聚光；不能借暗角、圆窗或裁切规避隐私处理，也不能遮掉手势。其他三套不支持画布效果。

已知差距：参考人物圆窗/轮廓描边、实物插镜、商品图标、黑色椭圆彩点框、精准圆胖字、逐字弹入和聚光动画尚未复原。当前授权替代字体、原创云团/符号和稳定弧形字位不等于官方资源。技术验证、正常速度视听和用户逐套审美必须分开记录。
