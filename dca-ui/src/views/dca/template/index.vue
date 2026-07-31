<template>
  <div class="app-container legacy-retired-page">
    <el-alert :title="retiredMessage" type="warning" :closable="false" show-icon />

    <el-card class="retired-card" shadow="never">
      <template #header>
        <div class="retired-header">
          <span>{{ pageTitle }}</span>
        </div>
      </template>

      <p class="retired-description">
        {{ pageDescription }}
      </p>

      <ul class="retired-guides">
        <li v-for="item in guidanceItems" :key="item">{{ item }}</li>
      </ul>

      <div class="retired-links">
        <router-link
          v-for="item in shortcutItems"
          :key="item.path"
          :to="item.path"
          class="retired-link"
        >
          <el-button type="primary" plain>{{ item.label }}</el-button>
        </router-link>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import {
  createLegacyTemplateConsoleLinks,
  createLegacyTemplateGuidance,
  pageDescription,
  pageTitle,
  retiredMessage
} from './legacyTemplateRetirement'

const shortcutItems = createLegacyTemplateConsoleLinks()
const guidanceItems = createLegacyTemplateGuidance()
</script>

<style scoped>
.legacy-retired-page {
  display: grid;
  gap: 16px;
}

.retired-card {
  border: 1px solid #f3d19e;
  background: linear-gradient(180deg, #fffaf0 0%, #ffffff 100%);
}

.retired-header {
  font-size: 16px;
  font-weight: 600;
  color: #7c4a03;
}

.retired-description {
  margin: 0 0 16px;
  color: #6b7280;
  line-height: 1.7;
}

.retired-guides {
  margin: 0 0 16px;
  padding-left: 18px;
  color: #6b7280;
  line-height: 1.8;
}

.retired-links {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.retired-link {
  text-decoration: none;
}
</style>
