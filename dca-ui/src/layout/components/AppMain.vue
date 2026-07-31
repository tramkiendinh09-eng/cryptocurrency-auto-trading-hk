<template>
  <section class="app-main">
    <router-view v-slot="{ Component, route }">
      <transition name="fade-transform" mode="out-in">
        <keep-alive :include="tagsViewStore.cachedViews">
          <div>
            <component v-if="!route.meta.link" :is="Component" :key="route.path"/>
          </div>
        </keep-alive>
      </transition>
    </router-view>
    <iframe-toggle />
    <copyright />
  </section>
</template>

<script setup>
import copyright from "./Copyright/index"
import iframeToggle from "./IframeToggle/index"
import useTagsViewStore from '@/store/modules/tagsView'

const route = useRoute()
const tagsViewStore = useTagsViewStore()

onMounted(() => {
  addIframe()
})

watchEffect(() => {
  addIframe()
})

function addIframe() {
  if (route.meta.link) {
    useTagsViewStore().addIframeView(route)
  }
}
</script>

<style lang="scss" scoped>
.app-main {
  /* 50= navbar  50  */
  min-height: calc(100vh - 50px);
  width: 100%;
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(circle at 16% 8%, rgba(64, 158, 255, 0.06), transparent 24%),
    linear-gradient(180deg, rgba(248, 251, 255, 0.92), rgba(244, 247, 252, 0.98));
}

.app-main::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(64, 158, 255, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(64, 158, 255, 0.035) 1px, transparent 1px);
  background-size: 38px 38px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.72), transparent 42%);
}

.app-main :deep(.app-container) {
  position: relative;
  animation: workspaceRise 0.46s cubic-bezier(.16, 1, .3, 1) both;
}

.fixed-header + .app-main {
  overflow-y: auto;
  scrollbar-gutter: auto;
  height: calc(100vh - 50px);
  min-height: 0px;
}

.app-main:has(.copyright) {
  padding-bottom: 36px;
}

.fixed-header + .app-main {
  margin-top: 50px;
}

.hasTagsView {
  .app-main {
    /* 84 = navbar + tags-view = 50 + 34 */
    min-height: calc(100vh - 84px);
  }

  .fixed-header + .app-main {
    margin-top: 84px;
    height: calc(100vh - 84px);
    min-height: 0px;
  }
}

/* 移动端fixed-header优化 */
@media screen and (max-width: 991px) {
  .fixed-header + .app-main {
    padding-bottom: max(60px, calc(constant(safe-area-inset-bottom) + 40px));
    padding-bottom: max(60px, calc(env(safe-area-inset-bottom) + 40px));
    overscroll-behavior-y: none;
  }

  .hasTagsView .fixed-header + .app-main {
    padding-bottom: max(60px, calc(constant(safe-area-inset-bottom) + 40px));
    padding-bottom: max(60px, calc(env(safe-area-inset-bottom) + 40px));
    overscroll-behavior-y: none;
  }
}

@supports (-webkit-touch-callout: none) {
  @media screen and (max-width: 991px) {
    .fixed-header + .app-main {
      padding-bottom: max(17px, calc(constant(safe-area-inset-bottom) + 10px));
      padding-bottom: max(17px, calc(env(safe-area-inset-bottom) + 10px));
      height: calc(100svh - 50px);
      height: calc(100dvh - 50px);
    }

    .hasTagsView .fixed-header + .app-main {
      padding-bottom: max(17px, calc(constant(safe-area-inset-bottom) + 10px));
      padding-bottom: max(17px, calc(env(safe-area-inset-bottom) + 10px));
      height: calc(100svh - 84px);
      height: calc(100dvh - 84px);
    }
  }
}

@keyframes workspaceRise {
  from {
    opacity: 0;
    transform: translate3d(0, 12px, 0);
  }
  to {
    opacity: 1;
    transform: translate3d(0, 0, 0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .app-main :deep(.app-container) {
    animation: none;
  }
}
</style>

<style lang="scss">
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background-color: #f1f1f1;
}

::-webkit-scrollbar-thumb {
  background-color: #c0c0c0;
  border-radius: 3px;
}
</style>
