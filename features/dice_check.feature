Feature: 骰子检定
  作为跑团玩家，我希望系统对检定进行结构化判定，
  以便剧情随骰子结果演进。

  Scenario: 有效检定通过
    Given 玩家进行检定 "1d20+3" 对抗难度 15
    When 掷骰完成
    Then 系统返回结构化的检定结果
    And 结果包含公式、数值、难度与成败

  Scenario: 无效公式被拒绝
    Given 玩家进行检定 "abc" 对抗难度 10
    When 系统校验公式
    Then 抛出无效公式错误

  Scenario: 高难度导致失败
    Given 玩家进行检定 "1d20" 对抗难度 30
    When 掷骰完成
    Then 判定结果为失败
