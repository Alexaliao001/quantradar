const { request, ensureSession } = require("../../utils/api");
Page({
  data: { symbol: "", result: null, error: "", hypothesis: "", invalidation: "" },
  onSymbol(e) { this.setData({ symbol: e.detail.value }); },
  onHyp(e) { this.setData({ hypothesis: e.detail.value }); },
  onInv(e) { this.setData({ invalidation: e.detail.value }); },
  async analyze() {
    const result = await request(`/api/analyze?symbol=${this.data.symbol}&market=A`);
    if (!result.ok) this.setData({ error: result.error || "数据不足", result: null });
    else this.setData({ result, error: "" });
  },
  async sample() {
    const result = await request("/api/sample");
    this.setData({ result, symbol: result.symbol || "600519", error: "" });
  },
  async saveReview() {
    await ensureSession();
    const r = this.data.result;
    const res = await request("/api/reviews", "POST", {
      symbol: r.symbol,
      name: r.name,
      primary_score: r.primary_score,
      posture: r.posture,
      hypothesis: this.data.hypothesis,
      invalidation: this.data.invalidation
    });
    wx.showToast({ title: res.ok ? "已写入" : "失败", icon: "none" });
  }
});
