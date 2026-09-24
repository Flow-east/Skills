# 可选音效索引（74 种）

以下素材随技能打包，供根据内容结构和画面动作选择；并非每条视频都要加音效。

原始 MP3 在 `assets/sfx/sources/`，渲染用 48 kHz 单声道 WAV 在 `assets/sfx/collection/`，`assets/sfx/catalog.json` 存逐项许可、作者、哈希与建议语境。此前六项 Kenney UI 素材仍为 `rejected_by_user`，禁止选择。公开剪映音效分类映射来自历史清单，不声称与当前客户端逐字相同。

选择顺序：语义节点与原声空间 → 画面动作/花字/转场是否有落点 → 模板强弱与内容语气 → 试听短样 → `sound_events`。不允许按句号机械插声；每个事件最多一声；长环境声不能盖口播。严格按照 `roles`、`styles` 和 `selection_guidance` 判断。

| ID | 分类 | 音效 | 时长 | 主要用途 | 强度 |
|---|---|---|---:|---|---|
| `sfx-tape-rewind` | 转场 | 模拟倒带 | 1.84s | transition, keyword | light |
| `sfx-record-scratch` | 转场 | 反差刮盘 | 1.88s | transition, keyword | light |
| `sfx-soft-wipe-in` | 转场 | 轻盈擦入 | 1.00s | transition, keyword | light |
| `sfx-whip-swish` | 转场 | 甩鞭 | 0.67s | transition, keyword | light |
| `sfx-handclap-accent` | 打斗 | 击掌打点 | 1.07s | keyword, contrast, sentence_end | heavy |
| `sfx-boxing-punch` | 打斗 | 拳击冲击 | 0.36s | keyword, contrast, sentence_end | heavy |
| `sfx-wooden-mallet-hit` | 打斗 | 木槌敲击 | 0.26s | keyword, contrast, sentence_end | heavy |
| `sfx-low-thud` | 打斗 | 低闷撞击 | 0.53s | keyword, contrast, sentence_end | heavy |
| `sfx-muted-metal-hit` | 打斗 | 金属闷击 | 0.92s | keyword, contrast, sentence_end | heavy |
| `sfx-metal-clang` | 打斗 | 金属敲响 | 2.15s | keyword, contrast, sentence_end | heavy |
| `sfx-glass-shatter` | 打斗 | 玻璃破碎 | 1.87s | keyword, contrast, sentence_end | heavy |
| `sfx-paper-tear` | 生活 | 纸张撕裂 | 2.72s | foley, keyword | light |
| `sfx-dish-shatter` | 打斗 | 陶瓷破碎 | 0.74s | keyword, contrast, sentence_end | heavy |
| `sfx-doorbell` | 生活 | 门铃提示 | 1.40s | foley, keyword | light |
| `sfx-telephone-ring` | 手机 | 电话铃声 | 3.74s | foley, keyword | light |
| `sfx-warning-alarm` | 悬疑 | 警报提醒 | 12.16s | ambience, contrast, transition | medium |
| `sfx-electronic-beep` | 游戏 | 电子哔声 | 0.22s | keyword, sentence_end, sticker | light |
| `sfx-cash-register-success` | 游戏 | 收银成功 | 2.20s | keyword, sentence_end, sticker | light |
| `sfx-coins-jingle` | 游戏 | 多枚硬币 | 2.62s | keyword, sentence_end, sticker | light |
| `sfx-phone-vibration` | 手机 | 手机振动 | 0.66s | foley, keyword | light |
| `sfx-crowd-laughter` | 笑声 | 群体笑声 | 3.37s | reaction, contrast | medium |
| `sfx-crowd-applause` | 综艺 | 群体鼓掌 | 6.56s | reaction, contrast | medium |
| `sfx-crowd-disappointment` | 人声 | 群体失望 | 2.66s | reaction, contrast | medium |
| `sfx-crowd-boo` | 人声 | 群体喝倒彩 | 4.01s | reaction, contrast | medium |
| `sfx-crowd-surprise` | 人声 | 群体惊讶 | 1.59s | reaction, contrast | medium |
| `sfx-male-laugh` | 笑声 | 男性笑声 | 1.10s | reaction, contrast | medium |
| `sfx-female-sigh` | 人声 | 女性叹气 | 0.89s | reaction, contrast | medium |
| `sfx-female-gasp` | 人声 | 女性惊呼 | 1.16s | reaction, contrast | medium |
| `sfx-baby-laugh` | 笑声 | 婴儿笑声 | 0.59s | reaction, contrast | medium |
| `sfx-finger-snap` | 综艺 | 打响指 | 0.27s | reaction, contrast | medium |
| `sfx-water-pour` | 美食 | 倒水 | 2.83s | foley, keyword | light |
| `sfx-glass-clink` | 美食 | 杯子碰响 | 1.00s | foley, keyword | light |
| `sfx-scissors-snip` | 生活 | 剪刀 | 0.25s | foley, keyword | light |
| `sfx-keys-jingle` | 生活 | 钥匙碰撞 | 0.71s | foley, keyword | light |
| `sfx-book-close` | 生活 | 合上书本 | 2.74s | foley, keyword | light |
| `sfx-jar-open` | 生活 | 开玻璃罐 | 7.17s | foley, keyword | light |
| `sfx-lock-open` | 生活 | 开锁 | 0.21s | foley, keyword | light |
| `sfx-match-strike` | 生活 | 划火柴 | 1.35s | foley, keyword | light |
| `sfx-lighter-click` | 生活 | 打火机 | 0.67s | foley, keyword | light |
| `sfx-door-open` | 生活 | 开门 | 1.79s | foley, keyword | light |
| `sfx-squeaky-hinge` | 生活 | 门轴吱呀 | 0.96s | foley, keyword | light |
| `sfx-footsteps` | 生活 | 脚步 | 0.92s | foley, keyword | light |
| `sfx-camera-shutter` | 机械 | 相机快门 | 0.45s | foley, keyword | light |
| `sfx-keyboard-typing` | 机械 | 键盘输入 | 0.40s | foley, keyword | light |
| `sfx-electric-spark` | 科幻 | 电火花 | 3.11s | ambience, contrast, transition | medium |
| `sfx-electric-current` | 科幻 | 电流 | 0.22s | ambience, contrast, transition | medium |
| `sfx-steam-release` | 机械 | 蒸汽泄压 | 1.47s | foley, keyword | light |
| `sfx-telephone-hangup` | 手机 | 电话挂断 | 1.46s | foley, keyword | light |
| `sfx-telephone-dial` | 手机 | 拨号 | 1.68s | foley, keyword | light |
| `sfx-water-splash` | 环境音 | 水花 | 1.73s | ambience, contrast, transition | medium |
| `sfx-bubbles` | 环境音 | 连续气泡 | 0.44s | ambience, contrast, transition | medium |
| `sfx-rainfall` | 环境音 | 雨声 | 2.42s | ambience, contrast, transition | medium |
| `sfx-natural-thunder` | 环境音 | 自然雷鸣 | 8.85s | ambience, contrast, transition | medium |
| `sfx-wind-ambience` | 环境音 | 风声 | 7.70s | ambience, contrast, transition | medium |
| `sfx-fire-crackle` | 环境音 | 火焰 | 1.72s | ambience, contrast, transition | medium |
| `sfx-cat-meow` | 动物 | 猫叫 | 1.37s | foley, keyword | light |
| `sfx-dog-bark` | 动物 | 狗吠 | 0.39s | foley, keyword | light |
| `sfx-transition-impact` | 转场 | 复合转场击点 | 4.00s | transition, keyword | medium |
| `sfx-rising-transition` | 转场 | 上扬过渡 | 4.31s | transition, keyword | medium |
| `sfx-reverse-suction` | 转场 | 反向吸入 | 0.66s | transition, keyword | light |
| `sfx-soft-rise` | 转场 | 轻升起 | 2.00s | transition, keyword | light |
| `sfx-cartoon-spring` | 综艺 | 卡通弹簧 | 2.25s | reaction, contrast | medium |
| `sfx-stamp-hit` | 生活 | 盖章 | 0.58s | foley, keyword | light |
| `sfx-short-chime` | 魔法 | 短促清叮 | 1.25s | keyword, sentence_end, sticker | light |
| `sfx-error-buzzer` | 游戏 | 错误蜂鸣 | 2.77s | keyword, sentence_end, sticker | light |
| `sfx-result-sparkle` | 魔法 | 结果闪亮 | 1.76s | keyword, sentence_end, sticker | light |
| `sfx-light-sparkle` | 魔法 | 轻亮闪光 | 2.76s | keyword, sentence_end, sticker | light |
| `sfx-car-horn` | 交通 | 汽车喇叭 | 1.00s | foley, keyword | light |
| `sfx-basketball-bounce` | 运动 | 篮球落地 | 0.25s | foley, keyword | light |
| `sfx-metal-gong` | 乐器 | 锣鼓金属音 | 7.68s | foley, keyword | light |
| `sfx-vegetable-chopping` | 美食 | 切菜 | 11.79s | foley, keyword | light |
| `sfx-frying-sizzle` | 美食 | 炒菜滋啦 | 6.25s | foley, keyword | light |
| `sfx-heartbeat` | 悬疑 | 心跳 | 2.40s | ambience, contrast, transition | medium |
| `sfx-suspense-drum` | 乐器 | 悬念鼓点 | 0.93s | foley, keyword | light |
