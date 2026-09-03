<template>
  <div class="login-page">
    <div class="motion-scene" aria-hidden="true">
      <span class="soft-orb orb-one"></span>
      <span class="soft-orb orb-two"></span>
      <span class="soft-orb orb-three"></span>
      <span class="dot-field"></span>
      <span class="shape shape-a"></span>
      <span class="shape shape-b"></span>
      <span class="shape shape-c"></span>
    </div>

    <main class="login-wrap">
      <section class="hero-panel">
        <div class="brand-line">
          <span class="brand-mark">AI</span>
          <span>Trading Workspace</span>
        </div>

        <div class="hero-copy">
          <p class="hero-kicker">Signal · Decision · Execution</p>
          <h3>让交易系统保持清醒、有序、可追踪</h3>
          <p class="hero-desc">
            面向 AI 辅助交易的轻量控制台，聚合行情状态、决策记录、风险阻断与执行链路。
          </p>
        </div>

        <div class="status-strip">
          <div class="status-item">
            <span>Market</span>
            <strong>Fresh</strong>
          </div>
          <div class="status-item">
            <span>Agent</span>
            <strong>Ready</strong>
          </div>
          <div class="status-item">
            <span>Risk</span>
            <strong>Guarded</strong>
          </div>
        </div>
      </section>

      <section class="login-card">
        <transition name="auth-loading-fade">
          <div v-if="loading" class="auth-loading-overlay" aria-live="polite">
            <span class="loading-dots">
              <i></i>
              <i></i>
              <i></i>
            </span>
            <strong>正在验证</strong>
            <em>正在打开交易工作台...</em>
          </div>
        </transition>

        <div class="card-heading">
          <span>Secure Login</span>
          <h2>欢迎回来</h2>
          <p>使用授权账号继续访问控制台</p>
        </div>

        <el-form ref="loginRef" :model="loginForm" :rules="loginRules" class="login-form">
          <el-form-item prop="username" class="form-row">
            <label class="field-shell">
              <span class="field-label">账号</span>
              <el-input
                v-model="loginForm.username"
                type="text"
                size="large"
                auto-complete="off"
                placeholder="请输入账号"
                class="fresh-input"
              >
                <template #prefix>
                  <svg-icon icon-class="user" class="input-icon" />
                </template>
              </el-input>
            </label>
          </el-form-item>

          <el-form-item prop="password" class="form-row">
            <label class="field-shell">
              <span class="field-label">密码</span>
              <el-input
                v-model="loginForm.password"
                type="password"
                size="large"
                auto-complete="off"
                placeholder="请输入密码"
                class="fresh-input"
                @keyup.enter="handleLogin"
              >
                <template #prefix>
                  <svg-icon icon-class="password" class="input-icon" />
                </template>
              </el-input>
            </label>
          </el-form-item>

          <template v-if="captchaEnabled">
            <el-form-item prop="code" class="form-row captcha-row">
              <label class="field-shell">
                <span class="field-label">验证码</span>
                <el-input
                  v-model="loginForm.code"
                  size="large"
                  auto-complete="off"
                  placeholder="请输入验证码"
                  class="fresh-input"
                  @keyup.enter="handleLogin"
                >
                  <template #prefix>
                    <svg-icon icon-class="validCode" class="input-icon" />
                  </template>
                </el-input>
              </label>
              <button type="button" class="captcha-card" @click="getCode">
                <img :src="codeUrl" class="captcha-img" alt="captcha" />
              </button>
            </el-form-item>
          </template>

          <div class="form-meta">
            <el-checkbox v-model="loginForm.rememberMe" class="remember-check">记住密码</el-checkbox>
            <span class="meta-pill">验证码{{ captchaEnabled ? '开启' : '关闭' }}</span>
          </div>

          <el-form-item class="submit-row">
            <el-button
              :loading="loading"
              size="large"
              type="primary"
              class="submit-button"
              @click.prevent="handleLogin"
            >
              <span v-if="!loading">进入控制台</span>
              <span v-else>验证中...</span>
            </el-button>
          </el-form-item>

          <div class="card-footer">
            <span>仅授权人员可访问</span>
            <router-link v-if="register" :to="'/register'">创建账号</router-link>
          </div>
        </el-form>
      </section>
    </main>

    <footer class="login-footer">{{ footerContent }}</footer>
  </div>
</template>

<script setup>
import { ElMessage } from "element-plus"
import { getCodeImg } from "@/api/login"
import Cookies from "js-cookie"
import { encrypt, decrypt } from "@/utils/jsencrypt"
import useUserStore from '@/store/modules/user'
import defaultSettings from '@/settings'
import { animateTargets, stagger } from '@/utils/motion'

const footerContent = defaultSettings.footerContent
const userStore = useUserStore()
const route = useRoute()
const router = useRouter()
const { proxy } = getCurrentInstance()

const loginForm = ref({
  username: "",
  password: "",
  rememberMe: false,
  code: "",
  uuid: ""
})

const loginRules = {
  username: [{ required: true, trigger: "blur", message: "请输入您的账号" }],
  password: [{ required: true, trigger: "blur", message: "请输入您的密码" }],
  code: [{ required: true, trigger: "change", message: "请输入验证码" }]
}

const codeUrl = ref("")
const loading = ref(false)
const captchaEnabled = ref(true)
const register = ref(false)
const redirect = ref(undefined)

watch(route, (newRoute) => {
  redirect.value = newRoute.query && newRoute.query.redirect
}, { immediate: true })

function handleLogin() {
  proxy.$refs.loginRef.validate(valid => {
    if (valid) {
      loading.value = true
      if (loginForm.value.rememberMe) {
        Cookies.set("username", loginForm.value.username, { expires: 30 })
        Cookies.set("password", encrypt(loginForm.value.password), { expires: 30 })
        Cookies.set("rememberMe", loginForm.value.rememberMe, { expires: 30 })
      } else {
        Cookies.remove("username")
        Cookies.remove("password")
        Cookies.remove("rememberMe")
      }
      userStore.login(loginForm.value).then(() => {
        const query = route.query
        const otherQueryParams = Object.keys(query).reduce((acc, cur) => {
          if (cur !== "redirect") {
            acc[cur] = query[cur]
          }
          return acc
        }, {})
        // router.push resolves once the guard settles. If route generation
        // fails the guard rejects, and without this the overlay would sit on
        // "正在验证" forever with no error shown.
        return router.push({ path: redirect.value || "/", query: otherQueryParams })
          .catch(err => {
            loading.value = false
            const message = err && err.message ? err.message : "打开工作台失败"
            ElMessage.error(`登录成功但工作台加载失败：${message}`)
            if (captchaEnabled.value) {
              getCode()
            }
          })
      }).catch(() => {
        loading.value = false
        if (captchaEnabled.value) {
          getCode()
        }
      })
    }
  })
}

function getCode() {
  getCodeImg().then(res => {
    captchaEnabled.value = res.captchaEnabled === undefined ? true : res.captchaEnabled
    if (captchaEnabled.value) {
      codeUrl.value = "data:image/gif;base64," + res.img
      loginForm.value.uuid = res.uuid
    }
  })
}

function getCookie() {
  const username = Cookies.get("username")
  const password = Cookies.get("password")
  const rememberMe = Cookies.get("rememberMe")
  loginForm.value = {
    username: username === undefined ? loginForm.value.username : username,
    password: password === undefined ? loginForm.value.password : decrypt(password),
    rememberMe: rememberMe === undefined ? false : Boolean(rememberMe)
  }
}

getCode()
getCookie()

onMounted(() => {
  nextTick(() => {
    animateTargets(
      '.login-page .brand-line, .login-page .hero-copy, .login-page .status-item, .login-page .login-card, .login-page .form-row, .login-page .form-meta, .login-page .submit-row, .login-page .card-footer',
      [
        { opacity: 0, transform: 'translate3d(0, 18px, 0) scale(.985)' },
        { opacity: 1, transform: 'translate3d(0, 0, 0) scale(1)' }
      ],
      { duration: 720, delay: index => stagger(index, 38, 60) }
    )
  })
})
</script>

<style lang='scss' scoped>
.login-page {
  --page-bg: #f7f4ec;
  --page-bg-2: #edf7f3;
  --ink: #20313b;
  --muted: #6a7b82;
  --card: rgba(255, 255, 255, 0.76);
  --line: rgba(43, 61, 70, 0.1);
  --mint: #76d7bd;
  --mint-dark: #279c81;
  --sky: #79c8f2;
  --peach: #ffb38a;
  --lavender: #b9a8ff;
  --shadow: 0 28px 80px rgba(54, 70, 74, 0.14);
  min-height: 100vh;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(18px, 4vw, 52px);
  background:
    radial-gradient(circle at 14% 16%, rgba(255, 179, 138, 0.34), transparent 26%),
    radial-gradient(circle at 84% 12%, rgba(121, 200, 242, 0.32), transparent 24%),
    linear-gradient(135deg, var(--page-bg), var(--page-bg-2));
  color: var(--ink);
  font-family: "Inter", "PingFang SC", "Microsoft YaHei", sans-serif;
}

.login-page,
.login-page * {
  box-sizing: border-box;
}

.motion-scene,
.motion-scene span {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.soft-orb {
  width: 360px;
  height: 360px;
  border-radius: 999px;
  filter: blur(20px);
  opacity: 0.46;
  animation: orbFloat 13s ease-in-out infinite;
}

.orb-one {
  inset: -120px auto auto -110px !important;
  background: var(--peach);
}

.orb-two {
  inset: auto -120px 8% auto !important;
  background: var(--sky);
  animation-delay: -5s;
}

.orb-three {
  inset: 50% auto auto 42% !important;
  width: 240px;
  height: 240px;
  background: var(--mint);
  animation-delay: -8s;
}

.dot-field {
  opacity: 0.58;
  background-image: radial-gradient(rgba(32, 49, 59, 0.18) 1px, transparent 1px);
  background-size: 24px 24px;
  mask-image: radial-gradient(circle at center, #000, transparent 78%);
  animation: dotsSlide 22s linear infinite;
}

.shape {
  width: 62px;
  height: 62px;
  border-radius: 22px;
  border: 1px solid rgba(32, 49, 59, 0.08);
  background: rgba(255, 255, 255, 0.45);
  box-shadow: 0 16px 42px rgba(52, 67, 75, 0.08);
  animation: shapeDrift 9s ease-in-out infinite;
}

.shape-a {
  inset: 18% auto auto 8% !important;
  transform: rotate(12deg);
}

.shape-b {
  inset: auto 10% 18% auto !important;
  width: 78px;
  height: 78px;
  border-radius: 999px;
  animation-delay: -3s;
}

.shape-c {
  inset: 12% 22% auto auto !important;
  width: 44px;
  height: 44px;
  animation-delay: -6s;
}

.login-wrap {
  min-width: 0;
  position: relative;
  z-index: 1;
  width: min(1040px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 0.95fr) minmax(360px, 420px);
  gap: clamp(22px, 4vw, 54px);
  align-items: center;
}

.hero-panel {
  min-height: 560px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 54px;
}

.brand-line {
  width: fit-content;
  display: inline-flex;
  align-items: center;
  gap: 12px;
  padding: 9px 14px 9px 9px;
  border-radius: 999px;
  color: rgba(32, 49, 59, 0.72);
  background: rgba(255, 255, 255, 0.52);
  border: 1px solid rgba(255, 255, 255, 0.68);
  box-shadow: 0 14px 42px rgba(52, 67, 75, 0.08);
  font-size: 13px;
  font-weight: 700;
}

.brand-mark {
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: #fff;
  background: linear-gradient(135deg, var(--mint-dark), #56b7e6);
  letter-spacing: 0.04em;
}

.hero-kicker {
  margin: 0 0 18px;
  color: var(--mint-dark);
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.hero-copy h1 {
  max-width: 660px;
  margin: 0;
  font-size: clamp(42px, 5vw, 68px);
  line-height: 1.02;
  letter-spacing: -0.06em;
}

.hero-desc {
  max-width: 560px;
  margin: 24px 0 0;
  color: var(--muted);
  font-size: 16px;
  line-height: 1.9;
}

.status-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  max-width: 620px;
}

.status-item {
  padding: 18px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.48);
  border: 1px solid rgba(255, 255, 255, 0.64);
  box-shadow: 0 18px 52px rgba(52, 67, 75, 0.08);
  transition: transform 0.28s cubic-bezier(.16, 1, .3, 1), box-shadow 0.28s ease;
}

.status-item:hover {
  transform: translateY(-5px);
  box-shadow: 0 24px 62px rgba(52, 67, 75, 0.12);
}

.status-item span {
  display: block;
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 10px;
}

.status-item strong {
  font-size: 18px;
  color: var(--ink);
}

.login-card {
  position: relative;
  overflow: hidden;
  padding: clamp(26px, 4vw, 38px);
  border-radius: 34px;
  background: var(--card);
  border: 1px solid rgba(255, 255, 255, 0.76);
  box-shadow: var(--shadow);
  backdrop-filter: blur(22px);
}

.login-card::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.78), transparent 34%),
    radial-gradient(circle at 100% 0%, rgba(118, 215, 189, 0.2), transparent 30%);
  pointer-events: none;
}

.card-heading,
.login-form {
  position: relative;
  z-index: 1;
}

.card-heading {
  margin-bottom: 28px;
}

.card-heading span {
  color: var(--mint-dark);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.card-heading h2 {
  margin: 12px 0 8px;
  font-size: 32px;
  line-height: 1.1;
  letter-spacing: -0.04em;
}

.card-heading p {
  margin: 0;
  color: var(--muted);
  font-size: 14px;
}

.form-row {
  margin-bottom: 18px;
}

.field-shell {
  display: block;
  width: 100%;
  min-width: 0;
}

.field-label {
  display: block;
  margin: 0 0 8px 3px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 700;
}

.fresh-input :deep(.el-input__wrapper) {
  height: 54px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.76);
  border: 1px solid rgba(32, 49, 59, 0.08);
  box-shadow: none;
  transition: transform 0.24s cubic-bezier(.16, 1, .3, 1), border-color 0.24s ease, background 0.24s ease, box-shadow 0.24s ease;
}

.fresh-input :deep(.el-input__wrapper:hover),
.fresh-input :deep(.el-input__wrapper.is-focus) {
  transform: translateY(-2px);
  background: #fff;
  border-color: rgba(39, 156, 129, 0.35);
  box-shadow: 0 16px 36px rgba(39, 156, 129, 0.12);
}

.fresh-input :deep(.el-input__inner) {
  color: var(--ink);
  font-size: 14px;
}

.input-icon {
  width: 16px;
  height: 16px;
  color: var(--mint-dark);
}

.captcha-row :deep(.el-form-item__content) {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 124px;
  gap: 12px;
}

.captcha-card {
  align-self: end;
  height: 54px;
  padding: 0;
  border: 1px solid rgba(32, 49, 59, 0.08);
  border-radius: 18px;
  overflow: hidden;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.7);
  transition: transform 0.24s cubic-bezier(.16, 1, .3, 1), box-shadow 0.24s ease;
}

.captcha-card:hover {
  transform: translateY(-2px) scale(1.01);
  box-shadow: 0 14px 34px rgba(52, 67, 75, 0.12);
}

.captcha-img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.form-meta,
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.form-meta {
  margin: 2px 0 22px;
}

.remember-check :deep(.el-checkbox__label) {
  color: var(--muted);
  font-size: 13px;
}

.meta-pill {
  padding: 7px 10px;
  border-radius: 999px;
  color: var(--mint-dark);
  background: rgba(118, 215, 189, 0.16);
  font-size: 12px;
  font-weight: 700;
}

.submit-row {
  margin-bottom: 0;
}

.submit-row :deep(.el-form-item__content) {
  width: 100%;
}

.submit-button {
  width: 100%;
  min-height: 56px;
  position: relative;
  overflow: hidden;
  border: 0;
  border-radius: 18px;
  color: #fff;
  background: linear-gradient(135deg, #2aa88d, #62c8d8 62%, #8b7cf6);
  box-shadow: 0 20px 42px rgba(42, 168, 141, 0.22);
  font-weight: 800;
  letter-spacing: 0.08em;
  transition: transform 0.24s cubic-bezier(.16, 1, .3, 1), box-shadow 0.24s ease, filter 0.24s ease;
}

.submit-button:hover {
  transform: translateY(-2px);
  filter: saturate(1.08);
  box-shadow: 0 26px 54px rgba(42, 168, 141, 0.28);
}

.submit-button::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(110deg, transparent 0%, rgba(255, 255, 255, 0.28) 44%, transparent 62%);
  transform: translateX(-120%);
  transition: transform 0.72s cubic-bezier(.16, 1, .3, 1);
}

.submit-button:hover::after {
  transform: translateX(120%);
}

.submit-button span {
  position: relative;
  z-index: 1;
}

.card-footer {
  margin-top: 18px;
  color: var(--muted);
  font-size: 12px;
}

.card-footer a {
  color: var(--mint-dark);
  text-decoration: none;
  font-weight: 800;
}

.auth-loading-overlay {
  position: absolute;
  inset: 0;
  z-index: 4;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--ink);
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(18px);
}

.loading-dots {
  display: flex;
  gap: 8px;
}

.loading-dots i {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--mint-dark);
  animation: dotJump 0.86s ease-in-out infinite;
}

.loading-dots i:nth-child(2) {
  background: var(--sky);
  animation-delay: 0.12s;
}

.loading-dots i:nth-child(3) {
  background: var(--lavender);
  animation-delay: 0.24s;
}

.auth-loading-overlay em {
  color: var(--muted);
  font-size: 13px;
  font-style: normal;
}

.auth-loading-fade-enter-active,
.auth-loading-fade-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}

.auth-loading-fade-enter-from,
.auth-loading-fade-leave-to {
  opacity: 0;
  transform: scale(0.98);
}

.login-footer {
  position: absolute;
  left: 50%;
  bottom: 18px;
  transform: translateX(-50%);
  z-index: 1;
  width: min(90vw, 760px);
  color: rgba(32, 49, 59, 0.44);
  font-size: 12px;
  text-align: center;
}

@keyframes orbFloat {
  0%, 100% {
    transform: translate3d(0, 0, 0) scale(1);
  }
  50% {
    transform: translate3d(28px, 18px, 0) scale(1.06);
  }
}

@keyframes dotsSlide {
  to {
    transform: translate3d(24px, 24px, 0);
  }
}

@keyframes shapeDrift {
  0%, 100% {
    transform: translate3d(0, 0, 0) rotate(12deg);
  }
  50% {
    transform: translate3d(12px, -18px, 0) rotate(22deg);
  }
}

@keyframes dotJump {
  0%, 100% {
    transform: translateY(0) scale(0.92);
    opacity: 0.58;
  }
  50% {
    transform: translateY(-9px) scale(1);
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .soft-orb,
  .dot-field,
  .shape,
  .loading-dots i {
    animation: none;
  }
}

@media (max-width: 980px) {
  .login-page {
    min-height: 100dvh;
    align-items: flex-start;
    overflow-x: hidden;
    overflow-y: auto;
    padding: 22px;
  }

  .login-wrap {
    width: min(560px, 100%);
    grid-template-columns: 1fr;
    gap: 20px;
  }

  .hero-panel {
    min-height: auto;
    gap: 24px;
    padding-top: 8px;
  }

  .hero-copy h1 {
    max-width: 520px;
    font-size: clamp(34px, 8vw, 52px);
    line-height: 1.08;
    letter-spacing: -0.045em;
  }

  .hero-desc {
    max-width: 520px;
    margin-top: 16px;
    font-size: 15px;
    line-height: 1.75;
  }

  .status-strip {
    max-width: none;
  }

  .soft-orb {
    width: 300px;
    height: 300px;
  }

  .shape-b {
    display: none;
  }
}

@media (max-width: 640px) {
  .login-page {
    display: block;
    min-height: 100dvh;
    padding: max(12px, env(safe-area-inset-top)) 12px max(12px, env(safe-area-inset-bottom));
    overflow-x: hidden;
    overflow-y: auto;
  }

  .login-wrap {
    width: 100%;
    min-height: calc(100dvh - 24px);
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 12px;
  }

  .hero-panel {
    min-height: 0;
    display: block;
    padding: 0;
  }

  .brand-line {
    max-width: 100%;
    margin: 0 auto 10px;
    gap: 8px;
    padding: 7px 11px 7px 7px;
    font-size: 12px;
    background: rgba(255, 255, 255, 0.68);
  }

  .brand-mark {
    width: 28px;
    height: 28px;
    font-size: 12px;
  }

  .hero-copy {
    text-align: center;
  }

  .hero-kicker,
  .hero-desc,
  .status-strip {
    display: none;
  }

  .hero-copy h1 {
    max-width: 320px;
    margin: 0 auto;
    font-size: clamp(21px, 6.2vw, 28px);
    line-height: 1.24;
    letter-spacing: -0.035em;
  }

  .login-card {
    width: 100%;
    max-width: 430px;
    margin: 0 auto;
    border-radius: 22px;
    padding: 18px;
    background: rgba(255, 255, 255, 0.84);
  }

  .card-heading {
    margin-bottom: 18px;
  }

  .card-heading span {
    font-size: 11px;
  }

  .card-heading h2 {
    margin: 7px 0 6px;
    font-size: 25px;
  }

  .card-heading p {
    font-size: 13px;
  }

  .form-row {
    margin-bottom: 13px;
  }

  .field-label {
    margin-bottom: 6px;
    font-size: 12px;
  }

  .fresh-input :deep(.el-input__wrapper) {
    height: 48px;
    border-radius: 15px;
  }

  .captcha-row :deep(.el-form-item__content) {
    grid-template-columns: minmax(0, 1fr) 104px;
    gap: 9px;
  }

  .captcha-card {
    width: auto;
    height: 48px;
    border-radius: 15px;
  }

  .form-meta,
  .card-footer {
    flex-direction: row;
    align-items: center;
  }

  .form-meta {
    margin: 0 0 16px;
  }

  .remember-check :deep(.el-checkbox__label) {
    font-size: 12px;
  }

  .meta-pill {
    padding: 5px 8px;
    font-size: 11px;
    white-space: nowrap;
  }

  .submit-button {
    min-height: 50px;
    border-radius: 15px;
  }

  .card-footer {
    margin-top: 14px;
    font-size: 11px;
  }

  .login-footer {
    position: static;
    width: 100%;
    margin-top: 10px;
    transform: none;
    color: rgba(32, 49, 59, 0.36);
    font-size: 10px;
  }

  .soft-orb {
    width: 260px;
    height: 260px;
  }

  .orb-one {
    inset: -150px auto auto -150px !important;
  }

  .orb-two {
    inset: auto -150px -120px auto !important;
  }

  .orb-three,
  .shape-a,
  .shape-b,
  .shape-c {
    display: none;
  }
}

@media (max-width: 420px) {
  .login-page {
    padding-inline: 10px;
  }

  .login-wrap {
    min-height: calc(100dvh - 20px);
    justify-content: center;
  }

  .hero-copy {
    display: none;
  }

  .brand-line {
    margin-bottom: 8px;
  }

  .login-card {
    padding: 16px;
    border-radius: 20px;
  }

  .captcha-row :deep(.el-form-item__content) {
    grid-template-columns: 1fr;
  }

  .captcha-card {
    width: 100%;
  }

  .form-meta,
  .card-footer {
    align-items: flex-start;
    flex-direction: column;
    gap: 7px;
  }
}

@media (max-width: 360px) {
  .brand-line {
    justify-content: center;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .login-card {
    padding: 14px;
  }

  .card-heading h2 {
    font-size: 23px;
  }

  .fresh-input :deep(.el-input__wrapper),
  .captcha-card {
    height: 46px;
  }
}

@media (max-height: 680px) and (max-width: 640px) {
  .login-wrap {
    justify-content: flex-start;
  }

  .hero-panel {
    margin-top: 4px;
  }

  .card-heading {
    margin-bottom: 14px;
  }

  .form-row {
    margin-bottom: 10px;
  }

  .login-card {
    padding-block: 14px;
  }
}

</style>
