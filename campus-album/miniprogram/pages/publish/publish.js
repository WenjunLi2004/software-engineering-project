const api = require('../../utils/api');

const MAX_TEXT_LENGTH = 500;

Page({
  data: {
    text: '',
    charCount: 0,
    maxLength: MAX_TEXT_LENGTH,
    submitting: false,
    errorMessage: '',
    needLogin: false,
    currentUser: null
  },

  onShow() {
    this.syncAuthState();
  },

  onUnload() {
    if (this._redirectTimer) {
      clearTimeout(this._redirectTimer);
      this._redirectTimer = null;
    }
  },

  syncAuthState() {
    const token = api.getToken();
    const user = api.getUser();
    const isLoggedIn = Boolean(token);

    this.setData({
      currentUser: isLoggedIn ? user : null,
      needLogin: !isLoggedIn,
      errorMessage: isLoggedIn && this.data.needLogin ? '' : this.data.errorMessage
    });
  },

  onTextInput(e) {
    const value = (e && e.detail && typeof e.detail.value === 'string') ? e.detail.value : '';
    const nextData = {
      text: value,
      charCount: value.length
    };

    if (this.data.errorMessage && value.trim().length > 0 && !this.data.needLogin) {
      nextData.errorMessage = '';
    }

    this.setData(nextData);
  },

  onSubmit() {
    if (this.data.submitting) {
      return;
    }

    const trimmed = (this.data.text || '').trim();
    if (!trimmed) {
      this.setData({
        errorMessage: '请输入作品内容'
      });
      return;
    }

    const token = api.getToken();
    if (!token) {
      const loginMsg = '请先登录后再发布作品';
      this.setData({
        currentUser: null,
        needLogin: true,
        errorMessage: loginMsg
      });
      this.promptLogin(loginMsg);
      return;
    }

    this.setData({
      submitting: true,
      errorMessage: ''
    });

    api.createPost(trimmed)
      .then(() => {
        wx.showToast({
          title: '发布成功',
          icon: 'success',
          duration: 900
        });

        this._redirectTimer = setTimeout(() => {
          this._redirectTimer = null;
          wx.reLaunch({
            url: '/pages/index/index'
          });
        }, 600);
      })
      .catch((err) => {
        const statusCode = err && err.statusCode;
        const code = err && err.code;
        const message = (err && (err.message || err.errMsg)) || '发布失败，请稍后重试';

        if (statusCode === 401 || code === 'UNAUTHORIZED') {
          api.clearSession();
          const authMessage = (err && err.message) || '登录状态无效或已过期，请重新登录';
          this.setData({
            submitting: false,
            currentUser: null,
            needLogin: true,
            errorMessage: authMessage
          });
          this.promptLogin(authMessage);
          return;
        }

        this.setData({
          submitting: false,
          errorMessage: message
        });
      });
  },

  promptLogin(message) {
    wx.showModal({
      title: '登录提示',
      content: message || '登录状态无效或已过期，请重新登录',
      confirmText: '去登录',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          this.onGoToLogin();
        }
      }
    });
  },

  onGoToLogin() {
    wx.navigateTo({
      url: '/pages/login/login',
      fail: () => {
        wx.reLaunch({
          url: '/pages/login/login'
        });
      }
    });
  },

  onCancel() {
    if (this.data.submitting) {
      return;
    }

    const pages = getCurrentPages();
    if (pages && pages.length > 1) {
      wx.navigateBack({ delta: 1 });
      return;
    }

    wx.reLaunch({
      url: '/pages/index/index'
    });
  }
});
