// Cookie consent: loads Google Analytics only after the visitor accepts.
// Standalone copy of assets/js/consent.js from the blog theme (blog@theme): same cookie,
// same banner, but the banner is built here because these pages have no shared layout.
// The choice is kept in a cookie on bartlomiejmucha.com (strictly necessary, needs
// no consent), so one answer covers www, edu and apps. It is asked again after a year.
// Any [data-cookie-settings] element reopens the banner.
(function () {
	var GA_ID = 'G-S2470CXBB6';
	var KEY = 'cookie-consent';
	var MAX_AGE = 365 * 24 * 60 * 60;

	var style = document.createElement('style');
	style.textContent =
		'#cookie-consent{position:fixed;left:16px;right:16px;bottom:16px;z-index:2147483000;margin:0 auto;max-width:36rem;box-sizing:border-box;' +
		'padding:24px;border:1px solid rgba(10,10,10,.1);border-radius:16px;background:#f6f5f2;color:#0a0a0a;' +
		'box-shadow:0 20px 50px -20px rgba(10,10,10,.5);font-family:Inter,ui-sans-serif,system-ui,sans-serif;text-align:left}' +
		'#cookie-consent[hidden]{display:none}' +
		'#cookie-consent p{margin:0;font-size:14px;line-height:1.625;color:rgba(10,10,10,.7)}' +
		'#cookie-consent div{display:flex;gap:12px;margin-top:20px}' +
		'#cookie-consent button{flex:1;margin:0;padding:10px 20px;border:1px solid transparent;border-radius:9999px;font-family:inherit;font-size:14px;font-weight:500;line-height:20px;cursor:pointer;transition:background-color .15s,border-color .15s}' +
		'#cookie-consent [data-consent=granted]{background:#0a0a0a;color:#f6f5f2}' +
		'#cookie-consent [data-consent=granted]:hover{background:rgba(10,10,10,.8)}' +
		'#cookie-consent [data-consent=denied]{background:transparent;color:#0a0a0a;border-color:rgba(10,10,10,.25)}' +
		'#cookie-consent [data-consent=denied]:hover{border-color:#0a0a0a}' +
		'@media (min-width:40rem){#cookie-consent{left:24px;right:24px;bottom:24px}}';
	document.head.appendChild(style);

	var banner = document.createElement('div');
	banner.id = 'cookie-consent';
	banner.hidden = true;
	banner.setAttribute('role', 'dialog');
	banner.setAttribute('aria-live', 'polite');
	banner.setAttribute('aria-label', 'Cookie consent');
	banner.innerHTML =
		'<p>I use Google Analytics cookies to see which pages people visit. They are set only if you accept. ' +
		'You can change your mind any time from the Cookie settings link at the bottom of the page.</p>' +
		'<div><button type="button" data-consent="granted">Accept</button>' +
		'<button type="button" data-consent="denied">Reject</button></div>';

	function read() {
		var m = document.cookie.match(/(?:^|;\s*)cookie-consent=(granted|denied)/);
		return m ? m[1] : null;
	}

	function save(choice) {
		var domain = /(^|\.)bartlomiejmucha\.com$/.test(location.hostname) ? '; domain=bartlomiejmucha.com' : '';
		var secure = location.protocol === 'https:' ? '; Secure' : '';
		document.cookie = KEY + '=' + choice + '; Max-Age=' + MAX_AGE + '; path=/; SameSite=Lax' + domain + secure;
	}

	function loadAnalytics() {
		if (window.gtag) return;
		window.dataLayer = window.dataLayer || [];
		window.gtag = function () { dataLayer.push(arguments); };
		gtag('js', new Date());
		gtag('config', GA_ID);
		var s = document.createElement('script');
		s.async = true;
		s.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(GA_ID);
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

	function show() { banner.hidden = false; }
	function hide() { banner.hidden = true; }

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

	function init() {
		document.body.appendChild(banner);
		var choice = read();
		if (choice === 'granted') loadAnalytics();
		else if (choice === 'denied') clearAnalyticsCookies();
		else show();
	}
	if (document.body) init();
	else document.addEventListener('DOMContentLoaded', init);
}());
