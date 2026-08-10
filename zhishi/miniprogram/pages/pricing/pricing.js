const { request } = require("../../utils/api");
Page({
  data: { msg: "" },
  async buy(e) {
    const sku = e.currentTarget.dataset.sku;
    const res = await request("/api/pay/mock_checkout", "POST", { sku });
    this.setData({
      msg: res.ok ? `${res.name || sku} prepay=${res.prepay_id || "n/a"}` : res.error || "失败"
    });
    // 生产：wx.requestPayment({ ... }) 使用统一下单返回字段
  }
});
