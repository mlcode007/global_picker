export const STATUS_MAP = {
  pending:   { text: '待定',   color: 'default' },
  selected:  { text: '已选',   color: 'success' },
  abandoned: { text: '放弃',   color: 'error'   },
}

export const REGION_MAP = {
  PH: '菲律宾', MY: '马来西亚', TH: '泰国',
  SG: '新加坡', ID: '印尼', VN: '越南',
}

export function profitRateColor(rate) {
  const r = parseFloat(rate) * 100
  if (r >= 20) return '#52c41a'
  if (r >= 10) return '#faad14'
  return '#ff4d4f'
}
