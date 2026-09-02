<template>
  <transition name="route-loading-fade">
    <div v-if="routeLoading" class="route-loading" aria-live="polite" aria-label="页面加载中">
      <div class="route-loading__panel">
        <span class="route-loading__ring"></span>
        <div class="route-loading__copy">
          <strong>Loading workspace</strong>
          <span>Syncing route, permissions and market cockpit.</span>
        </div>
        <div class="route-loading__bars" aria-hidden="true">
          <i></i>
          <i></i>
          <i></i>
          <i></i>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { routeLoading } from '@/utils/routeLoading'
</script>

<style lang="scss" scoped>
.route-loading {
  position: fixed;
  inset: 0;
  // Element Plus allocates modal z-indexes from 2000 upwards. At 3000 this
  // overlay sat on top of every dialog, so the "password is still the initial
  // one" confirm raised during getInfo() rendered underneath a blurred veil —
  // invisible, and with nothing on screen to dismiss it.
  z-index: 1990;
  display: grid;
  place-items: center;
  pointer-events: none;
  background:
    radial-gradient(circle at 50% 44%, rgba(64, 158, 255, 0.16), transparent 28%),
    rgba(7, 13, 24, 0.2);
  backdrop-filter: blur(8px);
}

.route-loading__panel {
  width: min(420px, calc(100vw - 48px));
  display: grid;
  grid-template-columns: 58px 1fr;
  gap: 16px;
  align-items: center;
  padding: 18px;
  border-radius: 24px;
  color: #eaf4ff;
  background: linear-gradient(135deg, rgba(9, 18, 29, 0.92), rgba(18, 41, 64, 0.88));
  border: 1px solid rgba(148, 198, 255, 0.18);
  box-shadow: 0 30px 90px rgba(0, 0, 0, 0.28);
}

.route-loading__ring {
  width: 54px;
  height: 54px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.12);
  border-top-color: #54d2ff;
  border-right-color: #76f6c4;
  animation: routeSpin 0.92s linear infinite;
  box-shadow: 0 0 32px rgba(84, 210, 255, 0.26);
}

.route-loading__copy {
  display: grid;
  gap: 6px;

  strong {
    font-size: 15px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  span {
    color: rgba(234, 244, 255, 0.66);
    font-size: 12px;
  }
}

.route-loading__bars {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;

  i {
    height: 3px;
    border-radius: 999px;
    background: linear-gradient(90deg, rgba(84, 210, 255, 0.18), rgba(118, 246, 196, 0.9));
    transform-origin: left center;
    animation: routeBar 1.1s cubic-bezier(.16, 1, .3, 1) infinite;
  }

  i:nth-child(2) { animation-delay: 0.08s; }
  i:nth-child(3) { animation-delay: 0.16s; }
  i:nth-child(4) { animation-delay: 0.24s; }
}

.route-loading-fade-enter-active,
.route-loading-fade-leave-active {
  transition: opacity 0.24s ease, transform 0.24s ease;
}

.route-loading-fade-enter-from,
.route-loading-fade-leave-to {
  opacity: 0;
  transform: scale(0.985);
}

@keyframes routeSpin {
  to { transform: rotate(360deg); }
}

@keyframes routeBar {
  0%, 100% { transform: scaleX(0.18); opacity: 0.42; }
  50% { transform: scaleX(1); opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
  .route-loading__ring,
  .route-loading__bars i {
    animation: none;
  }
}
</style>
