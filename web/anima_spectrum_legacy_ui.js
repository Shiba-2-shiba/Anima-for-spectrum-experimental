import { app } from "/scripts/app.js";

const SPECTRUM_NODE_ID = "ShibaAnimaForSpectrumExperimental";
const MANUAL_PRESET = "Manual";

const MANUAL_WIDGETS = new Set([
  "spectrum_w",
  "spectrum_warmup_steps",
  "spectrum_window_size",
  "enable_calibration",
  "calibration_strength",
  "calibration_mode",
  "spectrum_m",
  "spectrum_lam",
  "spectrum_taylor_damping",
  "spectrum_multistep_damping",
  "spectrum_flex_window",
  "spectrum_stop_caching_step",
  "spectrum_extra_forecast_steps",
  "calibration_decay",
  "calibration_buckets",
  "calibration_min_obs",
  "debug_enable_spectrum",
  "feature_site",
  "target_block_index",
  "forecast_mode",
  "debug_logging",
]);

function rememberWidgetDefaults(widget) {
  if (!widget.__animaSpectrumDefaults) {
    widget.__animaSpectrumDefaults = {
      computeSize: widget.computeSize,
      hidden: widget.hidden,
    };
  }
}

function hideWidget(widget) {
  rememberWidgetDefaults(widget);
  widget.hidden = true;
  widget.computeSize = () => [0, -4];
}

function showWidget(widget) {
  const defaults = widget.__animaSpectrumDefaults;
  if (!defaults) {
    return;
  }

  widget.hidden = defaults.hidden;
  widget.computeSize = defaults.computeSize;
}

function refreshNodeSize(node) {
  const size = node.computeSize?.();
  if (size) {
    node.setSize(size);
  }
  app.graph?.setDirtyCanvas(true, true);
}

function updateSpectrumWidgets(node) {
  const presetWidget = node.widgets?.find((widget) => widget.name === "spectrum_preset");
  const showManualControls = presetWidget?.value === MANUAL_PRESET;

  for (const widget of node.widgets ?? []) {
    if (!MANUAL_WIDGETS.has(widget.name)) {
      continue;
    }

    if (showManualControls) {
      showWidget(widget);
    } else {
      hideWidget(widget);
    }
  }

  refreshNodeSize(node);
}

app.registerExtension({
  name: "shiba.animaSpectrum.legacyUi",

  beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== SPECTRUM_NODE_ID) {
      return;
    }

    const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function (...args) {
      const result = originalOnNodeCreated?.apply(this, args);
      const presetWidget = this.widgets?.find((widget) => widget.name === "spectrum_preset");

      if (presetWidget && !presetWidget.__animaSpectrumCallbackWrapped) {
        const originalCallback = presetWidget.callback;
        presetWidget.callback = (...callbackArgs) => {
          const callbackResult = originalCallback?.apply(presetWidget, callbackArgs);
          updateSpectrumWidgets(this);
          return callbackResult;
        };
        presetWidget.__animaSpectrumCallbackWrapped = true;
      }

      updateSpectrumWidgets(this);
      return result;
    };

    const originalOnConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function (...args) {
      const result = originalOnConfigure?.apply(this, args);
      updateSpectrumWidgets(this);
      return result;
    };
  },
});
