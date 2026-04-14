import { taskApi } from '@/api/products'

/** 轮询中的采集任务状态 */
export const CRAWL_POLL_ACTIVE = new Set(['pending', 'running'])

export const CRAWL_STATUS_LABEL = {
  pending: '等待调度',
  running: '采集中',
  done: '完成',
  failed: '失败',
}

export function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms))
}

/**
 * 列表/日志用单行描述（含失败原因摘要）
 */
export function formatCrawlTaskLine(task) {
  if (!task) return '准备中…'
  // 后端写入的细粒度进度（如：正在处理验证码）
  if (task.status === 'running' && task.status_detail) {
    return task.status_detail
  }
  const base = CRAWL_STATUS_LABEL[task.status] || task.status
  if (task.status === 'failed' && task.error_msg) {
    const msg = String(task.error_msg).trim()
    const short = msg.length > 120 ? `${msg.slice(0, 120)}…` : msg
    return `${base}：${short}`
  }
  if (task.status === 'running') {
    return `${base} · 抓取 TikTok 商品页`
  }
  if (task.status === 'pending') {
    return `${base} · 队列中`
  }
  if (task.status === 'done') {
    return '采集完成，数据已更新'
  }
  return base
}

/**
 * 阻塞直到任务结束或超时；onTick 用于更新行内 UI。
 */
export async function pollCrawlTaskUntilDone(taskId, onTick, opts = {}) {
  const interval = opts.pollIntervalMs ?? 1600
  const maxMs = opts.maxWaitMs ?? 15 * 60 * 1000
  const start = Date.now()

  while (Date.now() - start < maxMs) {
    const t = await taskApi.get(taskId)
    onTick?.(t)
    if (t.status === 'done' || t.status === 'failed') {
      return t
    }
    await sleep(interval)
  }

  throw new Error('采集任务等待超时（15 分钟内未完成），请稍后刷新列表查看状态')
}
