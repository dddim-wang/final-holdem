import { createContext, useContext, useState } from 'react';

const TranslationContext = createContext();

export const useTranslation = () => {
  const context = useContext(TranslationContext);
  if (!context) {
    throw new Error('useTranslation must be used within a TranslationProvider');
  }
  return context;
};

// Chinese translations for all text in the app
const translations = {
  // App.jsx
  'Hold\'em Squat': '德州扑克深蹲',
  'The Ultimate Poker Fitness Game!': '终极扑克健身游戏！',
  'Host a room, show the QR, and let up to 15 players join!': '创建房间，显示二维码，让最多15名玩家加入！',
  'Betting is simultaneous with fixed options: check / 4 / 8 / fold': '下注同时进行，固定选项：过牌 / 4 / 8 / 弃牌',
  'First flop shows 2 cards for an extra betting round': '首次翻牌显示2张牌，增加一轮下注',
  'Losers do squats equal to their total bets!': '失败者要做与总下注数量相等的深蹲！',
  'Creating…': '创建中…',
  'Create Game (Host)': '创建游戏（主持人）',
  'Ready to play the most exciting poker game ever?': '准备好玩最刺激的扑克游戏了吗？',

  // HostView.jsx
  'Host — Game': '主持人 — 游戏',
  'Home': '首页',
  'Scan to join:': '扫描加入：',
  'Players:': '玩家：',
  'Stage:': '阶段：',
  'Raise status:': '加注状态：',
  'Someone raised': '有人加注',
  'No one has raised yet': '还没有人加注',
  'Start Round': '开始回合',
  'Deal next card': '发下一张牌',
  'Show results': '显示结果',
  'Play another round': '再玩一轮',
  'Hand rankings': '牌型排名',
  'Chat': '聊天',
  'Players': '玩家',
  'in': '参与',
  'folded': '弃牌',
  'acted': '已行动',
  'waiting': '等待中',
  'MUST CALL': '必须跟注',
  'Round Results': '回合结果',
  'Board wins! All players split the pot!': '公共牌获胜！所有玩家平分底池！',
  'The board had the best hand!': '公共牌有最好的牌型！',
  'won!!': '获胜！！',
  'All other players folded!': '所有其他玩家都弃牌了！',
  'won the round!': '赢得回合！',
  'All active players split the pot equally!': '所有活跃玩家平分底池！',
  'Board hand': '公共牌牌型',
  'Winning hand': '获胜牌型',
  'Congratulations to all winners!': '恭喜所有获胜者！',
  'Board Cards': '公共牌',
  'No cards revealed yet': '还没有显示牌',
  'Reset Round?': '重置回合？',
  'This will end the current round and start a new one. All players will be dealt new cards.': '这将结束当前回合并开始新的一轮。所有玩家将获得新牌。',
  'Cancel': '取消',
  'Yes, Reset Round': '是的，重置回合',
  'Dealing Cards...': '发牌中...',
  'Please wait while cards are being distributed': '请等待发牌完成',
  'Game': '游戏',
  'Game ID:': '游戏ID：',
  'Click anywhere to close': '点击任意位置关闭',

  // PlayerView.jsx
  'Joining Game...': '加入游戏中...',
  'Your name:': '你的名字：',
  'Current bet:': '当前下注：',
  'Squats you must complete:': '你必须完成的深蹲：',
  'You must call or fold!': '你必须跟注或弃牌！',
  'Call amount:': '跟注数量：',
  'You Folded!': '你弃牌了！',
  'You are no longer in this round. You must complete': '你不再参与这一轮。你必须完成',
  'squats.': '个深蹲。',
  'Wait for the round to end to see the results.': '等待回合结束查看结果。',
  'You folded and cannot take any more actions this round.': '你已弃牌，本轮无法再采取行动。',
  'Check': '过牌',
  'Call': '跟注',
  'More Squats': '更多深蹲',
  'Raise to 8 More Squats': '加注到8个更多深蹲',
  'Bet 4 More Squats': '下注4个更多深蹲',
  'Bet 8 More Squats': '下注8个更多深蹲',
  'I Quit': '我退出',
  'Board wins! All players split the pot!': '公共牌获胜！所有玩家平分底池！',
  'You won!!': '你赢了！！',
  'All other players folded!': '所有其他玩家都弃牌了！',
  'Congratulations on winning!': '恭喜获胜！',
  'Hand over. You must do': '手牌结束。你必须做',
  'squats!': '个深蹲！',
  'You won because you were the last player standing!': '你赢了，因为你是最后一个站着的玩家！',
  'Your hand:': '你的手牌：',
  'The board had the best hand:': '公共牌有最好的手牌：',
  'Leave a comment (scrolls on host screen):': '留下评论（在主持人屏幕上滚动）：',
  'Type your message…': '输入你的消息…',
  'Sending…': '发送中…',
  'Send': '发送',
  'Are you sure?': '你确定吗？',
  'If you quit now, you must complete': '如果你现在退出，你必须完成',
  'Yes, I Quit': '是的，我退出',

  // Login.jsx
  'Login': '登录',
  'Welcome back to Hold\'em Squat!': '欢迎回到德州扑克深蹲！',
  'Username': '用户名',
  'Enter your username': '输入你的用户名',
  'Password': '密码',
  'Enter your password': '输入你的密码',
  'Don\'t have an account? Register here!': '没有账户？在这里注册！',
  'Username must be 20 characters or less': '用户名必须少于20个字符',
  'Login failed': '登录失败',

  // Register.jsx
  'Register': '注册',
  'Join the Hold\'em Squat community!': '加入德州扑克深蹲社区！',
  'Choose a username': '选择一个用户名',
  'Choose a password': '选择一个密码',
  'Create Account': '创建账户',
  'Already have an account? Login here!': '已有账户？在这里登录！',
  'Username must be at least 3 characters': '用户名必须至少3个字符',
  'Register failed': '注册失败',

  // HandRankings.jsx
  'Texas Hold\'em Rankings': '德州扑克牌型排名',
  'Close': '关闭',

  // CommentTicker.jsx
  'No comments yet': '还没有评论',

  // MusicPlayer.jsx
  'Pause Jay\'s T&E': '暂停Jay\'s T&E',
  'Jay\'s T&E': 'Jay\'s T&E',

  // Common
  'Loading...': '加载中...',
  'Loading Game...': '加载游戏中...',
  'Error': '错误',
  'Success': '成功',
  'Warning': '警告',
  'Info': '信息',
  'Hi': '你好',
  'Logout': '退出登录',
};

export const TranslationProvider = ({ children }) => {
  const [isChinese, setIsChinese] = useState(false);

  const t = (key) => {
    if (isChinese && translations[key]) {
      return translations[key];
    }
    return key;
  };

  const toggleLanguage = () => {
    setIsChinese(!isChinese);
  };

  const value = {
    isChinese,
    toggleLanguage,
    t,
  };

  return (
    <TranslationContext.Provider value={value}>
      {children}
    </TranslationContext.Provider>
  );
};
