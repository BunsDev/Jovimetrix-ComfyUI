/**
 * File: util_jov.js
 * Project: Jovimetrix
 *
 */

import { nodeFitHeight } from './util_node.js'
import { widgetShowVector, widgetFind, widget_type_name, widgetHide, widgetShow } from './util_widget.js'

export function hook_widget_size_mode(node, wh_hide=true) {
    const wh = widgetFind(node.widgets, '🇼🇭');
    const samp = widgetFind(node.widgets, '🎞️');
    const mode = widgetFind(node.widgets, 'MODE');
    mode.callback = () => {
        if (wh_hide) {
            widgetHide(node, wh, "-jov");
        }
        widgetHide(node, samp, "-jov");
        if (!['NONE'].includes(mode.value)) {
            widgetShow(wh);
        }
        if (!['NONE', 'CROP', 'MATTE'].includes(mode.value)) {
            widgetShow(samp);
        }
        nodeFitHeight(node);
    }
    setTimeout(() => { mode.callback(); }, 20);
}

export function hook_widget_size_mode2(nodeType, wh_hide=true) {
    const onNodeCreated = nodeType.prototype.onNodeCreated
    nodeType.prototype.onNodeCreated = function (node) {
        const me = onNodeCreated?.apply(this);
        const wh = widgetFind(node.widgets, '🇼🇭');
        const samp = widgetFind(node.widgets, '🎞️');
        const mode = widgetFind(node.widgets, 'MODE');
        mode.callback = () => {
            if (wh_hide) {
                widgetHide(node, wh, "-jov");
            }
            widgetHide(node, samp, "-jov");
            if (!['NONE'].includes(mode.value)) {
                widgetShow(wh);
            }
            if (!['NONE', 'CROP', 'MATTE'].includes(mode.value)) {
                widgetShow(samp);
            }
            nodeFitHeight(node);
        }
        setTimeout(() => { mode.callback(); }, 20);
        return me;
    }
}

export function hook_widget_type(node, control_key, match_output=0) {
    const combo = widgetFind(node.widgets, control_key);
    const output = node.outputs[match_output];

    if (!output || !combo) {
        throw new Error("Required widgets not found");
    }

    const oldCallback = combo.callback;
    combo.callback = () => {
        const me = oldCallback?.apply(this, arguments);
        node.outputs[match_output].name = widget_type_name(combo.value);
        node.outputs[match_output].type = combo.value;
        return me;
    }
    setTimeout(() => { combo.callback(); }, 10);
}

export function hook_widget_AB(node, control_key, match_output=-1) {
    const initializeTrack = (widget) => {
        const track = {};
        for (let i = 0; i < 4; i++) {
            track[i] = widget.options.default[i];
        }
        Object.assign(track, widget.value);
        return track;
    };

    const setCallback = (widget, trackKey) => {
        widget.options.menu = false;
        widget.callback = () => {
            if (widget.type === "toggle") {
                trackKey[0] = widget.value ? 1 : 0;
            } else {
                Object.keys(widget.value).forEach((key) => {
                    trackKey[key] = widget.value[key];
                });
            }
        };
    };

    const { widgets } = node;
    const A = widgetFind(widgets, '🅰️🅰️');
    const B = widgetFind(widgets, '🅱️🅱️');
    const combo = widgetFind(widgets, control_key);

    if (!A || !B || !combo) {
        throw new Error("Required widgets not found");
    }

    const data = {
        track_xyzw: initializeTrack(A),
        track_yyzw: initializeTrack(B),
        A,
        B,
        combo
    };

    if (match_output > -1) {
        hook_widget_type(node, control_key, match_output);
    }

    const oldCallback = combo.callback;
    combo.callback = () => {
        const me = oldCallback?.apply(this, arguments);
        widgetHide(node, A, "-jovi");
        widgetHide(node, B, "-jovi");
        if (["VEC2", "VEC2INT", "COORD2D", "VEC3", "VEC3INT", "VEC4", "VEC4INT", "BOOLEAN", "INT", "FLOAT"].includes(combo.value)) {
            widgetShowVector(A, data.track_xyzw, combo.value);
            widgetShowVector(B, data.track_yyzw, combo.value);
        }
        nodeFitHeight(node);
        return me;
    }

    setTimeout(() => { combo.callback(); }, 10);
    setCallback(A, data.track_xyzw);
    setCallback(B, data.track_yyzw);
    return data;
}
