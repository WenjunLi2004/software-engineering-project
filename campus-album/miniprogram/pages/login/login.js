const api = require('../../utils/api');

function resolveErrorMessage(err, mode) {
  if (err && typeof err.message === 'string' && err.message.trim()) {
    return err.message.trim();
  }
  const code = err && err.code;
  const statusCode = err && err.statusCode;

  if (code === 'INVALID_CREDENTIALS' || statusCode === 401) {
    return '用户名或密码错误';
  }
  if (code === 'USERNAME_TAKEN' || statusCode === 409) {
    return '用户名已被注册，请更换用户名或直接登录';
  }
  if (code === 'INVALID_INPUT' || statusCode === 400) {
    return '请输入有效的用户名和密码';
  }
  return mode === 'register'
    ? '注册失败，请检查网络或确认本地后端服务已启动'
    : '登录失败，请检查网络或确认本地后端服务已启动';
}

Page({
  data: {
    mode: 'login',
    username: '',
    password: '',
    errorMessage: '',
    submitting: false,
    currentUser: null
  },

  onLoad(options) {
    if (options && options.mode === 'register') {
      this.setData({ mode: 'register' });
    }
  },

  onShow() {
    this.setData({
      currentUser: api.getUser() || null
    });
  },

  onSwitchMode(event) {
    const nextMode = event.currentTarget.dataset.mode;
    if (!nextMode || nextMode === this.data.mode || this.data.submitting) {
      return;
    }
    this.setData({
      mode: nextMode,
      errorMessage: ''
    });
  },

  onToggleMode() {
    if (this.data.submitting) {
      return;
    }
    this.setData({
      mode: this.data.mode === 'login' ? 'register' : 'login',
      errorMessage: ''
    });
  },

  onUsernameInput(event) {
    this.setData({
      username: event.detail.value,
      errorMessage: ''
    });
  },

  onPasswordInput(event) {
    this.setData({
      password: event.detail.value,
      errorMessage: ''
    });
  },

  onLogout() {
    if (this.data.submitting) {
      return;
    }
    api.clearSession();
    this.setData({
      currentUser: null,
      errorMessage: ''
    });
    wx.showToast({
      title: '已退出登录',
      icon: 'none'
    });
  },

  onContinueAsGuest() {
    wx.reLaunch({
      url: '/pages/index/index'
    });
  },

  onSubmit() {
    if (this.data.submitting) {
      return;
    }

    const mode = this.data.mode;
    const username = (this.data.username || '').trim();
    const password = this.data.password || '';

    if (!username) {
      this.setData({ errorMessage: '请输入用户名' });
      return;
    }
    if (!password.trim()) {
      this.setData({ errorMessage: '请输入密码' });
      return;
    }

    this.setData({
      submitting: true,
      errorMessage: ''
    });

    if (mode === 'register') {
      api
        .register(username, password)
        .then(() =>
          api.login(username, password).then(
            (loginRes) => {
              api.setSession(loginRes.token, loginRes.user);
              this.setData({ submitting: false });
              wx.reLaunch({
                url: '/pages/index/index'
              });
            },
            () => {
              this.setData({
                mode: 'login',
                submitting: false,
                errorMessage: '账号已注册成功，但自动登录失败，请直接点击登录'
              });
            }
          )
        )
        .catch((err) => {
          this.setData({
            submitting: false,
            errorMessage: resolveErrorMessage(err, 'register')
          });
        });
      return;
    }

    api
      .login(username, password)
      .then((res) => {
        api.setSession(res.token, res.user);
        this.setData({ submitting: false });
        wx.reLaunch({
          url: '/pages/index/index'
        });
      })
      .catch((err) => {
        this.setData({
          submitting: false,
          errorMessage: resolveErrorMessage(err, 'login')
        });
      });
  }
});
