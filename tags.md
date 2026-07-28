---
layout: page
title: "Tags"
description: "Browse all articles by tag."
permalink: /tags/
---
<div class="single-post mb-0">
	<div class="entry clearfix">
		<div class="entry-title">
			<h2>Tags</h2>
		</div>
		<div class="entry-content mt-0">

			<div class="tagcloud clearfix">
				{% assign sorted_tags = site.tags | sort %}
				{% for tag in sorted_tags %}
				<a href="{{ '/tags/' | relative_url }}{{ tag[0] | slugify }}/">{{ tag[0] }} <small>({{ tag[1] | size }})</small></a>
				{% endfor %}
			</div>

		</div>
	</div>
</div>
