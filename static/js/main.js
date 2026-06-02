function initSpectrum() {
  initSplashIntro();
  initNavDropdowns();
  initSpectrumCarousel();
  initReveal();
}

function initNavDropdowns() {
  document.querySelectorAll("[data-dropdown]").forEach((item) => {
    let closeTimer = null;

    const open = () => {
      clearTimeout(closeTimer);
      item.classList.add("open");
    };

    const close = () => {
      closeTimer = setTimeout(() => item.classList.remove("open"), 120);
    };

    item.addEventListener("mouseenter", open);
    item.addEventListener("mouseleave", close);
    item.addEventListener("focusin", open);
    item.addEventListener("focusout", (e) => {
      if (!item.contains(e.relatedTarget)) close();
    });
  });
}

function initSplashIntro() {
  const splash = document.getElementById("splashIntro");
  const canvas = document.getElementById("splashCanvas");
  if (!splash || !canvas) return;

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reducedMotion) {
    splash.classList.add("is-dismissed");
    document.body.classList.remove("splash-active");
    return;
  }

  document.body.classList.add("splash-active");

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  let width = 0;
  let height = 0;
  let particles = [];
  let animationId = null;
  let startTime = 0;
  let dismissed = false;
  let convergeDone = false;
  const CONVERGE_MS = 2800;
  const TEXT = "THISDL";

  function sampleTextPoints() {
    const off = document.createElement("canvas");
    const octx = off.getContext("2d");
    const w = Math.min(900, Math.max(480, window.innerWidth * 0.82));
    const h = Math.min(220, w * 0.28);
    off.width = w;
    off.height = h;
    octx.fillStyle = "#000";
    octx.fillRect(0, 0, w, h);
    octx.fillStyle = "#fff";
    octx.font = `900 ${Math.floor(h * 0.72)}px Inter, Arial, sans-serif`;
    octx.textAlign = "center";
    octx.textBaseline = "middle";
    octx.fillText(TEXT, w / 2, h / 2);

    const data = octx.getImageData(0, 0, w, h).data;
    const points = [];
    const step = 5;
    for (let y = 0; y < h; y += step) {
      for (let x = 0; x < w; x += step) {
        const i = (y * w + x) * 4;
        if (data[i] > 120) points.push({ x, y });
      }
    }
    return { points, w, h };
  }

  function buildParticles() {
    const { points, w, h } = sampleTextPoints();
    const offsetX = (width - w) / 2;
    const offsetY = (height - h) / 2;

    particles = points.map((p) => {
      const angle = Math.random() * Math.PI * 2;
      const dist = Math.random() * Math.max(width, height) * 0.65;
      return {
        x: width / 2 + Math.cos(angle) * dist,
        y: height / 2 + Math.sin(angle) * dist,
        tx: offsetX + p.x,
        ty: offsetY + p.y,
        size: 1 + Math.random() * 2.2,
        delay: Math.random() * 0.35,
        twinkle: Math.random() * Math.PI * 2,
      };
    });
  }

  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    buildParticles();
  }

  function easeOutCubic(t) {
    return 1 - Math.pow(1 - t, 3);
  }

  function draw(now) {
    if (!startTime) startTime = now;
    const elapsed = now - startTime;
    const t = Math.min(1, elapsed / CONVERGE_MS);

    ctx.clearRect(0, 0, width, height);

    particles.forEach((p) => {
      const localT = Math.min(1, Math.max(0, (t - p.delay) / (1 - p.delay)));
      const e = easeOutCubic(localT);
      const x = p.x + (p.tx - p.x) * e;
      const y = p.y + (p.ty - p.y) * e;
      const alpha = 0.35 + 0.65 * e;
      const glow = 0.5 + 0.5 * Math.sin(now * 0.004 + p.twinkle);

      ctx.beginPath();
      ctx.arc(x, y, p.size * (0.6 + 0.4 * e), 0, Math.PI * 2);
      ctx.fillStyle = `rgba(216, 180, 254, ${alpha * glow})`;
      ctx.fill();

      if (e > 0.85) {
        ctx.beginPath();
        ctx.arc(x, y, p.size * 2.2, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(139, 92, 246, ${0.08 * glow})`;
        ctx.fill();
      }
    });

    if (t >= 1 && !convergeDone) {
      convergeDone = true;
      splash.classList.add("show-title", "show-hint");
    }

    if (!dismissed) animationId = requestAnimationFrame(draw);
  }

  function dismissSplash() {
    if (dismissed) return;
    dismissed = true;
    splash.classList.add("is-dismissed");
    document.body.classList.remove("splash-active");
    document.body.classList.add("splash-dismissed");
    if (animationId) cancelAnimationFrame(animationId);
    setTimeout(() => {
      splash.style.display = "none";
    }, 950);
  }

  let scrollAccum = 0;
  function onWheel(e) {
    if (dismissed) return;
    if (e.deltaY > 0) {
      scrollAccum += e.deltaY;
      if (scrollAccum > 40 || convergeDone) dismissSplash();
    }
  }

  let touchY = null;
  function onTouchStart(e) {
    touchY = e.touches[0].clientY;
  }
  function onTouchMove(e) {
    if (dismissed || touchY === null) return;
    const dy = touchY - e.touches[0].clientY;
    if (dy > 30) dismissSplash();
  }

  resize();
  window.addEventListener("resize", resize);
  requestAnimationFrame(draw);

  window.addEventListener("wheel", onWheel, { passive: true });
  splash.addEventListener("touchstart", onTouchStart, { passive: true });
  splash.addEventListener("touchmove", onTouchMove, { passive: true });

  setTimeout(() => {
    if (!dismissed) splash.classList.add("show-hint");
  }, CONVERGE_MS + 400);

  setTimeout(() => {
    if (!dismissed && convergeDone) dismissSplash();
  }, 6500);
}

function initSpectrumCarousel() {
  const dataEl = document.getElementById("carouselData");
  const slideBox = document.getElementById("slideBox");
  if (!dataEl || !slideBox) return;

  let slides = [];
  try {
    slides = JSON.parse(dataEl.textContent);
  } catch {
    return;
  }
  if (!slides.length) return;

  let slideIndex = 0;
  let timer = null;

  const slideArt = document.getElementById("slideArt");
  const slideField = document.getElementById("slideField");
  const slideTitle = document.getElementById("slideTitle");
  const slideDesc = document.getElementById("slideDesc");
  const slideStack = document.getElementById("slideStack");
  const slideDetailLink = document.getElementById("slideDetailLink");
  const dotsContainer = document.getElementById("carouselDots");
  const carousel = document.getElementById("homeCarousel");

  function renderSlide() {
    const p = slides[slideIndex];
    slideBox.style.animation = "none";
    void slideBox.offsetWidth;
    slideBox.style.animation = "pop .28s ease-out";

    if (slideField) slideField.textContent = p.category || "";
    if (slideTitle) slideTitle.textContent = p.title || "";
    if (slideDesc) slideDesc.textContent = p.summary || "";
    if (slideStack) {
      const tags = p.tags && p.tags.length ? p.tags : [p.author].filter(Boolean);
      slideStack.innerHTML = tags.map((s) => `<span>${s}</span>`).join("");
    }
    if (slideDetailLink) {
      slideDetailLink.href = `/work/${p.id}`;
    }
    if (slideArt) {
      if (p.cover) {
        slideArt.className = "slide-art has-cover";
        slideArt.style.backgroundImage = `linear-gradient(180deg,rgba(0,0,0,.1),rgba(0,0,0,.45)), url('${p.cover}')`;
      } else {
        slideArt.className = "slide-art";
        slideArt.style.backgroundImage = "";
      }
    }
    if (dotsContainer) {
      dotsContainer.innerHTML = slides
        .map(
          (_, i) =>
            `<button type="button" class="dot${i === slideIndex ? " active" : ""}" data-index="${i}" aria-label="Slide ${i + 1}"></button>`
        )
        .join("");
      dotsContainer.querySelectorAll(".dot").forEach((dot) => {
        dot.addEventListener("click", () => {
          slideIndex = Number(dot.dataset.index);
          renderSlide();
          startAuto();
        });
      });
    }
  }

  function nextSlide() {
    slideIndex = (slideIndex + 1) % slides.length;
    renderSlide();
  }

  function prevSlide() {
    slideIndex = (slideIndex - 1 + slides.length) % slides.length;
    renderSlide();
  }

  function startAuto() {
    stopAuto();
    if (slides.length > 1) {
      timer = setInterval(nextSlide, 5200);
    }
  }

  function stopAuto() {
    if (timer) clearInterval(timer);
  }

  carousel?.querySelector(".carousel-prev")?.addEventListener("click", () => {
    prevSlide();
    startAuto();
  });
  carousel?.querySelector(".carousel-next")?.addEventListener("click", () => {
    nextSlide();
    startAuto();
  });
  carousel?.querySelector(".carousel-next-btn")?.addEventListener("click", () => {
    nextSlide();
    startAuto();
  });

  carousel?.addEventListener("mouseenter", stopAuto);
  carousel?.addEventListener("mouseleave", startAuto);

  renderSlide();
  startAuto();
}

function initReveal() {
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const elements = document.querySelectorAll(".reveal");

  if (reducedMotion) {
    elements.forEach((el) => {
      el.classList.add("visible", "revealed-once");
    });
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        const el = entry.target;
        if (el.dataset.revealed === "1") return;

        if (entry.isIntersecting) {
          el.dataset.revealed = "1";
          el.classList.add("visible");
          observer.unobserve(el);
          el.addEventListener(
            "transitionend",
            () => el.classList.add("revealed-once"),
            { once: true }
          );
        }
      });
    },
    { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
  );

  elements.forEach((el) => observer.observe(el));
}

function initUploadPreview() {
  const input = document.getElementById("images");
  const preview = document.getElementById("previewList");
  const zone = document.getElementById("uploadZone");
  const captionFields = document.getElementById("captionFields");

  if (input && preview) {
    input.addEventListener("change", () => {
      renderPreviews(input, preview);
      renderCaptionFields(input, captionFields);
    });
    if (zone) {
      bindUploadZone(zone, input, () => {
        renderPreviews(input, preview);
        renderCaptionFields(input, captionFields);
      });
    }
  }

  const actInput = document.getElementById("activity_images");
  const actPreview = document.getElementById("activityPreviewList");
  const actZone = document.getElementById("activityUploadZone");
  if (actInput && actPreview) {
    actInput.addEventListener("change", () => renderPreviews(actInput, actPreview));
    if (actZone) {
      bindUploadZone(actZone, actInput, () => renderPreviews(actInput, actPreview));
    }
  }
}

function bindUploadZone(zone, input, onUpdate) {
  zone.addEventListener("dragover", (e) => {
    e.preventDefault();
    zone.classList.add("dragover");
  });
  zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("dragover");
    input.files = e.dataTransfer.files;
    onUpdate();
  });
}

function renderCaptionFields(input, container) {
  if (!container) return;
  container.innerHTML = "";
  Array.from(input.files).forEach((file, i) => {
    if (!file.type.startsWith("image/")) return;
    const wrap = document.createElement("div");
    wrap.className = "field";
    wrap.innerHTML = `
      <label>图片 ${i + 1} 名称</label>
      <input type="text" name="image_caption" maxlength="120" placeholder="如：训练阶段、游戏界面">
    `;
    container.appendChild(wrap);
  });
}

function renderPreviews(input, container) {
  container.innerHTML = "";
  Array.from(input.files).forEach((file) => {
    if (!file.type.startsWith("image/")) return;
    const img = document.createElement("img");
    img.src = URL.createObjectURL(file);
    img.onload = () => URL.revokeObjectURL(img.src);
    container.appendChild(img);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initSpectrum();
  initUploadPreview();

  document.querySelectorAll(".flash").forEach((el) => {
    setTimeout(() => {
      el.style.opacity = "0";
      el.style.transition = "opacity 0.4s";
      setTimeout(() => el.remove(), 400);
    }, 5000);
  });
});
