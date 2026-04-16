import http from './request'

export const userApi = {
  getUserInfo: () => http.get('/user/info'),
  /** 导出列偏好（localStorage 清空后用于恢复） */
  getExportFieldPreferences: () => http.get('/user/export-field-preferences'),
  putExportFieldPreferences: (data) => http.put('/user/export-field-preferences', data),
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