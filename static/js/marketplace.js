/**
 * EDUTUTOR PRO — INTERACTIVE MOTION & UX SCRIPT
 */

document.addEventListener('DOMContentLoaded', function() {
  
  // ── 1. Scroll-Triggered Entrance Animations (IntersectionObserver) ──
  const animatedElements = document.querySelectorAll('.animate-on-scroll');
  if ('IntersectionObserver' in window && animatedElements.length > 0) {
    const scrollObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, {
      root: null,
      rootMargin: '0px 0px -40px 0px',
      threshold: 0.1
    });

    animatedElements.forEach(el => scrollObserver.observe(el));
  } else {
    // Fallback: immediately show all elements if observer is not supported
    animatedElements.forEach(el => el.classList.add('is-visible'));
  }

  // ── 2. Animated Number Counters (Count-Up Effect) ──
  const counterElements = document.querySelectorAll('[data-counter]');
  if ('IntersectionObserver' in window && counterElements.length > 0) {
    const counterObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const el = entry.target;
          const targetNum = parseInt(el.getAttribute('data-counter'), 10);
          const suffix = el.getAttribute('data-suffix') || '';
          const prefix = el.getAttribute('data-prefix') || '';
          
          if (!isNaN(targetNum)) {
            animateCounter(el, 0, targetNum, 1400, prefix, suffix);
          }
          observer.unobserve(el);
        }
      });
    }, { threshold: 0.2 });

    counterElements.forEach(el => counterObserver.observe(el));
  }

  function animateCounter(el, start, end, duration, prefix, suffix) {
    let startTimestamp = null;
    const step = (timestamp) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      // Ease out cubic function
      const easeProgress = 1 - Math.pow(1 - progress, 3);
      const currentVal = Math.floor(easeProgress * (end - start) + start);
      el.textContent = `${prefix}${currentVal.toLocaleString()}${suffix}`;
      if (progress < 1) {
        window.requestAnimationFrame(step);
      } else {
        el.textContent = `${prefix}${end.toLocaleString()}${suffix}`;
      }
    };
    window.requestAnimationFrame(step);
  }

  // ── 3. Interactive Hero Search Mode Switcher ──
  const modeTabs = document.querySelectorAll('.mode-tab-btn');
  const modeInput = document.getElementById('hero-teaching-mode-input');

  if (modeTabs.length > 0 && modeInput) {
    modeTabs.forEach(tab => {
      tab.addEventListener('click', function(e) {
        e.preventDefault();
        modeTabs.forEach(t => t.classList.remove('active'));
        this.classList.add('active');
        const selectedMode = this.getAttribute('data-mode') || '';
        modeInput.value = selectedMode;
      });
    });
  }

  // ── 4. Interactive How It Works Audience Switcher ──
  const journeyToggles = document.querySelectorAll('[data-journey-toggle]');
  const studentJourney = document.getElementById('journey-students');
  const tutorJourney = document.getElementById('journey-tutors');

  if (journeyToggles.length > 0 && studentJourney && tutorJourney) {
    journeyToggles.forEach(btn => {
      btn.addEventListener('click', function() {
        const target = this.getAttribute('data-journey-toggle');
        journeyToggles.forEach(b => b.classList.remove('btn-primary', 'btn-secondary'));
        journeyToggles.forEach(b => b.classList.add('btn-secondary'));
        this.classList.remove('btn-secondary');
        this.classList.add('btn-primary');

        if (target === 'students') {
          studentJourney.style.display = 'block';
          tutorJourney.style.display = 'none';
        } else {
          studentJourney.style.display = 'none';
          tutorJourney.style.display = 'block';
        }
      });
    });
  }

  // ── 5. Bookmark / Shortlist Favorite Micro-Interaction ──
  document.querySelectorAll('.bookmark-btn').forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      this.classList.toggle('saved');
      const isSaved = this.classList.contains('saved');
      showQuickToast(isSaved ? 'Tutor saved to your shortlist!' : 'Removed from shortlist');
    });
  });

  // ── 6. Toast Notification Helper ──
  function showQuickToast(msg) {
    let toast = document.getElementById('marketplace-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'marketplace-toast';
      toast.style.position = 'fixed';
      toast.style.bottom = '24px';
      toast.style.right = '24px';
      toast.style.background = 'var(--sidebar-bg, #0f172a)';
      toast.style.color = '#ffffff';
      toast.style.padding = '0.75rem 1.25rem';
      toast.style.borderRadius = '9999px';
      toast.style.boxShadow = '0 10px 25px rgba(0,0,0,0.2)';
      toast.style.fontSize = '0.875rem';
      toast.style.fontWeight = '600';
      toast.style.zIndex = '9999';
      toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
      toast.style.transform = 'translateY(20px)';
      toast.style.opacity = '0';
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(20px)';
    }, 2800);
  }

  // ── 7. Automatic dismiss on flash messages after 6s ──
  document.querySelectorAll('.alert').forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      alert.style.opacity = '0';
      alert.style.transform = 'translateY(-8px)';
      setTimeout(() => alert.remove(), 400);
    }, 6000);
  });

  // ── 8. Lucide Icons Refresh ──
  if (typeof lucide !== 'undefined' && lucide.createIcons) {
    lucide.createIcons();
  }
});
