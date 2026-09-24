# 第四批前四套：组件化但不套同一种布局

先完成creative-direction。用户暂后逐套审美验证，不等于机器安全检查可以延期，不等于正式接受效果。以下均显式template_delivery=preview，准确数量以台账为准。

|目标 / variant|整套设计|
|---|---|
|tpl-golden-sparkle 黄色闪亮 / tpl-golden-sparkle|金黄奶油渐变、棕金挤出边、大标题下纸带；白黄混排，短词指示手、可选灯泡/斜竖排词标|
|tpl-vivid-green 吸睛绿 / tpl-vivid-green|白粗字深底标题、绿底黑副标题；compact小双语与display绿白宋体大字；双箭头概念清单|
|tpl-business-tech 商务科技 / tpl-business-tech|银白金属斜体标题，多层斜切科技轨道持续显示；独立蓝白重点字；来源核验的竖向身份卡|
|tpl-science-highlight 醒目科普 / tpl-science-highlight|红蓝双行斜标题，白短句与paper黄红纸条态；短词指示手；可选蓝青小身份卡|

## 主字幕与状态

沿用输出时钟scene_captions；本批每个phrase都需要唯一id。正文runs只含body/keyword角色，禁止填任意fill/color。shine/tech/science每组一个短语，green的display可两个错位短语；compact每组只一个短语。

- green：`mode:compact`必须有按phrase_id/source_text绑定的独立英文译文；`mode:display`不显示英文且拒收该短语译文，防止默默丢译文。所有compact语义译文单独审查，renderer不生成译文。
- science：`mode:normal`白字；`mode:paper`浅锯齿纸条、黄正文红重点。当前不是自动逐字变色，每次变化须明确编排，保留主词流。
- shine/science可指定`pointer:"短词"`：必须在本句某一个run中唯一完整出现，手指放在该短词下方；模棱两可则阻止，不随便指第一个字。精确手指几何由代码原创绘制，不依赖Emoji缺字或付费生图。
- tech：字幕轨道在整条输出持续显示，正文切换不导致底条闪灭。底条/文字是经校验的父子关系，正文包围框必须在轨道内；仅这一包含关系可豁免碰撞，其它文字及人物保护区依然检查。

## 独立词标和概念清单

scene_tags：保留text/start/end/side/reason，新增必填phrase_id；须摘自该短语且时钟完整落在其内。shine允许`icon:bulb`和`orientation:vertical`（最多4字），默认水平；其余套不能滥用。灯泡是原创扁平图形，不冒充参考立体素材。

green可用scene_callouts：`{phrase_id,text,start,end,slot:0|1,side:'left'|'right',reason}`。text最多6字、须摘原句；在源短语仍显示时进入，可延长到其结束后以保留概念。相同槽不允许时间重叠；左右锚点仍受人脸/手势保护区约束，不自动跟踪人物。使用前先判定保留概念是否有必要，不仅为了填满两槽。

## 身份卡：先核验再显示

仅tech/science允许scene_identity数组，最多一张：

```json
{"name":"已核实姓名","detail":"已核实短身份","start":0,"end":2.5,"x":0.06,"y":0.3,"review_status":"reviewed","source":"实际资料来源","reviewer":"真实复核者与范围","reason":"介绍人物的内容依据及构图检查"}
```

name最多4字、detail最多12字；示例占位文字不能当真资料直接上片。x/y是归一化左上位置，必须为当前素材选安全空位。tech为双列竖向布局，science为蓝青斜切小卡。字段检查只确认提供了来源信息，**不证明人物履历是真的**，Codex仍需实质核验；无可靠资料就不填，不照搬参考的姓名/头衔。身份卡文字进入字形预检与包围框检查。

## 能力与差距

支持3:4/9:16预检；不是任意构图保证。明亮/深色背景都需看编码帧。所有文字限制最小72%缩放，过长重新分句不删字。商务科技得意黑不能保证所有繁体字，缺字停止；不得静默换字体。

字面渐变、指示手、灯泡、箭头、身份卡和科技轨道为原创近似；官方逐字显现、材质扫光、闪光粒子没有恢复。不得把合成组件测试当成用户原片真人身份或实拍交付。镜头按独立camera_recipe加语义节点编排，音效/转场不是模板强制项。保留教学式柔边打码与构图规则，不为模板/脱敏随意套窗或裁人。
