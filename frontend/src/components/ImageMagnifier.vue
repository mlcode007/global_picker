<template>
  <div
    ref="wrapperRef"
    class="image-zoom-wrapper"
    @mouseenter="onMouseEnter"
    @mouseleave="onMouseLeave"
  >
    <slot></slot>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useImageZoomShared } from '@/composables/useImageZoom'

const props = defineProps({
  src: {
    type: String,
    required: true,
  },
  previewSize: {
    type: Number,
    default: 400,
  },
})

const wrapperRef = ref(null)
const shared = useImageZoomShared()

function onMouseEnter() {
  const wrapper = wrapperRef.value
  if (!wrapper) return
  const img = wrapper.querySelector('img')
  if (!img) return
  const realSrc = img.currentSrc || img.src || props.src
  const rect = img.getBoundingClientRect()
  shared.src.value = realSrc
  shared.rect.value = rect
  shared.size.value = props.previewSize
  shared.visible.value = true
}

function onMouseLeave() {
  shared.visible.value = false
  shared.rect.value = null
}
</script>

<style scoped>
.image-zoom-wrapper {
  position: relative;
  display: inline-block;
  overflow: visible !important;
}
</style>
