import { ref, computed } from 'vue'

// 全局单例预览层: 避免每个 ImageMagnifier 各自创建一个 body 下的预览 div
// 多个实例同时 hover 时,只渲染最后一个
const sharedState = {
  visible: ref(false),
  src: ref(''),
  rect: ref(null),
  size: ref(400),
}

export function useImageZoomShared() {
  return sharedState
}

function hideShared() {
  sharedState.visible.value = false
  sharedState.rect.value = null
}

export function useImageZoom() {
  function show(src, rect, size) {
    sharedState.src.value = src
    sharedState.rect.value = rect
    sharedState.size.value = size
    sharedState.visible.value = true
  }
  return { show, hide: hideShared }
}
