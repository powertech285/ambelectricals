// Shared site interactions
window.addEventListener('load', () => {
  const loadingScreen = document.getElementById('loadingScreen');
  if (loadingScreen) {
    loadingScreen.classList.add('hide');
    setTimeout(() => loadingScreen.remove(), 500);
  }

  AOS.init({ duration: 800, once: true, offset: 80 });

  const typedElement = document.getElementById('typedText');
  if (typedElement) {
    new Typed('#typedText', {
      strings: ['reliable power systems.', 'safe electrical solutions.', 'modern engineering excellence.'],
      typeSpeed: 80,
      backSpeed: 50,
      backDelay: 1200,
      loop: true,
    });
  }

  const counters = document.querySelectorAll('.counter');
  counters.forEach((counter) => {
    const target = Number(counter.getAttribute('data-target'));
    const duration = 1400;
    const startTime = performance.now();

    const animate = (currentTime) => {
      const progress = Math.min((currentTime - startTime) / duration, 1);
      const value = Math.floor(progress * target);
      counter.textContent = value.toString();
      if (progress < 1) requestAnimationFrame(animate);
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          requestAnimationFrame(animate);
          observer.disconnect();
        }
      });
    }, { threshold: 0.6 });

    observer.observe(counter);
  });

  const progressBar = document.getElementById('scrollProgress');
  const backToTop = document.getElementById('backToTop');

  window.addEventListener('scroll', () => {
    const scrollTop = window.scrollY;
    const height = document.documentElement.scrollHeight - window.innerHeight;
    const progress = height > 0 ? (scrollTop / height) * 100 : 0;
    if (progressBar) progressBar.style.width = `${progress}%`;
    if (backToTop) backToTop.classList.toggle('show', scrollTop > 500);
  });

  if (backToTop) {
    backToTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
  }

  const forms = document.querySelectorAll('form');
  forms.forEach((form) => {
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      const successBox = form.querySelector('.form-success');
      if (successBox) {
        successBox.classList.add('show');
      }
      form.reset();
    });
  });
});
