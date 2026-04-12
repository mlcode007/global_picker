import http from './request'

export const userApi = {
  getUserInfo: () => http.get('/user/info'),
  updateUserInfo: (data) => http.patch('/user/info', data),
  changePassword: (data) => http.post('/user/change-password', data),
  uploadAvatar: (file) => {
    const formData = new FormData()
    formData.append('avatar', file)
    return http.post('/user/avatar', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  }
}