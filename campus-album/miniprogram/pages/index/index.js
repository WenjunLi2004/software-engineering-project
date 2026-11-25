const api = require('../../utils/api');

function pad2(num) {
  return num < 10 ? '0' + num : String(num);
}

function formatTimestamp(isoString) {
  if (!isoString || typeof isoString !== 'string') {
    return '';
  }

  const trimmed = isoString.trim();
  if (!trimmed) {
    return '';
  }

  let normalized = trimmed;
  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(trimmed)) {
    normalized = trimmed.replace(' ', 'T') + 'Z';
  }

  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) {
    return trimmed;
  }

  const year = date.getFullYear();
  const month = pad2(date.getMonth() + 1);
  const day = pad2(date.getDate());
  const hours = pad2(date.getHours());
  const minutes = pad2(date.getMinutes());
  return year + '-' + month + '-' + day + ' ' + hours + ':' + minutes;
}

function formatCurrentClock() {
  const now = new Date();
  return pad2(now.getHours()) + ':' + pad2(now.getMinutes()) + ':' + pad2(now.getSeconds());
}

function getAuthorInitial(username) {
  if (!username || typeof username !== 'string') {
    return '校';
  }
  const trimmed = username.trim();
  if (!trimmed) {
    return '校';
  }
  const firstChar = Array.from(trimmed)[0];
  return /[a-z]/.test(firstChar) ? firstChar.toUpperCase() : firstChar;
}

function normalizePost(item) {
  const authorObj = item && item.author && typeof item.author === 'object' ? item.author : {};
  const authorUsername = authorObj.username || '匿名同学';
  return {
    id: item.id,
    text: typeof item.text === 'string' ? item.text : '',
    author: {
      id: authorObj.id !== undefined ? authorObj.id : null,
      username: authorUsername,
    },
    authorInitial: getAuthorInitial(authorUsername),
    createdAt: item.createdAt || '',
    displayTime: formatTimestamp(item.createdAt),
  };
}

Page({
  data: {
    isLoggedIn: false,
    currentUser: null,
    currentUserInitial: '',
    posts: [],
    loading: false,
    hasLoaded: false,
    errorMessage: '',
    lastUpdatedText: '',
  },

  _requestSeq: 0,

  onLoad() {
    this.syncUserStatus();
  },

  onShow() {
    this.syncUserStatus();
    this.loadPosts({ fromPullDown: false, showToast: false });
  },

  onPullDownRefresh() {
    this.syncUserStatus();
    this.loadPosts({ fromPullDown: true, showToast: false });
  },

  syncUserStatus() {
    const token = api.getToken();
    const user = api.getUser();
    const isLoggedIn = Boolean(token && user && user.username);
    this.setData({
      isLoggedIn: isLoggedIn,
      currentUser: isLoggedIn ? user : null,
      currentUserInitial: isLoggedIn ? getAuthorInitial(user.username) : '',
    });
  },

  loadPosts(options) {
    const opts = options || {};
    const fromPullDown = Boolean(opts.fromPullDown);
    const showToast = Boolean(opts.showToast);

    this._requestSeq += 1;
    const currentSeq = this._requestSeq;

    this.setData({
      loading: true,
      errorMessage: '',
    });

    api
      .listPosts()
      .then((data) => {
        if (currentSeq !== this._requestSeq) {
          return;
        }
        const rawPosts = Array.isArray(data)
          ? data
          : data && Array.isArray(data.posts)
          ? data.posts
          : [];
        const posts = rawPosts.map(normalizePost);

        this.setData({
          posts: posts,
          loading: false,
          hasLoaded: true,
          errorMessage: '',
          lastUpdatedText: formatCurrentClock(),
        });

        if (fromPullDown) {
          wx.stopPullDownRefresh();
        }
        if (showToast) {
          wx.showToast({
            title: '列表已刷新',
            icon: 'success',
            duration: 1200,
          });
        }
      })
      .catch((err) => {
        if (currentSeq !== this._requestSeq) {
          return;
        }
        const message =
          (err && err.message) ||
          (err && err.error && err.error.message) ||
          '无法加载校园作品，请确认本地 Flask 后端服务正在运行';

        this.setData({
          loading: false,
          hasLoaded: true,
          errorMessage: message,
        });

        if (fromPullDown) {
          wx.stopPullDownRefresh();
        }
      });
  },

  handleRefresh() {
    this.syncUserStatus();
    this.loadPosts({ fromPullDown: false, showToast: true });
  },

  handleGoLogin() {
    wx.navigateTo({
      url: '/pages/login/login',
    });
  },

  handleGoPublish() {
    const token = api.getToken();
    const user = api.getUser();
    if (!token || !user || !user.username) {
      this.syncUserStatus();
      wx.showToast({
        title: '请先登录后再发布作品',
        icon: 'none',
      });
      wx.navigateTo({
        url: '/pages/login/login',
      });
      return;
    }

    wx.navigateTo({
      url: '/pages/publish/publish',
    });
  },

  handleLogout() {
    wx.showActionSheet({
      itemList: ['切换其他账号', '退出当前账号'],
      success: (res) => {
        if (res.tapIndex === 0) {
          api.clearSession();
          this.syncUserStatus();
          wx.navigateTo({
            url: '/pages/login/login',
          });
        } else if (res.tapIndex === 1) {
          api.clearSession();
          this.syncUserStatus();
          wx.showToast({
            title: '已退出登录',
            icon: 'none',
          });
        }
      },
    });
  },
});
