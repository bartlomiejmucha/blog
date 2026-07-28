---
layout: post
title: "How to install XM0 with Installation Assistant"
description: "The SitecoreInstallation Assistant for XM Scaled installs CM and CD as two separate sites. If all you need for local development is a single standalone instance, here is how to turn that install into XM0."
date: "2026-03-13 +0100"
tags: [Sitecore, Sitecore 10.4.1, SIF, Installation]
---
### Why XM0?

The *Installation Assistant for XM Scaled* setup package ships an XM1 topology - it installs a Content Management and a Content Delivery site as two separate roles. For local development that is usually more than you need. XM0 is the same thing collapsed into a single **Standalone** instance: one site that does both CM and CD.

There is no official XM0 package, but you can get there by trimming a few things from the XM1 setup before you run it, and by switching the role to `Standalone` afterwards.

Below are the changes I make, split into what to do **before** and **after** running the installer. Everything here was tested on **Sitecore 10.4.1**.

### Before the installation

#### 1. Download the graphical installer

Grab the *Installation Assistant for XM Scaled*, in my case it is **Sitecore 10.4.1 rev. 012149 (Setup XM1 Developer Workstation rev. 1.6.1-r7)**, and unzip it.

#### 2. Remove "cm" from the site prefix

Open `setup.exe.config`. The XM1 template defines two sitenames, one for CM and one for CD:

``` xml
<parameter name="SitecoreContentManagementSitename" value="{Prefix}cm.dev.local" />
<parameter name="SitecoreContentDeliverySitename" value="{Prefix}cd.dev.local" />
```

Because we want a single standalone site, drop the `cm` suffix so the content management site gets the clean hostname:

``` xml
<parameter name="SitecoreContentManagementSitename" value="{Prefix}.dev.local" />
<parameter name="SitecoreContentDeliverySitename" value="{Prefix}cd.dev.local" />
```

#### 3. Remove the SitecoreCD registration

In `XM1-SingleDeveloper.json`, the modules are registered in the `Includes` section, right before the `Register` section:

``` json
"Includes" : {
    "IdentityServerCertificates":{
        "Source": ".\\createcert.json"
    },
    "IdentityServer": {
        "Source": ".\\identityServer.json"
    },
    "SitecoreSolr": {
        "Source": ".\\Sitecore-solr.json"
    },
    "SitecoreCM": {
        "Source": ".\\Sitecore-XM1-cm.json"
    },
    "SitecoreCD": {
        "Source": ".\\Sitecore-XM1-cd.json"
    }
},
"Register": {
    "Tasks": {
        "SetVariable": "Set-Variable"
    }
},
```

XM0 has no separate delivery role, so remove the whole `SitecoreCD` block from `Includes`:

``` json
"Includes" : {
    "IdentityServerCertificates":{
        "Source": ".\\createcert.json"
    },
    "IdentityServer": {
        "Source": ".\\identityServer.json"
    },
    "SitecoreSolr": {
        "Source": ".\\Sitecore-solr.json"
    },
    "SitecoreCM": {
        "Source": ".\\Sitecore-XM1-cm.json"
    }
},
"Register": {
    "Tasks": {
        "SetVariable": "Set-Variable"
    }
},
```

Now you can run the setup.

### After the installation

#### 1. Set the role to Standalone

The XM1 install leaves the site configured as `ContentManagement`. Open the site's `Web.config` and change the role to `Standalone` so the single instance serves both CM and CD:

``` xml
<add key="role:define" value="Standalone" />
```

That's it - you now have a single standalone XM0 instance instead of the XM1 topology.

Happy Sitecoring!
