const easingMap = {
  enter: 'cubic-bezier(.16, 1, .3, 1)',
  exit: 'cubic-bezier(.7, 0, .84, 0)',
  pulse: 'cubic-bezier(.45, 0, .55, 1)'
}

export function prefersReducedMotion() {
  return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export function stagger(index, step = 55, start = 0) {
  return start + index * step
}

export function animateTargets(targets, keyframes, options = {}) {
  if (prefersReducedMotion() || typeof Element === 'undefined') {
    return []
  }
  const resolvedTargets = typeof targets === 'string'
    ? document.querySelectorAll(targets)
    : targets
  const nodes = Array.from(resolvedTargets || []).filter(Boolean)
  return nodes
    .filter(node => typeof node.animate === 'function')
    .map((node, index) => node.animate(keyframes, {
      duration: 720,
      easing: easingMap.enter,
      fill: 'both',
      ...options,
      delay: typeof options.delay === 'function' ? options.delay(index) : options.delay
    }))
}

export { easingMap }
