NDK library size analyzer
==========================

This is a simple tool to analyze size of native Android .so files and figure out which symbols are taking the most space.

Usage:

```bash
ndk-size-analyzer --symbols 100 android_project/.externalNativeBuild/cmake/debug/obj/armeabi-v7a/libnative.so
```

**NOTE**: You must analyze a **non-stripped debug** version of the library to get proper results. The analyzer won't count sizes of debug symbols.

Screenshot:

License:

```
Copyright 2013 Jernej Virag.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```
