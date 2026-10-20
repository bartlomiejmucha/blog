---
layout: post
title: "Adding an Execute button to the Sitecron admin page"
description: "I added an Execute button to the Sitecron admin page and submitted the change as a pull request to the original repository."
date: "2026-10-20 +0100"
tags: [Sitecore, Sitecore 10.5, Sitecron]
---
## Running a Sitecron job on demand

Sitecron is one of the modules I install in every project. It is useful for running jobs on a schedule, but sometimes you want to start a job manually instead of waiting for its next scheduled run. If the job is configured in a config patch, there is no way to do it.

That is why I added an **Execute** button to the Sitecron admin page to make that possible.

## The change

The button lets you trigger a job directly from the admin page. This is handy when you want to run a job on demand—for example, while testing a change or checking its behavior—without changing its schedule.

![Execute button in Sitecron admin panel](/assets/images/posts/042/execute-button-in-sitecron-admin-panel.png){: loading="lazy" width="1968" height="812"}

## Contributing it back

Rather than keeping the change in my own copy, I submitted it as a pull request to the original Sitecron repository: [https://github.com/akshaysura/Sitecron/pull/46](https://github.com/akshaysura/Sitecron/pull/46)
