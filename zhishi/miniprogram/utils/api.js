const app = getApp();

function request(path, method = "GET", data = {}) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: app.globalData.apiBase + path,
      method,
      data,
      header: {
        "Content-Type": "application/json",
        "X-Session": app.globalData.session || ""
      },
      success: (res) => resolve(res.data),
      fail: reject
    });
  });
}

async function ensureSession() {
  if (app.globalData.session) return app.globalData.session;
  const data = await request("/api/session", "POST", {});
  app.globalData.session = data.session;
  wx.setStorageSync("zhishi_session", data.session);
  return data.session;
}

module.exports = { request, ensureSession };
