import http from './request'

export const authApi = {
  sendSmsCode: (phone, purpose = 'login') =>
    http.post('/auth/sms/send', { phone, purpose }),

  smsLogin: (phone, code) =>
    http.post('/auth/sms/login', { phone, code }),

  passwordLogin: (username, password) =>
    http.post('/auth/login', { username, password }),

  register: (data) =>
    http.post('/auth/register', data),

  getMe: () =>
    http.get('/auth/me'),

  updateProfile: (data) =>
    http.put('/auth/me', data),

  refreshToken: () =>
    http.post('/auth/refresh'),
}
