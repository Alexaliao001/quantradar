App({
  globalData: {
    apiBase: "http://127.0.0.1:8787",
    session: "",
    disclaimer: "本产品为投资教育工具，不构成任何投资建议。市场有风险，决策须自负。"
  },
  onLaunch() {
    const session = wx.getStorageSync("zhishi_session");
    if (session) this.globalData.session = session;
  }
});
