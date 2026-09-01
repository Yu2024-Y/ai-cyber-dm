# US07 剧情语音播报

优先级：P1 ｜ 故事点：2 ｜ 对应 Sprint 3

## Card

- **As a**：跑团玩家
- **I want**：关键剧情能语音播报
- **So that**：增强沉浸感，解放眼睛

## Conversation

- 前置条件：玩家在会话中，收到剧情文本
- 描述：前端提供"播报"按钮，将剧情文本发给后端，后端用 edge-tts 合成 mp3 返回，前端播放
- 验收：能生成中文语音；播放流畅；支持多种音色（默认晓晓）

## Confirmation

```gherkin
Feature: 剧情语音播报
  Scenario: 播报剧情
    Given 玩家收到一段剧情文本
    When 玩家点击"播报"按钮
    Then 系统生成语音文件
    And 前端播放该语音
```
