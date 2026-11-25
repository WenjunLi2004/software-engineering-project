const BASE_URL = 'http://127.0.0.1:5001';

const TOKEN_STORAGE_KEY = 'campus_album_token';
const USER_STORAGE_KEY = 'campus_album_user';

function resolveBaseUrl() {
  if (typeof getApp === 'function') {
    const app = getApp();
    if (app && app.globalData && app.globalData.baseUrl) {
      return app.globalData.baseUrl;
    }
  }
  return BASE_URL;
}

function getToken() {
  try {
    return wx.getStorageSync(TOKEN_STORAGE_KEY) || '';
  } catch (_err) {
    return '';
  }
}

function getUser() {
  try {
    return wx.getStorageSync(USER_STORAGE_KEY) || null;
  } catch (_err) {
    return null;
  }
}

function setSession(token, user) {
  if (token) {
    wx.setStorageSync(TOKEN_STORAGE_KEY, token);
  } else {
    wx.removeStorageSync(TOKEN_STORAGE_KEY);
  }

  if (user) {
    wx.setStorageSync(USER_STORAGE_KEY, user);
  } else {
    wx.removeStorageSync(USER_STORAGE_KEY);
  }
}

function clearSession() {
  wx.removeStorageSync(TOKEN_STORAGE_KEY);
  wx.removeStorageSync(USER_STORAGE_KEY);
}

function parseResponseData(rawData) {
  if (typeof rawData === 'string') {
    try {
      return JSON.parse(rawData);
    } catch (_err) {
      return null;
    }
  }
  return rawData;
}

function request({ url, method = 'GET', data, auth = false }) {
  const fullUrl = /^https?:\/\//.test(url) ? url : `${resolveBaseUrl()}${url}`;
  const header = {
    'Content-Type': 'application/json'
  };

  if (auth) {
    const token = getToken();
    if (token) {
      header.Authorization = `Bearer ${token}`;
    }
  }

  return new Promise((resolve, reject) => {
    const options = {
      url: fullUrl,
      method,
      header,
      success(res) {
        const statusCode = res.statusCode;
        const body = parseResponseData(res.data);

        if (statusCode >= 200 && statusCode < 300) {
          resolve(body);
          return;
        }

        const apiError =
          body && typeof body === 'object' && body.error && typeof body.error === 'object'
            ? body.error
            : null;

        reject({
          statusCode,
          code: (apiError && apiError.code) || 'REQUEST_FAILED',
          message: (apiError && apiError.message) || `请求失败（HTTP ${statusCode}）`
        });
      },
      fail() {
        reject({
          statusCode: 0,
          code: 'NETWORK_ERROR',
          message: '无法连接后端服务，请确认 Flask 已运行在 http://127.0.0.1:5001'
        });
      }
    };

    if (data !== undefined) {
      options.data = data;
    }

    wx.request(options);
  });
}

function register(username, password) {
  return request({
    url: '/api/auth/register',
    method: 'POST',
    data: { username, password }
  });
}

function login(username, password) {
  return request({
    url: '/api/auth/login',
    method: 'POST',
    data: { username, password }
  });
}

function createPost(text) {
  return request({
    url: '/api/posts',
    method: 'POST',
    data: { text },
    auth: true
  });
}

function listPosts() {
  return request({
    url: '/api/posts',
    method: 'GET'
  });
}

module.exports = {
  BASE_URL,
  getToken,
  getUser,
  setSession,
  clearSession,
  request,
  register,
  login,
  createPost,
  listPosts
};
