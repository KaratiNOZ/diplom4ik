// Простая карусель: prev/next + точки + drag/swipe + клавиатура.
// Работает с любым блоком, у которого есть data-carousel.
// Структура: .carousel > .carousel-viewport > .carousel-track > .carousel-slide

(function () {
    'use strict';

    function initCarousel(root) {
        const viewport = root.querySelector('[data-carousel-viewport]');
        const track = root.querySelector('[data-carousel-track]');
        const prevBtn = root.querySelector('[data-carousel-prev]');
        const nextBtn = root.querySelector('[data-carousel-next]');
        const dotsBox = root.querySelector('[data-carousel-dots]');
        const slides = Array.from(track.children);

        if (!slides.length) return;

        let index = 0;

        // Сколько слайдов помещается за раз — вычисляем по реальной ширине.
        function slidesPerView() {
            const slideW = slides[0].getBoundingClientRect().width;
            const gap = parseFloat(getComputedStyle(track).gap) || 0;
            const viewportW = viewport.getBoundingClientRect().width;
            return Math.max(1, Math.round((viewportW + gap) / (slideW + gap)));
        }

        function maxIndex() {
            return Math.max(0, slides.length - slidesPerView());
        }

        function update() {
            const slideW = slides[0].getBoundingClientRect().width;
            const gap = parseFloat(getComputedStyle(track).gap) || 0;
            const offset = index * (slideW + gap);
            track.style.transform = `translateX(-${offset}px)`;

            if (prevBtn) prevBtn.disabled = index <= 0;
            if (nextBtn) nextBtn.disabled = index >= maxIndex();

            // Подсветка точек
            if (dotsBox) {
                Array.from(dotsBox.children).forEach((dot, i) => {
                    dot.classList.toggle('active', i === index);
                });
            }
        }

        function go(i) {
            index = Math.max(0, Math.min(i, maxIndex()));
            update();
        }

        // Точки
        function buildDots() {
            if (!dotsBox) return;
            dotsBox.innerHTML = '';
            const total = maxIndex() + 1;
            for (let i = 0; i < total; i++) {
                const dot = document.createElement('button');
                dot.className = 'carousel-dot';
                dot.type = 'button';
                dot.setAttribute('aria-label', `Слайд ${i + 1}`);
                dot.addEventListener('click', () => go(i));
                dotsBox.appendChild(dot);
            }
        }

        // Кнопки
        if (prevBtn) prevBtn.addEventListener('click', () => go(index - 1));
        if (nextBtn) nextBtn.addEventListener('click', () => go(index + 1));

        // Клавиатура (когда фокус внутри карусели)
        root.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft') { e.preventDefault(); go(index - 1); }
            if (e.key === 'ArrowRight') { e.preventDefault(); go(index + 1); }
        });
        root.tabIndex = 0;

        // Свайп / drag
        let startX = 0;
        let dragging = false;

        viewport.addEventListener('pointerdown', (e) => {
            dragging = true;
            startX = e.clientX;
            viewport.setPointerCapture(e.pointerId);
        });
        viewport.addEventListener('pointerup', (e) => {
            if (!dragging) return;
            dragging = false;
            const dx = e.clientX - startX;
            if (Math.abs(dx) > 40) {
                go(index + (dx < 0 ? 1 : -1));
            }
        });
        viewport.addEventListener('pointercancel', () => { dragging = false; });

        // Ресайз — пересчитать точки и положение
        let resizeTimer;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {
                buildDots();
                go(index); // проверит границы
            }, 150);
        });

        buildDots();
        update();
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('[data-carousel]').forEach(initCarousel);
    });
})();
