import router from './router'
import { ElMessage } from 'element-plus'
import { getToken } from '@/utils/auth'
import { isHttp, isPathMatch } from '@/utils/validate'
import { isRelogin } from '@/utils/request'
import useUserStore from '@/store/modules/user'
import useLockStore from '@/store/modules/lock'
import useSettingsStore from '@/store/modules/settings'
import usePermissionStore from '@/store/modules/permission'
import { hideRouteLoading, showRouteLoading } from '@/utils/routeLoading'

const whiteList = ['/login', '/register']

const isWhiteList = (path) => {
  return whiteList.some(pattern => isPathMatch(pattern, path))
}

router.beforeEach((to, from, next) => {
  showRouteLoading()
  if (getToken()) {
    to.meta.title && useSettingsStore().setTitle(to.meta.title)
    const isLock = useLockStore().isLock
    /* has token*/
    if (to.path === '/login') {
      next({ path: '/' })
    } else if (isWhiteList(to.path)) {
      next()
    } else if (isLock && to.path !== '/lock') {
      next({ path: '/lock' })
    } else if (!isLock && to.path === '/lock') {
      next({ path: '/' })
    } else {
      if (useUserStore().roles.length === 0) {
        isRelogin.show = true
        // The inner generateRoutes() promise must be returned. Without it a
        // rejection there escapes this catch, next() is never called, and the
        // navigation hangs forever — leaving RouteLoading's overlay up with no
        // way out, which looks exactly like a frozen "Loading workspace" screen.
        useUserStore().getInfo().then(() => {
          isRelogin.show = false
          return usePermissionStore().generateRoutes().then(accessRoutes => {
            accessRoutes.forEach(route => {
              if (!isHttp(route.path)) {
                router.addRoute(route)
              }
            })
            next({ ...to, replace: true })
          })
        }).catch(err => {
          isRelogin.show = false
          hideRouteLoading()
          useUserStore().logOut().then(() => {
            ElMessage.error(err)
            next({ path: '/login' })
          }).catch(() => {
            // Even a failing logout must not strand the user on the overlay.
            next({ path: '/login' })
          })
        })
      } else {
        next()
      }
    }
  } else {
    if (isWhiteList(to.path)) {
      next()
    } else {
      next(`/login?redirect=${to.fullPath}`)
    }
  }
})

router.afterEach(() => {
  hideRouteLoading()
})

router.onError(() => {
  hideRouteLoading()
})