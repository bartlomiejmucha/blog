// Cookie consent: loads Google Analytics only after the visitor accepts.
// The choice is kept in a cookie on bartlomiejmucha.com (strictly necessary, needs
// no consent), so one answer covers www, edu and apps. It is asked again after a year.
// Any [data-cookie-settings] element reopens the banner.
// edu and apps carry a standalone copy of this logic in their own consent.js.
(function () {
	var KEY = 'cookie-consent';
	var MAX_AGE = 365 * 24 * 60 * 60;
	var banner = document.getElementById('cookie-consent');
	if (!banner) return;
	var gaId = banner.getAttribute('data-ga-id');

	function read() {
		var m = document.cookie.match(/(?:^|;\s*)cookie-consent=(granted|denied)/);
		if (m) return m[1];
		// Choices made before the cookie existed were kept in localStorage. Move them over.
		try {
			var saved = JSON.parse(localStorage.getItem(KEY));
			localStorage.removeItem(KEY);
			if (saved && Date.now() - saved.at < MAX_AGE * 1000) { save(saved.choice); return saved.choice; }
		} catch (e) {}
		return null;
	}

	function save(choice) {
		var domain = /(^|\.)bartlomiejmucha\.com$/.test(location.hostname) ? '; domain=bartlomiejmucha.com' : '';
		var secure = location.protocol === 'https:' ? '; Secure' : '';
		document.cookie = KEY + '=' + choice + '; Max-Age=' + MAX_AGE + '; path=/; SameSite=Lax' + domain + secure;
	}

	function loadAnalytics() {
		if (!gaId || window.gtag) return;
		window.dataLayer = window.dataLayer || [];
		window.gtag = function () { dataLayer.push(arguments); };
		gtag('js', new Date());
		gtag('config', gaId);
		var s = document.createElement('script');
		s.async = true;
		s.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(gaId);
		document.head.appendChild(s);
	}

	// GA sets _ga and _ga_<id> on the top-most domain it can, so try every parent domain.
	function clearAnalyticsCookies() {
		var parts = location.hostname.split('.');
		document.cookie.split(';').forEach(function (c) {
			var name = c.split('=')[0].trim();
			if (name !== '_ga' && name.indexOf('_ga_') !== 0) return;
			for (var i = 0; i < parts.length; i++) {
				var domain = parts.slice(i).join('.');
				document.cookie = name + '=; Max-Age=0; path=/; domain=' + domain;
			}
			document.cookie = name + '=; Max-Age=0; path=/';
		});
	}

	function show() { banner.classList.remove('hidden'); }
	function hide() { banner.classList.add('hidden'); }

	banner.addEventListener('click', function (e) {
		var btn = e.target.closest('[data-consent]');
		if (!btn) return;
		var choice = btn.getAttribute('data-consent');
		var wasLoaded = !!window.gtag;
		save(choice);
		hide();
		if (choice === 'granted') {
			loadAnalytics();
		} else {
			clearAnalyticsCookies();
			// A running gtag keeps writing cookies until the page is gone.
			if (wasLoaded) location.reload();
		}
	});

	document.addEventListener('click', function (e) {
		if (e.target.closest('[data-cookie-settings]')) { e.preventDefault(); show(); }
	});

	var choice = read();
	if (choice === 'granted') loadAnalytics();
	else if (choice === 'denied') clearAnalyticsCookies();
	else show();
}());
