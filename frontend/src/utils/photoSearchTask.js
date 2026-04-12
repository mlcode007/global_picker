import { photoSearchApi } from '@/api/products'

/** 与列表页、详情页拍照购轮询逻辑保持一致 */
export const PHOTO_POLL_ACTIVE = new Set([
  'queued',
  'dispatching',
  'running',
  'collecting',
  'parsing',
  'saving',
  'retry_waiting',
])

export const PHOTO_STATUS_LABEL = {
  queued: '排队中',
  dispatching: '分配设备',
  running: '执行中',
  collecting: '采集结果',
  parsing: '解析中',
  saving: '入库中',
  success: '完成',
  failed: '失败',
  cancelled: '已取消',
  retry_waiting: '等待重试',
}

export function formatPhotoTaskLine(task) {
  if (!task) return '准备中…'
  const base = PHOTO_STATUS_LABEL[task.status] || task.status
  if (task.step && PHOTO_POLL_ACTIVE.has(task.status)) {
    return `${base} · ${task.step}`
  }
  return base
}

export function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms))
}

export async function pollPhotoTaskUntilDone(taskId, onTick) {
  while (true) {
    const res = await photoSearchApi.getTask(taskId)
    onTick(res)
    if (!PHOTO_POLL_ACTIVE.has(res.status)) {
      return res
    }
    await sleep(2000)
  }
}
