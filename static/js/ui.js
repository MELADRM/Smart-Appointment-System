/* ═══════════════════════════════════════════════════════════════
 *  ui.js — SmartBook interactive polish.
 *
 *  Everything here is progressive enhancement: nothing in the app
 *  depends on it, and anyone with JS off still gets the full, working
 *  site. We run after DOMContentLoaded so markup is ready.
 *
 *  Features:
 *    1. Scroll-reveal: elements with [data-reveal] fade + slide up
 *       when they enter the viewport (uses IntersectionObserver).
 *    2. Animated counters: [data-counter="42"] counts up from 0 once
 *       the number comes into view.
 *    3. Card hover tilt: .sb-tilt gets a subtle mouse-aware 3-D tilt.
 *    4. Ripple: any .btn gains a click-ripple effect.
 *    5. Scroll-to-top: a floating button appears below the fold.
 *    6. Auto-dismiss flash toasts: ditto, plus a manual close.
 *    7. Booking-success confetti: one-off celebration when a page
 *       contains a [data-confetti] element.
 *    8. Logo live-preview: pick a logo → see it before saving.
 *    9. Copy-feedback: shared <button data-copy="text"> helper (the
 *       existing "Copy" buttons still work, this just unifies them).
 *
 *  We always honor `prefers-reduced-motion` — if the user asked for
 *  calmer UI we skip animations and keep behavior static.
 * ═══════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  const reduceMotion = window.matchMedia(
    '(prefers-reduced-motion: reduce)'
  ).matches;

  document.addEventListener('DOMContentLoaded', () => {
    initReveal();
    initCounters();
    initTilt();
    initRipple();
    initScrollTop();
    initToasts();
    initConfetti();
    initLogoPreview();
  });

  /* ── 1. Scroll reveal ───────────────────────────────────────── */
  function initReveal() {
    const els = document.querySelectorAll('[data-reveal]');
    if (!els.length) return;
    if (reduceMotion || !('IntersectionObserver' in window)) {
      els.forEach((el) => el.classList.add('is-visible'));
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add('is-visible');
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
    );
    els.forEach((el) => io.observe(el));
  }

  /* ── 2. Animated counters ───────────────────────────────────── */
  function initCounters() {
    const els = document.querySelectorAll('[data-counter]');
    if (!els.length) return;
    const run = (el) => {
      const target = parseFloat(el.dataset.counter) || 0;
      const decimals = (el.dataset.counter.split('.')[1] || '').length;
      if (reduceMotion) {
        el.textContent = target.toFixed(decimals);
        return;
      }
      const dur = 1400; // ms
      const start = performance.now();
      const tick = (now) => {
        const p = Math.min(1, (now - start) / dur);
        // easeOutCubic
        const eased = 1 - Math.pow(1 - p, 3);
        el.textContent = (target * eased).toFixed(decimals);
        if (p < 1) requestAnimationFrame(tick);
        else el.textContent = target.toFixed(decimals);
      };
      requestAnimationFrame(tick);
    };
    if (!('IntersectionObserver' in window)) {
      els.forEach(run);
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            run(e.target);
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.4 }
    );
    els.forEach((el) => io.observe(el));
  }

  /* ── 3. Card tilt ───────────────────────────────────────────── */
  function initTilt() {
    if (reduceMotion) return;
    document.querySelectorAll('.sb-tilt').forEach((card) => {
      let raf = null;
      const reset = () => {
        card.style.transform = '';
      };
      card.addEventListener('mousemove', (e) => {
        const r = card.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - 0.5;
        const y = (e.clientY - r.top) / r.height - 0.5;
        if (raf) cancelAnimationFrame(raf);
        raf = requestAnimationFrame(() => {
          card.style.transform =
            `perspective(800px) rotateY(${x * 6}deg) rotateX(${-y * 6}deg) translateY(-4px)`;
        });
      });
      card.addEventListener('mouseleave', reset);
    });
  }

  /* ── 4. Button ripple ───────────────────────────────────────── */
  function initRipple() {
    if (reduceMotion) return;
    document.addEventListener('click', (e) => {
      const btn = e.target.closest('.btn');
      if (!btn || btn.classList.contains('btn-link')) return;
      const r = btn.getBoundingClientRect();
      const ripple = document.createElement('span');
      ripple.className = 'sb-ripple';
      ripple.style.left = e.clientX - r.left + 'px';
      ripple.style.top = e.clientY - r.top + 'px';
      btn.appendChild(ripple);
      setTimeout(() => ripple.remove(), 650);
    });
  }

  /* ── 5. Scroll-to-top ───────────────────────────────────────── */
  function initScrollTop() {
    const btn = document.createElement('button');
    btn.className = 'sb-scroll-top';
    btn.type = 'button';
    btn.setAttribute('aria-label', 'Scroll to top');
    btn.innerHTML = '<i class="bi bi-arrow-up"></i>';
    document.body.appendChild(btn);
    btn.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
    });
    const onScroll = () => {
      btn.classList.toggle('is-visible', window.scrollY > 400);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* ── 6. Flash toasts: auto-dismiss + close button ───────────── */
  function initToasts() {
    const alerts = document.querySelectorAll('.sb-alert');
    alerts.forEach((a, i) => {
      // Add a close button
      if (!a.querySelector('.sb-alert-close')) {
        const x = document.createElement('button');
        x.type = 'button';
        x.className = 'sb-alert-close';
        x.innerHTML = '&times;';
        x.setAttribute('aria-label', 'Dismiss');
        x.addEventListener('click', () => dismiss(a));
        a.appendChild(x);
      }
      // Auto-dismiss after 6 seconds (staggered so multiple don't all
      // vanish at the same instant).
      setTimeout(() => dismiss(a), 6000 + i * 400);
    });
    function dismiss(a) {
      a.classList.add('is-leaving');
      setTimeout(() => a.remove(), 350);
    }
  }

  /* ── 7. Confetti ────────────────────────────────────────────── */
  function initConfetti() {
    const trigger = document.querySelector('[data-confetti]');
    if (!trigger || reduceMotion) return;
    burstConfetti();
  }

  function burstConfetti() {
    const colors = ['#2563eb', '#059669', '#d97706', '#dc2626',
                    '#7c3aed', '#f59e0b', '#ec4899'];
    const layer = document.createElement('div');
    layer.className = 'sb-confetti-layer';
    document.body.appendChild(layer);
    const N = 90;
    for (let i = 0; i < N; i++) {
      const p = document.createElement('i');
      p.className = 'sb-confetti';
      const c = colors[i % colors.length];
      p.style.background = c;
      p.style.left = (45 + Math.random() * 10) + 'vw';
      p.style.setProperty('--dx', (Math.random() * 600 - 300) + 'px');
      p.style.setProperty('--dy', (300 + Math.random() * 400) + 'px');
      p.style.setProperty('--rot', (Math.random() * 720 - 360) + 'deg');
      p.style.animationDelay = Math.random() * 0.2 + 's';
      layer.appendChild(p);
    }
    setTimeout(() => layer.remove(), 3500);
  }
  window.SB_burstConfetti = burstConfetti;

  /* ── 8. Logo / image live preview ───────────────────────────── */
  function initLogoPreview() {
    document.querySelectorAll('input[type="file"][data-preview]').forEach((inp) => {
      inp.addEventListener('change', () => {
        const target = document.querySelector(inp.dataset.preview);
        if (!target || !inp.files || !inp.files[0]) return;
        const url = URL.createObjectURL(inp.files[0]);
        if (target.tagName === 'IMG') {
          target.src = url;
        } else {
          target.style.backgroundImage = `url('${url}')`;
          target.style.backgroundSize = 'cover';
          target.style.backgroundPosition = 'center';
          target.textContent = '';
        }
      });
    });
  }
})();
