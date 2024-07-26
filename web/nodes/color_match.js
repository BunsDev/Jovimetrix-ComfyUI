/**
 * File: color_match.js
 * Project: Jovimetrix
 *
 */

import { app } from "../../../scripts/app.js"
import { fitHeight } from '../util/util.js'
import { widget_hide, widget_show } from '../util/util_widget.js'

const _id = "COLOR MATCH (JOV) 💞"

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
            const color_map = this.widgets.find(w => w.name === '🇸🇨');
            const num_color = this.widgets.find(w => w.name === 'VAL');
            const mode = this.widgets.find(w => w.name === 'MODE');
            const map = this.widgets.find(w => w.name === 'MAP');
            map.callback = () => {
                widget_hide(this, color_map, "-jov");
                widget_hide(this, num_color, "-jov");
                if (mode.value == "LUT") {
                    if (map.value == "USER_MAP") {
                        widget_show(num_color);
                    } else {
                        widget_show(color_map);
                    }
                }
                fitHeight(self);
            };
            mode.callback = () => {
                widget_hide(this, map, "-jov");
                if (mode.value == "LUT") {
                    widget_show(map);
                }
                setTimeout(() => { map.callback(); }, 10);
            };
            setTimeout(() => { mode.callback(); }, 10);
            return me;
        }
    }
})
