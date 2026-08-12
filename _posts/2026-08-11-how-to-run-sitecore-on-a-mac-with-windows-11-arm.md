---
layout: post
title: "How to run Sitecore on a Mac with Windows 11 ARM"
description: "Out of curiosity I tried to install Sitecore 10.5 on a Windows 11 ARM virtual machine on my Mac. It installed and it started. Here is the full setup, including the one thing that does not work out of the box."
date: "2026-08-11 +0100"
tags: [Sitecore, Sitecore 10.5, Installation, ARM64, Windows 11, Mac, URL Rewrite]
---
### Sitecore on a Mac?

This one was an experiment. I was curious whether I could run Sitecore 10.5 on a Windows 11 ARM virtual machine on my Mac. If it worked, I could have just one machine for everything I need.

I was expecting problems, but in the end it went quite well. It installed and it started. There was only one ARM specific issue: URL Rewrite, and there is a workaround for it.

Below are the setup steps, in order.

### 0. The virtual machine

I ran this on **Parallels Desktop 26** on a MacBook Pro 14 inch M5 Max, with a Windows 11 ARM guest downloaded and installed by Parallels. The VM got **4 CPU cores** and **16 GB of RAM**, and at that size it was comfortable to work with.

### 1. A fresh Windows 11, in English

I started from a clean Windows 11 ARM installation and **set the display language to English**. When it was in Polish, installing SQL Server through `winget` failed for me.

### 2. Install IIS

Two `dism` commands, from an elevated prompt:

``` powershell
dism /online /enable-feature /featurename:IIS-WebServerRole /all /norestart
dism /online /enable-feature /featurename:IIS-WebServer /all
```

The first one enables the web server role and its dependencies, the second one enables the web server itself. `/all` pulls in the parent features, so you don't have to enable them one by one.

### 3. Install SQL Server 2025 and Management Studio

Both are available through `winget`, which saves you a trip to the download pages:

``` powershell
winget install Microsoft.SQLServer.2025.Developer
winget install Microsoft.SQLServerManagementStudio.22
```

### 4. Enable SQL authentication and unlock the `sa` user

The `winget` installation only enables Windows authentication, but the Sitecore Installation Assistant asks for a SQL login. So it has to be configured afterwards, with the following commands.

Mixed mode is a registry value - `LoginMode` set to `2`:

``` powershell
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Microsoft SQL Server\MSSQL17.MSSQLSERVER\MSSQLServer" -Name LoginMode -Value 2
```

Then enable the `sa` login and give it a password:

``` powershell
sqlcmd -S localhost -E -C -Q "ALTER LOGIN sa ENABLE; ALTER LOGIN sa WITH PASSWORD = '{Your Password}!' UNLOCK;"
```

`-E` connects with your Windows credentials, and `-C` trusts the self-signed server certificate.

The `LoginMode` value is only read at startup, so restart the service:

``` powershell
Restart-Service MSSQLSERVER
```

### 5. Install Visual Studio

``` powershell
winget install --id Microsoft.VisualStudio.Community -e --override "--quiet --wait --norestart --add Microsoft.VisualStudio.Workload.NetWeb --includeRecommended"
```

Everything after `--override` is passed straight to the Visual Studio installer: install quietly, wait for it to finish, don't reboot, and add the **ASP.NET and web development** workload with its recommended components.

Do not skip this step even if you were not planning to write code on this machine. On ARM64 Windows this gives you the ARM64 build of Visual Studio, and with it **IIS Express** - which is where the missing piece of the next step comes from.

### 6. Install URL Rewrite

Sitecore needs the URL Rewrite module, also available through `winget`:

``` powershell
winget install --id Microsoft.IIS.URLRewrite -e --accept-package-agreements --accept-source-agreements
```

This installs fine. On ARM64 it is not enough on its own, which brings us to the one broken piece.

### 7. Fix `rewrite.dll` for ARM64

Here is the one thing I mentioned at the top.

The official URL Rewrite installer ships only x86 and x64 builds of `rewrite.dll`. That is enough for emulated web apps, but as the patch author documents, IIS crashes the application pool when it tries to load the module into an ARM64 one. Microsoft never shipped an ARM64 build of the module, which is understandable - there is no ARM64 Windows Server to run it on in production.

IIS Express, however, *does* include an ARM64 `rewrite.dll` - and you have just installed IIS Express together with Visual Studio.

That is exactly what [lextm/rewrite-arm64](https://github.com/lextm/rewrite-arm64) automates. Clone the repository, open PowerShell as administrator, go to the repository folder and run:

``` powershell
.\patch.ps1
```

It is worth knowing that it pulls components out of IIS Express, which Microsoft licenses **for development and testing only**.

### 8. Install Sitecore 10.5

With all of the above in place, the ARM-specific work is done. Download the Sitecore 10.5 Installation Assistant and run it as you would on any other machine - it found IIS, found SQL Server, and installed the remaining prerequisites, Solr included, without needing anything else from me.

If you want a single standalone instance instead of the CM/CD split the Installation Assistant gives you, I described the changes for that in [How to install XM0 with Installation Assistant]({{ site.baseurl }}{% post_url 2026-03-13-how-to-install-xm0-with-installation-assistant %}).

### So does it work?

It does. I rebuilt the link databases, populated the Solr indexes and rebuilt them, and clicked around the Content Editor and the Experience Editor. Search works. Nothing along the way complained about the architecture.

What I have not done is anything real with it - no solution deployed on top, no serialization, no modules, no day of actual work. So this is a starting point rather than a verdict. Still, out of the whole stack exactly one DLL cared that it was running on ARM, and that one has a fix.

Happy Sitecoring!
