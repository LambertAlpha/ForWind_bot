# ForWind Bot

“其徐如林，其疾如風，不動如山，侵略如火。 ——《孫子·軍爭》”

ForWind Bot 是一个 Telegram 机器人，用于实时监控加密货币交易对的价格波动。当某个交易对的价格在 5 分钟内上涨 2% 或以上时，机器人将发送通知。

## 功能

- `/start` - 开始监控价格变化
- `/end` - 暂停监控价格变化
- `/list` - 列出所有正在监控的交易对
- `/add SYMBOL` - 添加交易对（例如：`/add BTC`）
- `/delete SYMBOL` - 删除交易对（例如：`/delete BTC`）
- `/help` - 显示帮助信息

## 安装步骤

1. 克隆该项目
2. 安装依赖库：
   ```
   pip install -r requirements.txt
   ```
3. 创建 `.env` 文件（参考 `.env.example`）:
   - 从 [@BotFather](https://t.me/BotFather) 获取 Telegram 机器人令牌
   - 设置授权用户 ID（可选）
4. 运行机器人：
   ```
   python main.py
   ```

## 设置 Telegram 机器人

1. 在 Telegram 中找到 [@BotFather](https://t.me/BotFather)
2. 发送 `/newbot` 命令
3. 按照提示设置机器人名称和用户名
4. 复制 BotFather 提供的令牌到 `.env` 文件中
5. 发送 `/setcommands` 命令给 BotFather，并选择你的机器人
6. 复制粘贴以下命令列表：
   ```
   start - 开始监控价格变化
   end - 暂停监控价格变化
   list - 列出所有正在监控的交易对
   add - 添加交易对 (例如: /add BTC)
   delete - 删除交易对 (例如: /delete BTC)
   help - 显示帮助信息
   ```

## 获取用户 ID
要获取您的 Telegram 用户 ID，请向 [@userinfobot](https://t.me/userinfobot) 发送任意消息。

## 注意事项

- 默认使用币安交易所 API
- 默认价格检查间隔为 5 秒
- 交易对数据存储在本地 `trading_pairs.json` 文件中
- 默认价格增2%时通知
