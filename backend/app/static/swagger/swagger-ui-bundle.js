(function () {
  "use strict";

  const root = document.getElementById("swagger-ui");

  function text(value) {
    return document.createTextNode(value || "");
  }

  function el(tag, className, children) {
    const node = document.createElement(tag);
    if (className) {
      node.className = className;
    }
    (children || []).forEach((child) => node.appendChild(child));
    return node;
  }

  function renderError(message) {
    root.replaceChildren(
      el("main", "swagger-shell", [
        el("div", "swagger-error", [text("Unable to load OpenAPI schema: " + message)]),
      ]),
    );
  }

  function renderOperation(path, method, operation) {
    const methodName = method.toUpperCase();
    const summary = operation.summary || operation.operationId || "API operation";
    const details = el("details", "swagger-card", [
      el("summary", "", [
        el("span", "swagger-method " + method, [text(methodName)]),
        el("span", "swagger-path", [text(path)]),
        el("span", "", [text(summary)]),
      ]),
    ]);
    details.appendChild(
      el("div", "swagger-body", [
        el("p", "", [text(operation.description || summary)]),
        el("p", "swagger-meta", [
          text("Operation ID: " + (operation.operationId || "not specified")),
        ]),
      ]),
    );
    return details;
  }

  function renderSchema(schema) {
    const title = schema.info && schema.info.title ? schema.info.title : "API documentation";
    const version = schema.info && schema.info.version ? schema.info.version : "";
    const operations = [];
    Object.entries(schema.paths || {}).forEach(([path, methods]) => {
      Object.entries(methods || {}).forEach(([method, operation]) => {
        if (["get", "post", "put", "patch", "delete"].includes(method)) {
          operations.push(renderOperation(path, method, operation || {}));
        }
      });
    });

    root.replaceChildren(
      el("main", "swagger-shell", [
        el("section", "swagger-header", [
          el("h1", "", [text(title)]),
          el("p", "", [text("OpenAPI " + (schema.openapi || "") + " " + version)]),
        ]),
        ...operations,
      ]),
    );
  }

  window.SwaggerUIBundle = function SwaggerUIBundle(config) {
    fetch(config.url, { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) {
          throw new Error(response.status + " " + response.statusText);
        }
        return response.json();
      })
      .then(renderSchema)
      .catch((error) => renderError(error.message));
    return { initOAuth: function () {} };
  };
  window.SwaggerUIBundle.presets = { apis: {} };
  window.SwaggerUIBundle.SwaggerUIStandalonePreset = {};
})();
