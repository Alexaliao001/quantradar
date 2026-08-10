const { request } = require("../../utils/api");
Page({
  data: { lessons: [], markdown: "" },
  async onLoad() {
    const data = await request("/api/lessons");
    this.setData({ lessons: data.lessons || [] });
  },
  async open(e) {
    const id = e.currentTarget.dataset.id;
    const data = await request(`/api/lessons/${id}`);
    this.setData({ markdown: (data.lesson && data.lesson.markdown) || "" });
  }
});
