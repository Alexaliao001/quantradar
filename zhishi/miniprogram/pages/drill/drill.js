const { request, ensureSession } = require("../../utils/api");
Page({
  data: {
    prompt: "A股当日买入的股票，通常最早何时可以卖出？",
    feedback: "",
    drills: []
  },
  async answer(e) {
    await ensureSession();
    const ans = e.currentTarget.dataset.a;
    const correct = ans === "b";
    const explanation = "A股股票实行T+1：当日买入，下一交易日才能卖出。";
    this.setData({ feedback: (correct ? "正确。" : "未答对。") + explanation });
    if (!correct) {
      await request("/api/drills", "POST", {
        prompt: this.data.prompt,
        user_answer: ans,
        correct: false,
        explanation
      });
      const drills = await request("/api/me/drills");
      this.setData({ drills: drills.drills || [] });
    }
  }
});
