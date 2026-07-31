import { ref } from 'vue'

export const routeLoading = ref(false)

let hideTimer = null

export function showRouteLoading() {
  if (hideTimer) {
    clearTimeout(hideTimer)
    hideTimer = null
  }
  routeLoading.value = true
}

export function hideRouteLoading() {
  if (hideTimer) {
    clearTimeout(hideTimer)
  }
  hideTimer = setTimeout(() => {
    routeLoading.value = false
    hideTimer = null
  }, 220)
}
