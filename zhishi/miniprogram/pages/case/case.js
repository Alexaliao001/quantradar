const { request } = require("../../utils/api");
Page({
  data: { cases: [] },
  async onLoad() {
    const data = await request("/api/cases");
    this.setData({ cases: data.cases || [] });
  },
  open(e) {
    const symbol = e.currentTarget.dataset.symbol;
    wx.navigateTo({ url: `/pages/check/check?symbol=${symbol}` });
  }
});
