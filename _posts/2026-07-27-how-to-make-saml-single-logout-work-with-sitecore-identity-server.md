---
layout: post
title: "How to make SAML Single Logout work with a custom Sitecore Identity provider"
description: "Adding a custom SAML identity provider to Sitecore Identity Server is described on the internet by others, but those guides stop at login. Here is the missing piece that makes logout (SAML Single Logout) actually work."
date: "2026-07-27 +0100"
tags: [Sitecore, Sitecore Identity, SAML, Sustainsys.Saml2]
---
### Login is the easy part

Some time ago I had to plug a custom SAML identity provider into Sitecore Identity Server. There are a few good posts out there that walk you through the login side of it, and these are the ones I used when I implemented it:

- [Sitecore Identity - Part 1](https://himadritechblog.wordpress.com/2019/01/14/sitecore-identity-part-1/)
- [Does Sitecore 10.0.1 support SAML with Okta?](https://sitecore.stackexchange.com/questions/28362/does-sitecore-10-0-1-support-saml-with-okta)
- [Connecting Sitecore Identity to SAML - Part 1](https://www.velir.com/ideas/2021/09/22/connecting-sitecore-identity-to-saml-part-1)

The approach they describe uses the [Sustainsys.Saml2](https://github.com/Sustainsys/Saml2) library to add the SAML authentication scheme, and after following them, login works nicely. You click the external provider button, you get redirected to the IdP, you authenticate, you come back and you are logged into Sitecore.

And then you click logout, after a few redirects you get back to sitecore authenticated again.

### The problem

When you log out of Sitecore, you also want to log out of the identity provider, so the next time you hit the login button you are actually asked to authenticate again instead of being silently signed straight back in from an existing IdP session.

To do that, Sustainsys.Saml2 has to generate a SAML `LogoutRequest` and send it to the IdP. But in my case that request was never produced - so the IdP session was never terminated, and the logout round-trip just bounced me back into Sitecore, still authenticated.

### Why it happens

To build a valid `LogoutRequest`, Sustainsys.Saml2 needs two pieces of information from the original login:

```
http://Sustainsys.se/Saml2/LogoutNameIdentifier
http://Sustainsys.se/Saml2/SessionIndex
```

The catch is *where* those claims live. During login they are attached to the **external** identity, held in the short-lived `idsrv.external` cookie. Sitecore's `AccountController.ExternalLoginCallback` reads that external identity, picks out the claims it cares about (like `sub` and `sid`), copies them into the persistent Identity Server session, and then signs out of the `idsrv.external` scheme - which deletes that cookie and everything left on it.

The two Sustainsys logout claims are **not** on that copy-over list. So by the time you actually click logout, they are long gone, Sustainsys can't find the `NameID` and `SessionIndex`, and it can't build the `LogoutRequest`.

### The fix



The fix is to make sure those two claims survive the login callback, so they are stored in the Identity Server session and are still around when logout happens.

Sitecore's `AccountController` contains a method `ExternalLoginCallback`, where the additional claims that get persisted into the session are assembled. Right after Sitecore adds the `sid` claim, I copy the two Sustainsys claims across:

``` cs
List<Claim> additionalClaims = new List<Claim>();

Claim sid = claims.FirstOrDefault(x => string.Equals(x.Type, "sid", StringComparison.Ordinal));
if (sid != null)
    additionalClaims.Add(new Claim("sid", sid.Value));

// INFO: Customisation starts
Claim logoutNameIdentifierClaim = claims.FirstOrDefault(x =>
    string.Equals(x.Type, "http://Sustainsys.se/Saml2/LogoutNameIdentifier", StringComparison.Ordinal));
if (logoutNameIdentifierClaim != null)
    additionalClaims.Add(new Claim(
        logoutNameIdentifierClaim.Type,
        logoutNameIdentifierClaim.Value,
        logoutNameIdentifierClaim.ValueType,
        logoutNameIdentifierClaim.Issuer,
        logoutNameIdentifierClaim.OriginalIssuer));

Claim sessionIndexClaim = claims.FirstOrDefault(x =>
    string.Equals(x.Type, "http://Sustainsys.se/Saml2/SessionIndex", StringComparison.Ordinal));
if (sessionIndexClaim != null)
    additionalClaims.Add(new Claim(
        sessionIndexClaim.Type,
        sessionIndexClaim.Value,
        sessionIndexClaim.ValueType,
        sessionIndexClaim.Issuer,
        sessionIndexClaim.OriginalIssuer));
// INFO: Customisation ends
```

With those two claims now living in the Identity Server session, the logout flow has everything it needs. When you hit logout, Sitecore triggers the external sign-out, Sustainsys.Saml2 finds the `LogoutNameIdentifier` and `SessionIndex` claims, generates a proper SAML `LogoutRequest`, and the IdP session finally gets terminated together with the Sitecore one.

### Replacing the AccountController

`ExternalLoginCallback` is part of Sitecore's own `AccountController`, which lives in the `Sitecore.Plugin.IdentityServer` assembly. I can't just drop in another controller with the same name - MVC would discover both and fail with an ambiguous match. So my `AccountController` is a copy of Sitecore's with only the change above, and I have to make MVC use mine instead of Sitecore's.

The way to do that is to hide Sitecore's controller from MVC's controller discovery. A `ControllerFeatureProvider` decides which types are treated as controllers, so I subclass it and answer "no" for Sitecore's `AccountController`:

``` cs
public class AccountControllerFeatureProvider : ControllerFeatureProvider
{
    private static readonly TypeInfo SitecoreAccountControllerType =
        typeof(Sitecore.Plugin.IdentityServer.Controllers.AccountController).GetTypeInfo();

    protected override bool IsController(TypeInfo typeInfo)
    {
        if (typeInfo == SitecoreAccountControllerType)
        {
            return false;
        }

        return base.IsController(typeInfo);
    }
}
```

Then in my plugin's `ConfigureSitecore` I add my own assembly as an application part - so my `AccountController` gets picked up - and swap the default feature provider for the one above:

``` cs
services
    .AddMvcCore()
    .ConfigureApplicationPartManager(apm =>
    {
        apm.ApplicationParts.Add(new AssemblyPart(typeof(AccountController).Assembly));

        for (var i = 0; i < apm.FeatureProviders.Count; i++)
        {
            if (apm.FeatureProviders[i] is ControllerFeatureProvider and not AccountControllerFeatureProvider)
            {
                apm.FeatureProviders[i] = new AccountControllerFeatureProvider();
            }
        }
    });
```

With Sitecore's `AccountController` hidden and mine registered under the same `Account` routes, my `ExternalLoginCallback` - and the two extra claims - now run in its place.

### One assumption

This fix is only about the claims, and it assumes the rest of your Single Logout setup is already in place. In particular, the IdP metadata has to advertise a Single Logout endpoint, and on the Sustainsys side you need a service certificate with a private key so it can sign the `LogoutRequest` - most IdPs will reject an unsigned one. If either of those is missing, carrying the claims across won't be enough on its own.

Happy Sitecoring!
