<template>
  <Teleport to="body">
    <div
      v-show="shared.visible.value"
      class="image-zoom-preview"
      :style="previewStyle"
    ></div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import { useImageZoomShared } from '@/composables/useImageZoom'

const shared = useImageZoomShared()

const previewStyle = computed(() => {
  if (!shared.rect.value) return {}
  const previewSize = shared.size.value
  const rect = shared.rect.value

  // 优先显示在图片右侧,空间不足则显示在左侧
  const spaceRight = window.innerWidth - rect.right
  let previewLeft = spaceRight >= previewSize + 10
    ? rect.right + 10
    : rect.left - previewSize - 10

  // 超出视口左边界则贴左显示
  if (previewLeft < 10) previewLeft = 10
  // 超出视口右边界则贴右显示
  if (previewLeft + previewSize > window.innerWidth - 10) {
    previewLeft = window.innerWidth - previewSize - 10
  }

  // 垂直方向:贴图片顶,不超出视口
  let previewTop = rect.top
  if (previewTop + previewSize > window.innerHeight - 10) {
    previewTop = window.innerHeight - previewSize - 10
  }
  if (previewTop < 10) previewTop = 10

  return {
    left: `${previewLeft}px`,
    top: `${previewTop}px`,
    width: `${previewSize}px`,
    height: `${previewSize}px`,
    backgroundImage: `url('${shared.src.value}')`,
    backgroundSize: 'contain',
    backgroundRepeat: 'no-repeat',
    backgroundPosition: 'center',
  }
})
</script>

<style>
.image-zoom-preview {
  position: fixed;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  pointer-events: none;
  z-index: 99999;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
  background-color: #fff;
  background-repeat: no-repeat;
  background-position: center;
  background-size: contain;
}
</style>
