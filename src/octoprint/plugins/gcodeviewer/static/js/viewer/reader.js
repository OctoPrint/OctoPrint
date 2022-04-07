/**
 * User: hudbrog (hudbrog@gmail.com)
 * Date: 10/21/12
 * Time: 7:31 AM
 */

GCODE.gCodeReader = (function () {
    // ***** PRIVATE ******
    var gcode, lines;
    var model = [];
    var max = {x: undefined, y: undefined, z: undefined};
    var min = {x: undefined, y: undefined, z: undefined};
    var modelSize = {x: undefined, y: undefined, z: undefined};
    var boundingBox = {
        minX: undefined,
        maxX: undefined,
        minY: undefined,
        maxY: undefined,
        minZ: undefined,
        maxZ: undefined
    };
    var filamentByLayer = {};
    var printTimeByLayer;
    var totalFilament = 0;
    var printTime = 0;
    var speeds = {};
    var speedsByLayer = {};
    var gCodeOptions = {
        sortLayers: false,
        purgeEmptyLayers: true,
        analyzeModel: false,
        toolOffsets: [{x: 0, y: 0}],
        bed: {
            x: undefined,
            y: undefined,
            r: undefined,
            circular: undefined,
            centeredOrigin: undefined
        },
        ignoreOutsideBed: false,
        g90InfluencesExtruder: false,
        bedZ: 0
    };

    var rendererModel = undefined;
    var layerPercentageLookup = [];
    var cachedLayer = undefined;
    var cachedCmd = undefined;

    var prepareGCode = function (totalSize) {
        if (!lines) return;
        gcode = [];
        var i, byteCount;

        byteCount = 0;
        for (i = 0; i < lines.length; i++) {
            byteCount += lines[i].length + 1; // line length + '\n'
            gcode.push({line: lines[i], percentage: (byteCount * 100) / totalSize});
        }
        lines = [];
    };

    var searchInPercentageTree = function (key) {
        function searchInLayers(lower, upper, key) {
            while (lower < upper) {
                var middle = Math.floor((lower + upper) / 2);

                if (
                    layerPercentageLookup[middle][0] <= key &&
                    layerPercentageLookup[middle][1] > key
                )
                    return middle;

                if (layerPercentageLookup[middle][0] > key) {
                    upper = middle - 1;
                } else {
                    lower = middle + 1;
                }
            }
            return lower;
        }

        function searchInCmds(layer, lower, upper, key) {
            while (lower < upper) {
                var middle = Math.floor((lower + upper) / 2);

                if (
                    rendererModel[layer][middle].percentage == key ||
                    (rendererModel[layer][middle].percentage <= key &&
                        rendererModel[layer][middle + 1].percentage > key)
                )
                    return middle;

                if (rendererModel[layer][middle].percentage > key) {
                    upper = middle - 1;
                } else {
                    lower = middle + 1;
                }
            }
            return lower;
        }

        if (rendererModel === undefined) return undefined;

        // this happens when the print is stopped.
        // just return last position to keep the last
        // position on screen.
        if (key == null) return {layer: cachedLayer, cmd: cachedCmd};

        var layer = searchInLayers(0, rendererModel.length - 1, key);
        var cmd = searchInCmds(layer, 0, rendererModel[layer].length - 1, key);

        // remember last position
        cachedLayer = layer;
        cachedCmd = cmd;

        return {layer: layer, cmd: cmd};
    };

    var sanitizeModel = function (m) {
        if (!m) return [];
        return _.filter(m, function (layer) {
            return !!layer;
        });
    };

    var purgeEmptyLayers = function (m) {
        return _.filter(m, function (layer) {
            return (
                !!layer &&
                layer.length > 0 &&
                _.find(layer, function (cmd) {
                    return cmd && cmd.extrude;
                }) !== undefined
            );
        });
    };

    var rebuildLayerPercentageLookup = function (m) {
        var result = [];

        if (m && m.length > 0) {
            for (var i = 0; i < m.length - 1; i++) {
                // start is first command of current layer
                var start = m[i].length ? m[i][0].percentage : -1;

                var end = -1;
                for (var j = i + 1; j < m.length; j++) {
                    // end is percentage of first command that follows our start, might
                    // be later layers if the next layer is empty!
                    if (m[j].length) {
                        end = m[j][0].percentage;
                        break;
                    }
                }

                result[i] = [start, end];
            }

            // final start-end-pair is start percentage of last layer and 100%
            result[m.length - 1] = m[m.length - 1].length
                ? [m[m.length - 1][0].percentage, 100]
                : [-1, -1];
        }

        layerPercentageLookup = result;
    };

    // ***** PUBLIC *******
    return {
        clear: function () {
            model = [];
            max = {x: undefined, y: undefined, z: undefined};
            min = {x: undefined, y: undefined, z: undefined};
            modelSize = {x: undefined, y: undefined, z: undefined};
            boundingBox = {
                minX: undefined,
                maxX: undefined,
                minY: undefined,
                maxY: undefined,
                minZ: undefined,
                maxZ: undefined
            };
            rendererModel = undefined;
            layerPercentageLookup = undefined;
            cachedLayer = undefined;
            cachedCmd = undefined;
        },

        loadFile: function (reader) {
            this.clear();

            var totalSize = reader.target.result.length;

            /*
             * Split by line ending
             *
             * Be aware that for windows line endings \r\n this leaves the \r attached to
             * the lines. That will not influence our parser, but makes file position
             * calculation way easier (line length + 1), so we just leave it in.
             *
             * This cannot cope with old MacOS \r line endings, but those should
             * really not be used anymore and thus we'll happily ignore them here.
             *
             * Note: A simple string split uses up *much* less memory than regex.
             */
            lines = reader.target.result.split("\n");

            reader.target.result = null;
            prepareGCode(totalSize);

            GCODE.ui.worker.postMessage({
                cmd: "parseGCode",
                msg: {
                    gcode: gcode,
                    options: {
                        firstReport: 5,
                        toolOffsets: gCodeOptions["toolOffsets"],
                        bed: gCodeOptions["bed"],
                        ignoreOutsideBed: gCodeOptions["ignoreOutsideBed"],
                        g90InfluencesExtruder: gCodeOptions["g90InfluencesExtruder"],
                        bedZ: gCodeOptions["bedZ"]
                    }
                }
            });
        },

        setOption: function (options) {
            var dirty = false;
            _.forOwn(options, function (value, key) {
                if (value === undefined) return;
                dirty = dirty || gCodeOptions[key] !== value;
                gCodeOptions[key] = value;
            });
            if (dirty) {
                if (model && model.length > 0) this.passDataToRenderer();
            }
        },

        passDataToRenderer: function () {
            var m = sanitizeModel(model);
            if (gCodeOptions["purgeEmptyLayers"]) m = purgeEmptyLayers(m);

            rendererModel = m;
            rebuildLayerPercentageLookup(m);

            GCODE.renderer.doRender(m, 0);
            return m;
        },

        processLayersFromWorker: function (msg) {
            for (var i = 0; i < msg.layers.length; i++) {
                model[msg.layers[i]] = msg.model[msg.layers[i]];
            }
        },

        processAnalyzeModelDone: function (msg) {
            min = msg.min;
            max = msg.max;
            modelSize = msg.modelSize;
            boundingBox = msg.boundingBox;
            totalFilament = msg.totalFilament;
            filamentByLayer = msg.filamentByLayer;
            speeds = msg.speeds;
            speedsByLayer = msg.speedsByLayer;
            printTime = msg.printTime;
            printTimeByLayer = msg.printTimeByLayer;
        },

        getLayerFilament: function (z) {
            return filamentByLayer[z];
        },

        getLayerSpeeds: function (z) {
            return speedsByLayer[z] ? speedsByLayer[z] : {};
        },

        getModelInfo: function () {
            return {
                min: min,
                max: max,
                modelSize: modelSize,
                boundingBox: boundingBox,
                totalFilament: totalFilament,
                speeds: speeds,
                speedsByLayer: speedsByLayer,
                printTime: printTime,
                printTimeByLayer: printTimeByLayer
            };
        },

        getGCodeLines: function (layer, fromSegments, toSegments) {
            var result = {
                first: model[layer][fromSegments].gcodeLine,
                last: model[layer][toSegments].gcodeLine
            };
            return result;
        },

        getCmdIndexForPercentage: function (percentage) {
            return searchInPercentageTree(percentage);
        }
    };
})();
