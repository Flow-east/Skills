# 第五批前四套：独立样式与说明图

四套入口：`tpl-orange-line` 暖线映橙、`tpl-colorful-pop` 明快彩彩、`tpl-antique-mint` 古雅水绿、`tpl-red-torn-paper` 撕纸红。均为明确选择的校准预览，不宣称原引擎或官方字体。音效专项已恢复为显式事件原型，旧计划仍不自动加音效，不能以原声存在声称配好音效。

## 创作先于样式

先按creative-direction.md确定内容结构、开场、表现、音效/转场判断和隐私，再选模板。新素材必须重做保护区和必要动作检查，不使用收缩/套窗/裁人来给装饰腾位或减少打码。原视频没有相关事实时，不照抄参考里的价格、医疗、房产、购买或身份内容。

## 场景时钟与布局

`scene_time_space: output`，所有`scene_captions[].phrases[]`须有唯一非空`id`，每组最多两句，各句独立入场/退场，不因后一行出现而重播第一行。`runs`只用`body/keyword`角色，禁止私改fill、pointer或color。句子和确认词流一致，不把标注混进ASR。

- **orangeline**：`mode: normal/display/impact`。小衬线、放大衬线、橙色强调；粗标题橙色斜下衬。两句时左右错位，独立橙下衬词标。
- **colorful**：`normal/display/impact`。细紫边斜衬线标题；正文白色、黄色展示、红色强调。斜体用字形剪切变换，不用整行倾斜充当斜体。两句错位。
- **mint**：`normal/card`。绿字或绿圆底黑字。可给短语指定`underline: "原句中的片段"`，按实际字体进位计算下划线位置，片段不在原句则拒绝。最多两行中置独立留屏。
- **tornred**：`normal/paper/impact`。小字半透窄底、逐字原创不规则白纸黑字、红色强调。纸片轮廓由文本确定，帧间不乱跳；各字纸片共享基线，不让“一”或标点变成半空中的短纸条。说明图见下。

`scene_tags`：必须包含`phrase_id/text/start/end/reason`，text是对应原句片段，时间在原句可见期内；`side`为left/right，不支持任意icon或竖排。词标是否使用由语义决定，不每句固定加。

## 明快彩彩：独立特征标签

仅colorful接受`scene_callouts`，每项`phrase_id/text/start/end/slot/side/reason`。text为已说原话片段（1–9字符），在对应句可见时入场，可跨句保留。slot为0或1，同侧同槽不能重叠；可设置归一化`x/y`一对坐标，经边界/碰撞/人物保护检查，不能只给其中一个。适合真实已讲的产品特征或概念，不伪造推荐语。

## 撕纸红：受约束的说明图片卡

仅tornred接受`scene_media`。不是自动搜图工具，不会去参考视频截取图片。每项示例：

```json
{
  "phrase_id": "phrase-2-0",
  "start": 3.2,
  "end": 4.8,
  "path": "/absolute/path/to/reviewed-image.png",
  "sha256": "actual_sha256_of_file",
  "x": 0.20,
  "y": 0.35,
  "width": 0.60,
  "height": 0.30,
  "fit": "contain",
  "source": "实际来源，不是占位文案",
  "rights": "用户供图或已确认可用的许可依据",
  "review_status": "reviewed",
  "reviewer": "实际复核者",
  "privacy_status": "reviewed",
  "privacy_review": "已检查/处理画面中的名字、账号、合同等，记录具体判断",
  "reason": "此图如何解释这句原话"
}
```

- 时间必须位于锚定短语可见区间。坐标归一化，width≤.75、height≤.6；完整包络仍须在安全区且不遮挡保护区或碰撞其他图层。
- 仅单帧PNG/JPEG/WebP，≤16MP，绝对本地路径，文件哈希必须匹配。先按EXIF旋转，再完整包含在圆角卡中；不支持cover裁切或动画图。
- 字段本身不是事实核验。创作者必须实际确认来源、使用权和隐私，不能机械填“reviewed”。检测到敏感内容先输出经过遮挡的图片并重新哈希，不能拿卡片圆角或部分裁切代替打码。
- 外部图片的来源及哈希写入font_qa.scene_media_assets，渲染前加载为固定快照；复用时检查哈希。此记录是资产溯源，不等于内容正确或隐私自动检查。
- 说明图内若含文字，普通字体覆盖检查不验证位图文字。需另外目检/OCR核验，无合适图宁可不加。仅实拍不宜放图时用独立合成测试展示能力，不能声称实拍已验证了该构图。

## 参考差距与验收

这四套具有独立契约及渲染分支，但字形为授权替代。逐字显字/揭纸、参考纹理、柔边窗口和背景虚化尚未还原，具体见契约limitations。人物主体不因追求参考布局而被遮住。没有用户逐套确认及常速视听审查，不计正式验收。
