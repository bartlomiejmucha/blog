---
layout: page
title: "Tags"
description: "Browse all articles by tag."
permalink: /en/blog/tags/
no_prose: true
---
<div class="flex flex-wrap gap-2 text-sm">
	{% assign sorted_tags = site.tags | sort %}
	{% for tag in sorted_tags %}
	<a href="{{ '/en/blog/tags/' | relative_url }}{{ tag[0] | slugify }}/" class="rounded-full border border-ink/20 px-4 py-1.5 text-ink/60 transition hover:border-ink hover:text-ink">{{ tag[0] }} <span class="text-ink/35">{{ tag[1] | size }}</span></a>
	{% endfor %}
</div>
