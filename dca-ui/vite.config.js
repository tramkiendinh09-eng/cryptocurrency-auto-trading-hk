import { defineConfig, loadEnv } from 'vite'
import path from 'path'
import createVitePlugins from './vite/plugins'

const baseUrl = 'http://localhost:8080' // 后端接口

// https://vitejs.dev/config/
export default defineConfig(({ mode, command }) => {
  const env = loadEnv(mode, process.cwd())
  const { VITE_APP_ENV } = env
  return {
    // 部署生产环境和开发环境下的URL。
    // 默认情况下，vite 会假设你的应用是被部署在一个域名的根路径上
    // 例如 https://www.ruoyi.vip/。如果应用被部署在一个子路径上，你就需要用这个选项指定这个子路径。例如，如果你的应用被部署在 https://www.ruoyi.vip/admin/，则设置 baseUrl 为 /admin/。
    base: VITE_APP_ENV === 'production' ? '/' : '/',
    plugins: createVitePlugins(env, command === 'build'),
    resolve: {
      // https://cn.vitejs.dev/config/#resolve-alias
      alias: {
        // 设置路径
        '~': path.resolve(__dirname, './'),
        // 设置别名
        '@': path.resolve(__dirname, './src')
      },
      // https://cn.vitejs.dev/config/#resolve-extensions
      extensions: ['.mjs', '.js', '.ts', '.jsx', '.tsx', '.json', '.vue']
    },
    // 打包配置
    build: {
      // https://vite.dev/config/build-options.html
      sourcemap: command === 'build' ? false : 'inline',
      outDir: 'dist',
      assetsDir: 'assets',
      // 阈值从 2000 收紧到 700：拆分后入口应当明显低于这个线，
      // 再超过就说明又有大依赖被塞回首屏了，构建时就该报出来。
      chunkSizeWarningLimit: 700,
      rollupOptions: {
        output: {
          chunkFileNames: 'static/js/[name]-[hash].js',
          entryFileNames: 'static/js/[name]-[hash].js',
          assetFileNames: 'static/[ext]/[name]-[hash].[ext]',
          /* 默认所有依赖都跟业务代码打成一个 1.5MB 的整块：改一行业务代码
             哈希就变，用户每次发版都要把 Element Plus 和 Vue 运行时重下一遍。
             把这几个框架级依赖单独拎出来，版本锁在 package.json 里、几乎不动，
             哈希稳定，跨版本发布能一直命中浏览器缓存。

             注意必须是「一个」chunk，不能按 vue / element-plus 再拆细：
             element-plus 与 Vue 运行时之间存在跨模块的循环引用，拆成两块之后
             Rollup 生成的求值顺序会让 element-plus 在 vendor-vue 初始化完成前
             就去取它的绑定，页面直接白屏在
             ReferenceError: Cannot access 'Y' before initialization。
             合成一块就没有跨 chunk 的边，问题自然不存在。 */
          manualChunks(id) {
            if (!id.includes('node_modules')) return
            if (/[\\/]node_modules[\\/](element-plus|@element-plus|vue|vue-router|pinia|@vue)[\\/]/.test(id)) {
              return 'vendor'
            }
          }
        }
      }
    },
    // vite 相关配置
    server: {
      port: 80,
      host: true,
      open: true,
      proxy: {
        // https://cn.vitejs.dev/config/#server-proxy
        '/dev-api': {
          target: baseUrl,
          changeOrigin: true,
          rewrite: (p) => p.replace(/^\/dev-api/, '')
        },
         // springdoc proxy
         '^/v3/api-docs/(.*)': {
          target: baseUrl,
          changeOrigin: true,
        }
      }
    },
    css: {
      postcss: {
        plugins: [
          {
            postcssPlugin: 'internal:charset-removal',
            AtRule: {
              charset: (atRule) => {
                if (atRule.name === 'charset') {
                  atRule.remove()
                }
              }
            }
          }
        ]
      }
    },
    test: {
      environment: 'jsdom'
    }
  }
})
