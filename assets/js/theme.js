// Hello Programming World — theme behaviour: reading progress, back-to-top,
// auto table of contents and read time. No dependencies.
(function () {
	var doc = document.documentElement;
	var bar = document.getElementById('progress');
	var top = document.getElementById('gotoTop');
	var body = document.getElementById('post-body');
	var toc = document.getElementById('toc');
	var links = [];
	var heads = [];

	// Read time
	var readTime = document.getElementById('read-time');
	if (body && readTime) {
		var words = (body.innerText || '').trim().split(/\s+/).length;
		readTime.textContent = Math.max(1, Math.round(words / 220)) + ' min read';
	}

	// Table of contents from the rendered headings
	if (body && toc) {
		var headings = body.querySelectorAll('h2, h3');
		Array.prototype.forEach.call(headings, function (h, i) {
			if (!h.id) {
				var base = (h.textContent || '')
					.toLowerCase()
					.replace(/[^a-z0-9]+/g, '-')
					.replace(/^-+|-+$/g, '') || 'section-' + i;
				var id = base;
				var n = 2;
				while (document.getElementById(id)) id = base + '-' + n++;
				h.id = id;
			}
			var a = document.createElement('a');
			a.href = '#' + h.id;
			a.textContent = h.textContent;
			a.className = 'block text-ink/55 hover:text-ink transition';
			if (h.tagName === 'H3') a.classList.add('pl-4');
			toc.appendChild(a);
			links.push(a);
			heads.push(h);
		});
		if (!links.length) toc.parentNode.style.display = 'none';
	}

	if (top) {
		top.addEventListener('click', function () {
			window.scrollTo({ top: 0, behavior: 'smooth' });
		});
	}

	function tick() {
		var max = doc.scrollHeight - doc.clientHeight;
		if (bar) bar.style.width = (max > 0 ? (doc.scrollTop / max) * 100 : 0) + '%';

		if (top) {
			var showTop = doc.scrollTop >= 600;
			top.classList.toggle('hidden', !showTop);
			top.classList.toggle('flex', showTop);
		}

		if (links.length) {
			var current = 0;
			heads.forEach(function (el, i) {
				if (el.getBoundingClientRect().top < 140) current = i;
			});
			links.forEach(function (a, i) {
				a.classList.toggle('font-medium', i === current);
				a.classList.toggle('text-ink', i === current);
				a.classList.toggle('text-ink/55', i !== current);
			});
		}
	}

	addEventListener('scroll', tick, { passive: true });
	addEventListener('resize', tick);
	tick();
})();
