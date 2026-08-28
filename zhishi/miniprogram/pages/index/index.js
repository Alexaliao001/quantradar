const app = getApp();
Page({
  data: { disclaimer: "" },
  onLoad() {
    this.setData({ disclaimer: app.globalData.disclaimer });
  }
});
