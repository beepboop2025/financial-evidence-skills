(function (global) {
  "use strict";

  const SUPPORTED_CONTEXT_TYPES = Object.freeze([
    "fdc3.instrument",
    "fdc3.organization",
    "fdc3.country",
  ]);

  const SAMPLE_CONTEXT = Object.freeze({
    type: "fdc3.instrument",
    name: "Example instrument",
    id: { ticker: "AAPL" },
  });

  function validateContext(context) {
    if (!context || typeof context !== "object" || Array.isArray(context)) {
      throw new TypeError("Context must be a JSON object.");
    }
    if (!SUPPORTED_CONTEXT_TYPES.includes(context.type)) {
      throw new TypeError(
        `Unsupported context type. Use ${SUPPORTED_CONTEXT_TYPES.join(", ")}.`,
      );
    }
    return context;
  }

  function parseContext(value) {
    let parsed;
    try {
      parsed = JSON.parse(value);
    } catch (_error) {
      throw new TypeError("Context must be valid JSON.");
    }
    return validateContext(parsed);
  }

  function sourceLabel(metadata) {
    const source = metadata && metadata.source;
    if (!source) return "Not provided";
    if (typeof source === "string") return source;
    if (source.appId && source.instanceId) {
      return `${source.appId} (${source.instanceId})`;
    }
    if (source.appId) return source.appId;
    return "Provided by Desktop Agent";
  }

  function createInspector(options) {
    const win = options.window;
    const doc = options.document;
    const now = options.now || (() => new Date());
    let desktopAgent = null;
    let connectionPromise = null;

    function element(id) {
      const found = doc.getElementById(id);
      if (!found) throw new Error(`Missing inspector element: ${id}`);
      return found;
    }

    function setStatus(kind, title, detail) {
      element("fdc3-status-indicator").className = `status-dot${kind ? ` ${kind}` : ""}`;
      element("fdc3-status").textContent = title;
      element("fdc3-status-detail").textContent = detail;
    }

    function setMessage(message, kind) {
      const output = element("composer-message");
      output.textContent = message;
      output.className = `message${kind ? ` ${kind}` : ""}`;
    }

    function renderContext(context, transport, metadata) {
      const valid = validateContext(context);
      element("context-type").textContent = valid.type;
      element("context-transport").textContent = transport;
      element("context-received-at").textContent = now().toISOString();
      element("context-source").textContent = sourceLabel(metadata);
      element("received-context").textContent = JSON.stringify(valid, null, 2);
      return valid;
    }

    async function connect(api) {
      if (connectionPromise) return connectionPromise;
      connectionPromise = (async () => {
        if (
          !api ||
          typeof api.addContextListener !== "function" ||
          typeof api.addIntentListener !== "function" ||
          typeof api.broadcast !== "function"
        ) {
          throw new TypeError("The injected object does not implement the required FDC3 2.0 APIs.");
        }

        desktopAgent = api;
        const registrations = [];
        try {
          for (const contextType of SUPPORTED_CONTEXT_TYPES) {
            registrations.push(
              await api.addContextListener(contextType, (context, metadata) => {
                renderContext(context, "FDC3 user channel", metadata);
              }),
            );
          }
          registrations.push(
            await api.addIntentListener("ViewInstrument", async (context, metadata) => {
              renderContext(context, "ViewInstrument intent", metadata);
            }),
          );
        } catch (error) {
          await Promise.allSettled(
            registrations.map((listener) =>
              listener && typeof listener.unsubscribe === "function"
                ? listener.unsubscribe()
                : undefined,
            ),
          );
          throw error;
        }

        setStatus(
          "connected",
          "FDC3 Desktop Agent connected",
          "Listening for three standard context types and the ViewInstrument intent.",
        );
        return api;
      })();

      try {
        return await connectionPromise;
      } catch (error) {
        desktopAgent = null;
        connectionPromise = null;
        setStatus("error", "FDC3 connection failed", error.message || String(error));
        throw error;
      }
    }

    function loadExample() {
      element("context-input").value = JSON.stringify(SAMPLE_CONTEXT, null, 2);
      setMessage("Example loaded locally. No context has been broadcast.", "");
    }

    async function broadcastInput() {
      let context;
      try {
        context = parseContext(element("context-input").value);
      } catch (error) {
        setMessage(error.message, "error");
        return false;
      }

      if (!desktopAgent) {
        renderContext(context, "Standalone local preview", null);
        setMessage(
          "No FDC3 Desktop Agent is connected. The context was previewed locally and was not broadcast.",
          "error",
        );
        return false;
      }

      try {
        await desktopAgent.broadcast(context);
        renderContext(context, "Outbound FDC3 user channel", null);
        setMessage("Context broadcast unchanged on the current FDC3 user channel.", "success");
        return true;
      } catch (error) {
        setMessage(`Broadcast failed: ${error.message || String(error)}`, "error");
        return false;
      }
    }

    function boot() {
      element("load-example-button").addEventListener("click", loadExample);
      element("broadcast-button").addEventListener("click", () => {
        void broadcastInput();
      });
      loadExample();

      if (win.fdc3) {
        void connect(win.fdc3).catch(() => undefined);
        return;
      }

      setStatus(
        "",
        "Standalone browser mode",
        "Waiting for the standard fdc3Ready event; local preview remains available.",
      );
      win.addEventListener(
        "fdc3Ready",
        () => {
          if (win.fdc3) {
            void connect(win.fdc3).catch(() => undefined);
          } else {
            setStatus(
              "error",
              "fdc3Ready fired without an API",
              "The Desktop Agent did not expose window.fdc3.",
            );
          }
        },
        { once: true },
      );
    }

    return Object.freeze({
      boot,
      broadcastInput,
      connect,
      loadExample,
      renderContext,
    });
  }

  const library = Object.freeze({
    SAMPLE_CONTEXT,
    SUPPORTED_CONTEXT_TYPES,
    createInspector,
    parseContext,
    sourceLabel,
    validateContext,
  });
  global.FinancialEvidenceFdc3 = library;

  if (global.window && global.document) {
    const inspector = createInspector({
      window: global.window,
      document: global.document,
    });
    inspector.boot();
  }
})(typeof globalThis === "undefined" ? this : globalThis);
