"use strict";

Redoc.init(
  "/openapi.json",
  { disableGoogleFont: true, hideDownloadButton: true, hideSidebar: true },
  document.getElementById("redoc"),
);
