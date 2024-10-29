# Webkit GTK doesn't interop flawless with Solid.js build result

1. Webkit expects script tag to be in `body` only solid.js puts the in the head.
2. script and css files are loaded with type="module" and crossorigin tags being set. WebKit silently fails to load then.
3. Paths to resiources are not allowed to start with "/" because webkit interprets them relative to the system and not the base url.
4. webkit doesn't support native features such as directly handling external urls (i.e opening them in the default browser)
6. Other problems to be found?
