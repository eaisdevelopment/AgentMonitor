# Work better with — product-family promotion

`index.html` is a self-contained promotion: copy it to a project or host it as a static file. It does not need a build, server-side code, external fonts, analytics, or network requests except when a visitor opens a product link.

To embed a hosted copy:

```html
<iframe
  src="/adv/index.html?exclude=cogent"
  title="Discover the Essential AI product family"
  style="width: 100%; min-height: 560px; border: 0;"
  loading="lazy"
></iframe>
```

Use `exclude` to hide the current project from the rotation, for example `?exclude=cogent` or `?exclude=cogent,all2wiki`. IDs are `cogent`, `all2wiki`, `clone-detector`, `marvin`, `klaire`, `megaprompting`, `jevmcp`, `skills`, `multi-edit`, and `agentmonitor`. Omit the parameter to show the entire family. The iframe height can be adapted to the space and viewport; direct inclusion or linking also works.

Rotation defaults to nine seconds. Use `?interval=12000` for 12 seconds; accepted values are 5,000–60,000 milliseconds. Visitors can navigate manually, pause the rotation, and choose a product from the directory. Rotation pauses when the browser tab is hidden, when a pointer or keyboard focus is within the promotion, and by default when reduced motion is requested.

Product names, descriptions, links, colours and the list order are in the `products` array in `index.html`. AgentMonitor links to its public source repository. Update its `url` field if the product gets a dedicated website.
