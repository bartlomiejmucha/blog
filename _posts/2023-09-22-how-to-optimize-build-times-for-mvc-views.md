---
layout: post
series: msbuild
title: "How to optimize build times for mvc views"
description: "In Sitecore projects, with many projects in a solution and huge number of view files, building mvc views can significanlty increase total build time. That time can be reduced by using MSBuild incremental build feature."
date: "2023-09-22 +0100"
tags: [Sitecore, MSBuild, MVC]
image: /assets/images/posts/msbuild-series-small-logo.png
categories: msbuild
---
### Compile MVC views during build
 
By default views are compiled at the runtime on the first request. It slows down start up times but also if there is a bug in the view, the error page will be displayed. That is why, it's a good idea to compile mvc views during build to pick up errors as early in the development process as possible.

Enabling MVC compilation during build time can be done by extending msbuild. To achieve that paste the following code to the `Directory.Build.targets` file:
``` xml
<PropertyGroup>
  <BuildDependsOn>
    $(BuildDependsOn);
    BuildMvcViews;
  </BuildDependsOn>
</PropertyGroup>

<Target Name="BuildMvcViews">
  <AspNetCompiler VirtualPath="temp" PhysicalPath="$(ProjectDir)" />
</Target>
```
### Build MVC views incrementally

The above code works fine, however if you have a huge number of projects (like we normally have in sitecore solutions) and a lot of `*.cshtml` files, the total build time of your solution can hugely increase. The `aspnet_compiler.exe` which is used under the hood is not well optimized. In my current project building mvc views doubles the total build time. It is especially painful for those with slow machines.

**MSBuild** has a feature called [incremental builds](https://learn.microsoft.com/en-us/visualstudio/msbuild/how-to-build-incrementally) that can be used to tell msbuild to avoid building views again if there are no changes.

The quote from the [documentation](https://learn.microsoft.com/en-us/visualstudio/msbuild/how-to-build-incrementally) says:

> To enable incremental builds (builds in which only those targets that have not been built before or targets that are out of date, are rebuilt), the Microsoft Build Engine (MSBuild) can compare the timestamps of the input files with the timestamps of the output files and determine whether to skip, build, or partially rebuild a target.

To use that feature we need to provide input files and output file(s) so MSBuild can compare timestamps of them. For inputs we can use `*.cshtml` files: 

``` xml
<ItemGroup>
  <BuildMvcViewsInputs Include="$(ProjectDir)Views\**\*.cshtml"></BuildMvcViewsInputs>
</ItemGroup>
```

We don't have an output file so we need to create one. For that we can just create an empty file and store it inside `obj\$(Configuration)`. The file will be updated every time the views are compiled. So the timestamp of the output file will be greater than the timestamp of all the input files, unless any of the input files is modified. In that case a rebuild will happen again and the output file will be overwritten with a new timestamp. We can keep the path to the output file in a new property:

``` xml
<BuildMvcViewsCacheFile>$(IntermediateOutputPath)$(MSBuildProjectFile).BuildMvcViews.cache</BuildMvcViewsCacheFile>
```

We can generate that output file directly after the compilation of mvc views is completed by adding the following code after `<AspNetCompiler`:

``` xml
<WriteLinesToFile
    File="$(BuildMvcViewsCacheFile)"
    Lines=""
    Overwrite="true" />
```

Finally we can provide `Inputs` and `Outputs` to `BuildMvcViews` target and set `Conditions`. The complete code can look like this:

``` xml
<PropertyGroup>
  <BuildDependsOn>
    $(BuildDependsOn);
    BuildMvcViews;
  </BuildDependsOn>

  <BuildMvcViewsCacheFile>$(IntermediateOutputPath)$(MSBuildProjectFile).BuildMvcViews.cache</BuildMvcViewsCacheFile>
</PropertyGroup>

<ItemGroup>
  <BuildMvcViewsInputs Include="$(ProjectDir)Views\**\*.cshtml"></BuildMvcViewsInputs>
</ItemGroup>

<Target Name="BuildMvcViews" Inputs="@(BuildMvcViewsInputs)" Outputs="$(BuildMvcViewsCacheFile)">
  <AspNetCompiler VirtualPath="temp" PhysicalPath="$(ProjectDir)" Condition="'@(BuildMvcViewsInputs)' != ''"/>
  <WriteLinesToFile
    File="$(BuildMvcViewsCacheFile)"
    Lines=""
    Overwrite="true"
    Condition="'@(BuildMvcViewsInputs)' != ''"/>
</Target>
```

There is one more thing to do. We need to delete the output file when someone runs Cleanup or Rebuild of the solution. For that we need to update the code with the following code: 

``` xml
<PropertyGroup>
  <CleanDependsOn>
    $(CleanDependsOn);
    CleanBuildMvcViewsCacheFile;
  </CleanDependsOn>
</PropertyGroup>

<Target Name="CleanBuildMvcViewsCacheFile">
  <Delete Files="$(BuildMvcViewsCacheFile)" />
</Target>
```

The complete example looks like this:

``` xml
<PropertyGroup>
  <BuildDependsOn>
    $(BuildDependsOn);
    BuildMvcViews;
  </BuildDependsOn>

  <BuildMvcViewsCacheFile>$(IntermediateOutputPath)$(MSBuildProjectFile).BuildMvcViews.cache</BuildMvcViewsCacheFile>
</PropertyGroup>

<ItemGroup>
  <BuildMvcViewsInputs Include="$(ProjectDir)Views\**\*.cshtml"></BuildMvcViewsInputs>
</ItemGroup>

<Target Name="BuildMvcViews" Inputs="@(BuildMvcViewsInputs)" Outputs="$(BuildMvcViewsCacheFile)">
  <AspNetCompiler VirtualPath="temp" PhysicalPath="$(ProjectDir)" Condition="'@(BuildMvcViewsInputs)' != ''"/>
  <WriteLinesToFile
    File="$(BuildMvcViewsCacheFile)"
    Lines=""
    Overwrite="true"
    Condition="'@(BuildMvcViewsInputs)' != ''"/>
</Target>

<PropertyGroup>
  <CleanDependsOn>
    $(CleanDependsOn);
    CleanBuildMvcViewsCacheFile;
  </CleanDependsOn>
</PropertyGroup>

<Target Name="CleanBuildMvcViewsCacheFile">
  <Delete Files="$(BuildMvcViewsCacheFile)" />
</Target>
```