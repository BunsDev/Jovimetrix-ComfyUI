/**
 * File: stream_reader.js
 * Project: Jovimetrix
 *
 */

import { app } from "../../../scripts/app.js"
import { fitHeight } from '../util/util.js'
import{ hook_widget_size_mode } from '../util/util_jov.js'
import { widget_hide, widget_show } from '../util/util_widget.js'

const _id = "STREAM READER (JOV) 📺"

app.registerExtension({
	name: 'jovimetrix.node.' + _id,
	async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== _id) {
            return
        }

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = async function () {
            const me = onNodeCreated?.apply(this);
            const self = this;
            hook_widget_size_mode(this);
            const url = this.widgets.find(w => w.name === '🌐');
            const orient = this.widgets.find(w => w.name === '🧭');
            const zoom = this.widgets.find(w => w.name === '🔎');
            const dpi = this.widgets.find(w => w.name === 'DPI');
            const camera = this.widgets.find(w => w.name === '📹');
            const monitor =this.widgets.find(w => w.name === '🖥');
            const window = this.widgets.find(w => w.name === '🪟');
            const fps = this.widgets.find(w => w.name === '🏎️');
            const bbox = this.widgets.find(w => w.name === '🔲');
            const source = this.widgets.find(w => w.name === 'SRC');
            source.callback = () => {
                widget_hide(this, url, "-jov");
                widget_hide(this, camera, "-jov");
                widget_hide(this, monitor, "-jov");
                widget_hide(this, window, "-jov");
                widget_hide(this, dpi, "-jov");
                widget_hide(this, bbox, "-jov");
                widget_hide(this, fps, "-jov");
                widget_hide(this, orient, "-jov");
                widget_hide(this, zoom, "-jov");

                switch (source.value) {
                    // "URL", "CAMERA", "MONITOR", "WINDOW", "SPOUT"
                    case "URL":
                        widget_show(url);
                        break;

                    case "CAMERA":
                        widget_show(camera);
                        widget_show(fps);
                        widget_show(orient);
                        widget_show(zoom);
                        break;

                    case "MONITOR":
                        widget_show(monitor);
                        widget_show(bbox);
                        break;

                    case "WINDOW":
                        widget_show(window);
                        widget_show(dpi);
                        widget_show(bbox);
                        break;

                    case "SPOUT":
                        widget_show(url);
                        widget_show(fps);
                        break;
                }
                fitHeight(self);
            }
            setTimeout(() => { source.callback(); }, 10);
            return me;
        }
    }
})
