# 第四批后四套：B4c独立视觉契约

继续按creative-direction先创作、后模板。音效专项已恢复为显式事件原型，旧计划仍不自动加音效，不能因增加四套视觉实现就声称已有完整专业音效。当前为有差距的授权替代校准版，用户逐套审美待验；原参考中未实现的分割/描边明确不支持。

|目标 / 入口|独立设计|核心限制|
|---|---|---|
|kp-30 秀丽粉 / `ref_elegantpink_v1`|白字玫红标题条；黑字白背板+玫红重点，小英文独立白签；最多四条玫红短句；独立场景词列表|原人物身份牌、英文推广行、旋转取景框与逐字光标未实现|
|kp-34 爆款促销 / `ref_promo_v1`|默认不强加顶部标题；低位紧凑红白多边字幕、字内点纹；原创红金喇叭/购物车|原创平面图标非原三维素材；原逐字变化/爱心粒子未完整复原|
|kp-36 专业金棕 / `ref_browngold_v1`|白主标题金副题、厚棕投影、金白正文；书法金姓名配细金线与衬线资料|人物抠像白边、替换纸背景、上部大字接管未实现，禁止框/圆窗冒充轮廓|
|kp-43 活泼亮粉 / `ref_hotpink_v1`|亮粉粗标题黑边与断角框；白粉正文、弧形短词、爱心和边缘漫画线|未实现人物黄描边跟踪、全帧流动粒子；边缘线需显式安全框|

## 输入与状态

四套均为`scene_time_space: output`，phrase必须有唯一id。正文与保留词流一致；每个短语/图标/清单独立start/end。使用`runs`的body/keyword角色，不允许任意fill、pointer或旧notes/highlights/title_surface混入。

- Elegantpink：默认`mode: bilingual`，每组单句，必须为该句提供独立英文翻译；`mode: ribbon`每组最多四句，白字玫红底条，交替左右留屏。组内不混两种模式；ribbon不能带被丢弃的英文。四句用专用较小字级，不靠缩到无法阅读来过安全检查。
- Promo：每组单句。参考无固定顶部标题，素材无标题需求时省略`scene_title_lines`并将title置空；显式添加语义标题属适配，不说是参考原有。
- Browngold：每组最多两句；关键字金色、连接文字白色，投影与标题统一。
- Hotpink：每组单句，`normal`白粉混合、`display`粉色放大、`arc`逐字旋转和弧形位移；arc最多8字且受实际宽度约束，超长应重组短句，不截字。

秀丽粉的`scene_translations`沿用独立译文时钟：phrase_id/source_text准确匹配、language=en、start/end在原中文句内；review_status与reviewer必填，草稿仅用于preview，输出英文单独SRT。不把译文混进中文ASR。

## 语义组件

`scene_tags`：text摘自当前phrase，phrase_id、reason、start/end（在该句内）、side。仅横排：
- elegantpink可`icon: heart_cursor`（原创心形光标）；
- promo可`icon: megaphone`或`cart`；购物车仅在真正购物/交易语义时用；
- hotpink可`icon: heart`；
- browngold无图形图标，不把其他模板素材硬拼进来。

`scene_callouts`只用于elegantpink：最多三个槽位slot=0/1/2，同侧同槽时段不可重叠；text≤6字、摘原phrase、进入时仍在该句内，可独立留到句后。默认侧边位置，不合适时可提供归一化x/y（两者一起），仍须完整通过人物保护区、字幕与边界碰撞检查。Codex主动布局，不要求用户填坐标。

`scene_identity`只用于browngold：最多一张，name≤4字、detail≤16字；start/end、显式归一化x/y、source/reviewer/review_status=reviewed/reason。渲染器只能核验字段，不能证明身份真实；没有可靠资料时省略，不从模板参考照搬名字。可选`detail_lines`明确分为一至两行，拼接须与detail完全一致，避免机械截成单字尾行。书法角色用于姓名，衬线辅助角色用于资料；完整字形检查包含两者。

`scene_accents`只用于hotpink：`kind: rays|hearts`，start/end、reason、归一化x/y/width/height，宽高各≤.35；rays可side=left/right。它是独立有界图层，不是自动人物避让；仍走所有安全/碰撞规则，不能以装饰角色豁免。旧模板传入该字段会拒绝，而不是静默无效。

## 画布与人物

Elegantpink可选原有circle能力，以`background: '#FFFFFF'`匹配白底；显式center/radius/reason，圆窗不是默认真实人物处理。Browngold可选vignette。不支持subject_outline/背景替换，输入应报错。不要为了放清单/漫画线缩小画窗，也不为了避隐私改变必要构图；尾部延长时继承隐私层到真实编码终点。

## 交付口径

每套有固定确认中文的3:4主样与9:16异文案样；专业金棕另做完整集成；合成组件视频展示四句/白底圆窗、图标、假身份和漫画短词，不冒充真人作品。所有字体是本地有许可的替代资源。字形、布局、解码、AV、旧版回归与安装哈希检查不能代替正常速度听审或用户审美。
