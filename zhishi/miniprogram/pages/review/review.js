const { request, ensureSession } = require("../../utils/api");
Page({
  data: { reviews: [], reminders: [] },
  async onShow() {
    await ensureSession();
    const reviews = await request("/api/me/reviews");
    const reminders = await request("/api/me/reminders");
    this.setData({ reviews: reviews.reviews || [], reminders: reminders.reminders || [] });
  },
  async complete(e) {
    await request("/api/reminders/complete", "POST", { id: e.currentTarget.dataset.id });
    this.onShow();
  }
});
